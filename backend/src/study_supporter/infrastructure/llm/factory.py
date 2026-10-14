from dataclasses import dataclass

from study_supporter.application.ports.llm import LLMAdapter
from study_supporter.config import Settings
from study_supporter.infrastructure.llm.ollama_client import OllamaClient
from study_supporter.infrastructure.llm.multi_provider_llm import MultiProviderLLM
from study_supporter.infrastructure.llm.openai_compatible_client import OpenAICompatibleClient


@dataclass(frozen=True)
class ProviderSelection:
    client: LLMAdapter
    mode: str
    notice: str = ""


def select_provider(settings: Settings, mode: str = "auto") -> ProviderSelection:
    def ollama():
        return OllamaClient(settings.ollama_model, settings.ollama_base_url)

    def gemini():
        from google import genai
        from study_supporter.infrastructure.llm.gemini_client import GeminiClient

        return GeminiClient(
            genai.Client(api_key=settings.gemini_api_key), model="gemini-3-flash-preview"
        )

    if mode == "ollama":
        return ProviderSelection(ollama(), mode)
    if mode == "gemini":
        if settings.gemini_api_key:
            try:
                return ProviderSelection(gemini(), mode)
            except Exception:
                pass
        return ProviderSelection(
            ollama(), "ollama", "Không khởi tạo được Gemini, chuyển sang Ollama local."
        )
    if mode != "auto":
        raise ValueError("Unknown provider mode")
    providers = []
    if settings.gemini_api_key:
        try:
            providers.append(gemini())
        except Exception:
            pass  # Preserve initialization fallback, without exposing SDK/key errors.
    for key, url, model, name, limit in [
        (
            settings.groq_api_key,
            "https://api.groq.com/openai/v1",
            "llama-3.3-70b-versatile",
            "Groq",
            25,
        ),
        (settings.cerebras_api_key, "https://api.cerebras.ai/v1", "llama-3.3-70b", "Cerebras", 25),
        (
            settings.github_token,
            "https://models.inference.ai.azure.com",
            "gpt-4o-mini",
            "GitHub Models",
            10,
        ),
        (
            settings.openrouter_api_key,
            "https://openrouter.ai/api/v1",
            "meta-llama/llama-3.3-70b-instruct:free",
            "OpenRouter",
            15,
        ),
    ]:
        if key:
            providers.append(
                OpenAICompatibleClient(
                    url, key, model, provider_name=name, max_calls=limit, period=60.0
                )
            )
    providers.append(ollama())
    return ProviderSelection(
        providers[0] if len(providers) == 1 else MultiProviderLLM(providers),
        "auto",
        "Không tìm thấy API key nào, chỉ dùng Ollama cục bộ." if len(providers) == 1 else "",
    )
