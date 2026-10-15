import asyncio

import pytest

pytest.importorskip("langchain")

from langchain_core.messages import AIMessage

from scripts.langchain_fixtures import ScriptedNativeModel, capability_model, native_call
from study_supporter.domain.provider_errors import ProviderUnavailable
from study_supporter.infrastructure.llm.langchain_bridge import (
    NativeModelConfig,
    create_native_model,
    probe_native_model,
    validated_model_factory,
)


def test_offline_native_roundtrip_and_unknown_usage():
    config = NativeModelConfig("ollama", "fixture:1")
    receipt = asyncio.run(probe_native_model(capability_model(), config))
    assert receipt.available and receipt.parallel_calls and receipt.requests == 2
    assert receipt.input_tokens is receipt.output_tokens is None
    assert callable(validated_model_factory(config, receipt))
    with pytest.raises(ProviderUnavailable):
        validated_model_factory(NativeModelConfig("ollama", "other:1"), receipt)


@pytest.mark.parametrize(
    "response",
    [
        AIMessage(content='Action: capability_echo\nAction Input: {"value": 1}'),
        AIMessage(content="", tool_calls=[native_call("capability_echo", {"value": 999})]),
        AIMessage(content="", tool_calls=[native_call("unknown", {"value": 1})]),
        RuntimeError("secret-provider-token"),
    ],
)
def test_unsupported_and_malformed_native_calls_fail_closed(response):
    config = NativeModelConfig("ollama", "fixture:1")
    receipt = asyncio.run(probe_native_model(ScriptedNativeModel(responses=[response]), config))
    assert not receipt.available and receipt.requests == 1
    assert "secret" not in repr(receipt)
    with pytest.raises(ProviderUnavailable):
        validated_model_factory(config, receipt)


def test_probe_cancels_at_deadline():
    config = NativeModelConfig("ollama", "fixture:1", timeout_seconds=0.01)
    model = capability_model()
    model.delay_seconds = 1
    receipt = asyncio.run(probe_native_model(model, config))
    assert not receipt.available and model.cursor == 0


@pytest.mark.parametrize("provider,model", [("auto", "x"), ("gemini", "auto"), ("ollama", "")])
def test_unpinned_provider_configuration_is_rejected(provider, model):
    with pytest.raises(ValueError):
        NativeModelConfig(provider, model)


def test_gemini_bridge_disables_sdk_retries_without_network(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import Mock

    from google.genai._api_client import retry_args
    from google.genai.types import HttpRetryOptions
    import langchain_google_genai

    constructor = Mock(return_value=object())
    monkeypatch.setattr(langchain_google_genai, "ChatGoogleGenerativeAI", constructor)
    create_native_model(NativeModelConfig("gemini", "gemini-2.5-flash-lite", api_key="test-only"))
    attempts = constructor.call_args.kwargs["max_retries"]
    assert attempts == 1
    stop = retry_args(HttpRetryOptions(attempts=attempts))["stop"]
    assert stop(SimpleNamespace(attempt_number=1)) is True
