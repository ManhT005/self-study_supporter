"""Pinned, no-fallback Gemini transport with explicit request/time/output limits."""

import time
from pathlib import Path

from study_supporter.application.ports.llm import ChatResponse
from study_supporter.domain.errors import QuotaExceeded
from study_supporter.domain.provider_errors import ProviderAuthenticationError, ProviderUnavailable


class RequestBudget:
    def __init__(self, max_calls, seconds, journal, *, clock=time.monotonic):
        self.max_calls, self.seconds, self.journal = max_calls, seconds, Path(journal)
        self.clock, self.started, self.calls = clock, clock(), 0

    def reserve(self):
        if self.clock() - self.started >= self.seconds:
            raise TimeoutError("Request deadline exhausted")
        if self.calls >= self.max_calls:
            raise ProviderUnavailable("Model call budget exhausted")
        self.calls += 1
        with self.journal.open("a", encoding="utf-8") as stream:
            stream.write('{"event":"model_call_reserved"}\n')
            stream.flush()


class PinnedGemini:
    def __init__(
        self,
        model,
        budget,
        *,
        api_key,
        max_output_tokens=768,
        temperature=0.0,
        client=None,
        blocked=False,
    ):
        self.model, self.budget, self.max_output_tokens = model, budget, max_output_tokens
        self.temperature, self.client, self.api_key = temperature, client, api_key
        self.blocked = blocked
        self.usage = []
        self.model_versions = set()
        self.failure_reason = None

    def chat(self, messages, system_prompt=None, stop_sequences=None):
        if self.blocked:
            self.failure_reason = self.failure_reason or "PROVIDER_DISABLED_AFTER_FAILURE"
            raise ProviderUnavailable("Provider disabled for this run")
        if sum(len(m.get("content", "")) for m in messages) + len(system_prompt or "") > 24000:
            raise ValueError("Frozen input-character budget exceeded")
        try:
            self.budget.reserve()
        except ProviderUnavailable:
            self.failure_reason = "BUDGET_EXHAUSTED"
            raise
        except TimeoutError:
            self.failure_reason = "DEADLINE_EXHAUSTED"
            raise
        from google import genai
        from google.genai import types

        if self.client is None:
            self.client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(
                    timeout=45000, retry_options=types.HttpRetryOptions(attempts=1)
                ),
            )
        contents = [
            {
                "role": "model" if m["role"] == "assistant" else m["role"],
                "parts": [{"text": m["content"]}],
            }
            for m in messages
        ]
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    stop_sequences=stop_sequences,
                    temperature=self.temperature,
                    max_output_tokens=self.max_output_tokens,
                    thinking_config=types.ThinkingConfig(thinking_budget=0, include_thoughts=False),
                ),
            )
        except Exception as exc:
            code = getattr(exc, "code", None)
            self.failure_reason = "PROVIDER_RATE_LIMIT" if code == 429 else "PROVIDER_FAILURE"
            self.blocked = True
            if code == 429:
                raise QuotaExceeded("Provider quota exhausted") from None
            if code in {401, 403}:
                raise ProviderAuthenticationError("Provider authentication failed") from None
            raise ProviderUnavailable("Provider request failed") from None
        if getattr(response, "model_version", None):
            self.model_versions.add(response.model_version)
        metadata = response.usage_metadata
        usage = (
            {
                "input_tokens": metadata.prompt_token_count,
                "output_tokens": metadata.candidates_token_count,
            }
            if metadata
            else None
        )
        self.usage.append(usage)
        if self.budget.clock() - self.budget.started >= self.budget.seconds:
            self.failure_reason = "DEADLINE_EXHAUSTED"
            raise TimeoutError("Provider response exceeded request deadline")
        return ChatResponse(text=response.text or "", usage=usage)

    def close(self):
        if self.client is not None:
            self.client.close()
