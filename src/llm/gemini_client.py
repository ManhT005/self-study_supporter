import time
from google import genai
from google.genai.types import GenerateContentConfig
from google.genai.errors import ClientError

from src.llm.llm_adapter import LLMAdapter, ChatResponse
from src.rag.embedding_provider import RateLimiter, _extract_retry_delay, _get_quota_period


class GeminiClient(LLMAdapter):
    def __init__(
        self,
        client: genai.Client,
        model: str = "gemini-3-flash-preview",
        max_retries: int = 5,
        max_calls: int = 8,
        period: float = 60.0,
    ):
        self.client = client
        self.model = model
        self.max_retries = max_retries
        self.rate_limiter = RateLimiter(max_calls=max_calls, period=period)

    def _to_gemini_contents(self, messages: list[dict]) -> list[dict]:
        """Gemini dùng role 'model' thay vì 'assistant' — cần convert."""
        contents = []
        for m in messages:
            role = "model" if m["role"] == "assistant" else m["role"]
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
        return contents

    def chat(self, messages: list[dict], system_prompt: str | None = None) -> ChatResponse:
        contents = self._to_gemini_contents(messages)
        config = GenerateContentConfig(system_instruction=system_prompt) if system_prompt else None

        for attempt in range(self.max_retries):
            self.rate_limiter.wait_if_needed()
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )
                usage = None
                if response.usage_metadata:
                    usage = {
                        "input_tokens": response.usage_metadata.prompt_token_count,
                        "output_tokens": response.usage_metadata.candidates_token_count,
                        "total_tokens": response.usage_metadata.total_token_count,
                    }
                finish_reason = None
                if response.candidates:
                    finish_reason = response.candidates[0].finish_reason.name

                return ChatResponse(
                    text=response.text,
                    usage=usage,
                    finish_reason=finish_reason,
                    raw=response,
                )

            except ClientError as e:
                if getattr(e, "status_code", None) != 429:
                    raise

                period_type = _get_quota_period(e)
                if period_type == "day":
                    raise RuntimeError(
                        "Hết quota generateContent theo NGÀY (free tier). "
                        "Đổi sang OllamaClient hoặc đợi reset."
                    ) from e

                if attempt < self.max_retries - 1:
                    wait = _extract_retry_delay(e)
                    print(f"429 (chat, per-minute), đợi {wait:.1f}s...")
                    time.sleep(wait)
                else:
                    raise