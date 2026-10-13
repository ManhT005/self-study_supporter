"""
OpenAI-compatible client — dùng chung cho mọi provider expose endpoint
POST /chat/completions theo chuẩn OpenAI (Groq, Cerebras, GitHub Models, OpenRouter).

Chỉ cần khác base_url / api_key / model khi khởi tạo.
"""

import time
import requests

from src.llm.llm_adapter import LLMAdapter, ChatResponse
from src.rag.embedding_provider import RateLimiter
from src.llm.errors import ProviderAuthenticationError, ProviderUnavailable
from study_supporter.domain.errors import QuotaExceeded


class QuotaExhaustedError(QuotaExceeded):
    """Lỗi quota theo NGÀY — MultiProviderLLM sẽ đánh dấu provider này 'chết'."""

    pass


class RateLimitError(Exception):
    """Lỗi quota theo PHÚT — MultiProviderLLM sẽ thử provider kế tiếp ngay."""

    pass


class OpenAICompatibleClient(LLMAdapter):
    """
    Client tương thích chuẩn OpenAI chat completions.
    Dùng cho Groq, Cerebras, GitHub Models, OpenRouter — bất kỳ provider nào
    expose POST {base_url}/chat/completions với schema giống OpenAI.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        provider_name: str = "unknown",
        max_retries: int = 3,
        max_calls: int = 20,
        period: float = 60.0,
        timeout: int = 60,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.provider_name = provider_name
        self.max_retries = max_retries
        self.timeout = timeout
        self.rate_limiter = RateLimiter(max_calls=max_calls, period=period)

    def chat(self, messages, system_prompt=None, stop_sequences=None) -> ChatResponse:
        # Build request messages
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        api_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": api_messages,
        }
        if stop_sequences:
            payload["stop"] = stop_sequences

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        for attempt in range(self.max_retries):
            self.rate_limiter.wait_if_needed()
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )

                if response.status_code == 429:
                    error_body = self._safe_json(response)
                    if self._is_daily_quota(error_body):
                        raise QuotaExhaustedError(
                            f"[{self.provider_name}] Hết quota theo NGÀY (free tier)."
                        )
                    # Per-minute rate limit → retry with backoff
                    if attempt < self.max_retries - 1:
                        wait = self._extract_retry_after(response, default=15.0)
                        print(
                            f"⏳ [{self.provider_name}] 429 (per-minute), đợi {wait:.1f}s..."
                        )
                        time.sleep(wait)
                        continue
                    else:
                        raise RateLimitError(
                            f"[{self.provider_name}] Rate limit sau {self.max_retries} lần thử."
                        )

                if response.status_code in {401, 403}:
                    raise ProviderAuthenticationError("Provider authentication failed")
                if response.status_code >= 400:
                    raise ProviderUnavailable(f"Provider HTTP {response.status_code}")

                data = response.json()
                return self._parse_response(data)

            except (requests.ConnectionError, requests.Timeout):
                if attempt < self.max_retries - 1:
                    wait = 2**attempt
                    print(f"⏳ [{self.provider_name}] Network error, retry sau {wait}s")
                    time.sleep(wait)
                    continue
                raise ProviderUnavailable("Provider network unavailable") from None

        # Should not reach here, but just in case
        raise RateLimitError(f"[{self.provider_name}] Hết số lần retry.")

    def _parse_response(self, data: dict) -> ChatResponse:
        """Parse response theo chuẩn OpenAI chat completions."""
        choices = data.get("choices", [])
        if not choices:
            return ChatResponse(text="", raw=data)

        choice = choices[0]
        message = choice.get("message", {})
        text = message.get("content", "") or ""

        finish_reason = choice.get("finish_reason")

        usage = None
        usage_data = data.get("usage")
        if usage_data:
            usage = {
                "input_tokens": usage_data.get("prompt_tokens"),
                "output_tokens": usage_data.get("completion_tokens"),
                "total_tokens": usage_data.get("total_tokens"),
            }

        return ChatResponse(
            text=text,
            usage=usage,
            finish_reason=finish_reason,
            raw=data,
        )

    @staticmethod
    def _safe_json(response) -> dict:
        try:
            return response.json()
        except Exception:
            return {}

    @staticmethod
    def _extract_retry_after(response, default: float = 15.0) -> float:
        """Lấy thời gian chờ từ header Retry-After hoặc dùng default."""
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return float(retry_after) + 1
            except ValueError:
                pass
        return default

    @staticmethod
    def _is_daily_quota(error_body: dict) -> bool:
        """Phát hiện lỗi quota theo ngày dựa trên nội dung error message."""
        error_msg = str(error_body).lower()
        daily_indicators = ["per day", "daily", "perday", "rate_limit_exceeded"]
        return any(indicator in error_msg for indicator in daily_indicators)

    def __repr__(self):
        return (
            f"OpenAICompatibleClient(provider={self.provider_name}, model={self.model})"
        )
