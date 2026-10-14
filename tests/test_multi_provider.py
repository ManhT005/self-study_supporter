"""
Unit tests cho MultiProviderLLM — test logic xoay vòng provider với mock objects.
Không cần API key thật, không cần mạng.
"""

import time
import pytest
from unittest.mock import MagicMock, patch

from src.llm.llm_adapter import ChatResponse
from src.llm.multi_provider_llm import MultiProviderLLM
from src.llm.openai_compatible_client import QuotaExhaustedError, RateLimitError


def _make_mock_provider(name: str, response_text: str = "OK") -> MagicMock:
    """Tạo mock LLMAdapter trả về response thành công."""
    provider = MagicMock()
    provider.provider_name = name
    provider.chat.return_value = ChatResponse(text=response_text)
    return provider


def _make_failing_provider(name: str, error: Exception) -> MagicMock:
    """Tạo mock LLMAdapter luôn raise exception."""
    provider = MagicMock()
    provider.provider_name = name
    provider.chat.side_effect = error
    return provider


class TestMultiProviderLLM:
    """Test suite cho MultiProviderLLM."""

    def test_first_provider_success(self):
        """Provider đầu tiên thành công → trả kết quả ngay, không thử provider sau."""
        p1 = _make_mock_provider("Gemini", "Gemini response")
        p2 = _make_mock_provider("Groq", "Groq response")

        multi = MultiProviderLLM([p1, p2])
        result = multi.chat([{"role": "user", "content": "hello"}])

        assert result.text == "Gemini response"
        p1.chat.assert_called_once()
        p2.chat.assert_not_called()

    def test_fallback_on_quota_exhausted(self):
        """Provider đầu hết quota ngày → chuyển sang provider tiếp theo."""
        p1 = _make_failing_provider("Gemini", QuotaExhaustedError("Hết quota"))
        p2 = _make_mock_provider("Groq", "Groq fallback")

        multi = MultiProviderLLM([p1, p2])
        result = multi.chat([{"role": "user", "content": "hello"}])

        assert result.text == "Groq fallback"
        p1.chat.assert_called_once()
        p2.chat.assert_called_once()

    def test_fallback_on_rate_limit(self):
        """Provider đầu bị rate limit (per-minute) → chuyển ngay, không sleep."""
        p1 = _make_failing_provider("Gemini", RateLimitError("Per-minute limit"))
        p2 = _make_mock_provider("Groq", "Groq response")

        multi = MultiProviderLLM([p1, p2])

        start = time.time()
        result = multi.chat([{"role": "user", "content": "hello"}])
        elapsed = time.time() - start

        assert result.text == "Groq response"
        assert elapsed < 1.0, "Không nên sleep khi chuyển provider"

    def test_dead_provider_skipped_on_subsequent_calls(self):
        """Provider đã hết quota ngày bị bỏ qua ở các lần gọi tiếp theo."""
        p1 = _make_failing_provider("Gemini", QuotaExhaustedError("Hết quota"))
        p2 = _make_mock_provider("Groq", "Groq response")

        multi = MultiProviderLLM([p1, p2])

        # Lần 1: p1 hết quota, fallback p2
        result1 = multi.chat([{"role": "user", "content": "hello 1"}])
        assert result1.text == "Groq response"

        # Lần 2: p1 bị skip (đánh dấu chết), gọi thẳng p2
        p1.chat.reset_mock()
        p2.chat.reset_mock()
        result2 = multi.chat([{"role": "user", "content": "hello 2"}])
        assert result2.text == "Groq response"
        p1.chat.assert_not_called()  # Không thử lại provider đã chết
        p2.chat.assert_called_once()

    def test_all_providers_exhausted(self):
        """Tất cả provider hết quota → raise RuntimeError."""
        p1 = _make_failing_provider("Gemini", QuotaExhaustedError("Hết quota Gemini"))
        p2 = _make_failing_provider("Groq", QuotaExhaustedError("Hết quota Groq"))

        multi = MultiProviderLLM([p1, p2])

        with pytest.raises(RuntimeError, match="Tất cả.*provider"):
            multi.chat([{"role": "user", "content": "hello"}])

    def test_runtime_error_non_quota_falls_through(self):
        """RuntimeError không phải quota → vẫn thử provider tiếp theo."""
        p1 = _make_failing_provider("Gemini", RuntimeError("Lỗi kết nối"))
        p2 = _make_mock_provider("Groq", "Groq response")

        multi = MultiProviderLLM([p1, p2])
        result = multi.chat([{"role": "user", "content": "hello"}])

        assert result.text == "Groq response"

    def test_unexpected_exception_falls_through(self):
        """Exception không mong đợi → vẫn thử provider tiếp, không crash."""
        p1 = _make_failing_provider("Gemini", ValueError("Unexpected"))
        p2 = _make_mock_provider("Groq", "Groq response")

        multi = MultiProviderLLM([p1, p2])
        result = multi.chat([{"role": "user", "content": "hello"}])

        assert result.text == "Groq response"

    def test_dead_provider_reset_next_day(self):
        """Provider 'chết' được reset khi sang ngày mới (UTC)."""
        p1 = _make_failing_provider("Gemini", QuotaExhaustedError("Hết quota"))
        p2 = _make_mock_provider("Groq", "Groq response")

        multi = MultiProviderLLM([p1, p2])

        # Gọi lần 1: p1 hết quota
        multi.chat([{"role": "user", "content": "hello"}])
        assert 0 in multi._dead_since

        # Giả lập "đã sang ngày mới" bằng cách set dead_since về hôm qua
        multi._dead_since[0] = time.time() - 86400 * 2  # 2 ngày trước

        # Giờ p1 nên được phục hồi
        p1.chat.reset_mock()
        p1.chat.side_effect = None  # Lần này p1 hoạt động bình thường
        p1.chat.return_value = ChatResponse(text="Gemini back")

        result = multi.chat([{"role": "user", "content": "hello"}])
        assert result.text == "Gemini back"
        p1.chat.assert_called_once()

    def test_get_status(self):
        """get_status() trả về trạng thái đúng cho từng provider."""
        p1 = _make_failing_provider("Gemini", QuotaExhaustedError("Hết quota"))
        p2 = _make_mock_provider("Groq", "Groq response")

        multi = MultiProviderLLM([p1, p2])
        multi.chat([{"role": "user", "content": "hello"}])

        status = multi.get_status()
        assert len(status) == 2
        assert status[0]["name"] == "Gemini"
        assert status[0]["available"] is False
        assert status[1]["name"] == "Groq"
        assert status[1]["available"] is True

    def test_cascade_three_providers(self):
        """Test xoay vòng 3 provider: P1 quota ngày, P2 rate limit phút, P3 thành công."""
        p1 = _make_failing_provider("Gemini", QuotaExhaustedError("Hết quota ngày"))
        p2 = _make_failing_provider("Groq", RateLimitError("Per-minute limit"))
        p3 = _make_mock_provider("Cerebras", "Cerebras response")

        multi = MultiProviderLLM([p1, p2, p3])
        result = multi.chat([{"role": "user", "content": "hello"}])

        assert result.text == "Cerebras response"
        p1.chat.assert_called_once()
        p2.chat.assert_called_once()
        p3.chat.assert_called_once()

    def test_single_provider(self):
        """MultiProviderLLM hoạt động đúng với chỉ 1 provider."""
        p1 = _make_mock_provider("Ollama", "Ollama response")

        multi = MultiProviderLLM([p1])
        result = multi.chat([{"role": "user", "content": "hello"}])
        assert result.text == "Ollama response"

    def test_empty_providers_raises(self):
        """Danh sách provider rỗng → raise ValueError ngay lúc khởi tạo."""
        with pytest.raises(ValueError, match="ít nhất 1 provider"):
            MultiProviderLLM([])

    def test_passes_all_arguments_to_provider(self):
        """Đảm bảo messages, system_prompt, stop_sequences được truyền đúng."""
        p1 = _make_mock_provider("Gemini", "OK")
        multi = MultiProviderLLM([p1])

        messages = [{"role": "user", "content": "hello"}]
        multi.chat(messages, system_prompt="You are helpful", stop_sequences=["STOP"])

        p1.chat.assert_called_once_with(
            messages,
            "You are helpful",
            ["STOP"],
        )
