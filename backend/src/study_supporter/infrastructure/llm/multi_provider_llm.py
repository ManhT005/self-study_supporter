"""
MultiProviderLLM — điều phối xoay vòng nhiều LLM provider.

Implement LLMAdapter, tương thích ngược hoàn toàn với ReActOrchestrator —
truyền thẳng vào ReActOrchestrator(llm=multi_provider, ...) mà không cần
sửa 1 dòng nào trong orchestrator.py hay bất kỳ tool nào.

Nguyên tắc:
- Thử từng provider theo thứ tự ưu tiên giảm dần.
- QuotaExhaustedError (quota ngày) → đánh dấu "chết", bỏ qua cho đến khi reset.
- RateLimitError / Exception khác → thử provider kế tiếp ngay (không sleep).
- Tất cả hết quota → raise RuntimeError rõ ràng.
"""

import time
from datetime import datetime, timezone

from study_supporter.application.ports.llm import LLMAdapter, ChatResponse
from study_supporter.infrastructure.llm.openai_compatible_client import (
    QuotaExhaustedError,
    RateLimitError,
)
from study_supporter.domain.provider_errors import ProviderAuthenticationError


class MultiProviderLLM(LLMAdapter):
    def __init__(self, providers: list[LLMAdapter]):
        """
        providers: danh sách LLMAdapter theo thứ tự ưu tiên giảm dần.
                   Provider đầu tiên (chất lượng cao nhất) sẽ được thử trước.
        """
        if not providers:
            raise ValueError("Cần ít nhất 1 provider trong danh sách.")
        self.providers = providers
        # Map: index → timestamp (UTC) khi provider bị đánh dấu "chết"
        self._dead_since: dict[int, float] = {}

    def chat(self, messages, system_prompt=None, stop_sequences=None) -> ChatResponse:
        self._reset_expired_providers()

        last_error = None
        for i, provider in enumerate(self.providers):
            if i in self._dead_since:
                continue  # provider này đã hết quota ngày, bỏ qua

            provider_name = self._get_provider_name(provider)
            try:
                result = provider.chat(messages, system_prompt, stop_sequences)
                print(f"✅ [{provider_name}] Phản hồi thành công.")
                return result

            except ProviderAuthenticationError:
                raise
            except QuotaExhaustedError as e:
                # Quota theo NGÀY → đánh dấu "chết" tới cuối ngày
                self._dead_since[i] = time.time()
                print(f"🚫 [{provider_name}] Hết quota ngày, chuyển provider tiếp theo.")
                last_error = e
                continue

            except (RateLimitError, RuntimeError) as e:
                # Quota theo PHÚT hoặc lỗi khác → thử provider kế tiếp ngay
                print(f"⚠️ [{provider_name}] Lỗi tạm thời, thử provider tiếp.")
                last_error = e
                continue

            except Exception as e:
                # Lỗi không mong đợi (network, parse, ...) → không chết hẳn, chỉ skip lần này
                print(f"⚠️ [{provider_name}] Lỗi không xác định, thử provider tiếp.")
                last_error = e
                continue

        raise RuntimeError(
            f"Tất cả {len(self.providers)} provider đều không khả dụng. "
            f"Loại lỗi cuối: {type(last_error).__name__}"
        )

    def _reset_expired_providers(self):
        """
        Reset các provider bị đánh dấu 'chết' nếu đã sang ngày mới (UTC).
        Quota miễn phí thường reset theo ngày UTC.
        """
        if not self._dead_since:
            return

        now = datetime.now(timezone.utc)
        expired_indices = []
        for idx, dead_timestamp in self._dead_since.items():
            dead_time = datetime.fromtimestamp(dead_timestamp, tz=timezone.utc)
            if now.date() > dead_time.date():
                expired_indices.append(idx)

        for idx in expired_indices:
            provider_name = self._get_provider_name(self.providers[idx])
            print(f"🔄 [{provider_name}] Đã sang ngày mới, reset trạng thái.")
            del self._dead_since[idx]

    def get_status(self) -> list[dict]:
        """Trả về trạng thái từng provider (cho logging/debug)."""
        self._reset_expired_providers()
        status = []
        for i, provider in enumerate(self.providers):
            name = self._get_provider_name(provider)
            is_dead = i in self._dead_since
            status.append(
                {
                    "index": i,
                    "name": name,
                    "available": not is_dead,
                    "dead_since": self._dead_since.get(i),
                }
            )
        return status

    @staticmethod
    def _get_provider_name(provider) -> str:
        """Lấy tên provider để log dễ đọc."""
        if hasattr(provider, "provider_name"):
            return provider.provider_name
        return type(provider).__name__

    def __repr__(self):
        names = [self._get_provider_name(p) for p in self.providers]
        return f"MultiProviderLLM(providers={names})"
