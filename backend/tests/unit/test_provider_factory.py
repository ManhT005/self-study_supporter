from study_supporter.config import Settings
from study_supporter.bootstrap import ApplicationFactory
from study_supporter.infrastructure.llm.factory import select_provider


def test_factory_is_lazy_and_has_no_per_user_orchestrator():
    factory = ApplicationFactory(Settings())
    assert factory.embedding._provider is None
    assert not hasattr(factory, "orchestrator")


def test_missing_keys_preserve_local_fallback_and_default_model():
    result = select_provider(Settings(), "gemini")
    assert result.mode == "ollama" and result.notice
    assert result.client.model == "qwen2.5:1.5b"


def test_provider_priority_is_unchanged():
    settings = Settings(
        groq_api_key="fixture",
        cerebras_api_key="fixture",
        github_token="fixture",
        openrouter_api_key="fixture",
    )
    result = select_provider(settings)
    assert [getattr(p, "provider_name", "Ollama") for p in result.client.providers] == [
        "Groq",
        "Cerebras",
        "GitHub Models",
        "OpenRouter",
        "Ollama",
    ]
