from unittest.mock import Mock, patch

import pytest
import requests

from src.llm.errors import ProviderAuthenticationError, ProviderUnavailable
from src.llm.multi_provider_llm import MultiProviderLLM
from src.llm.openai_compatible_client import OpenAICompatibleClient, RateLimitError


@pytest.mark.parametrize(
    "status,error",
    [
        (401, ProviderAuthenticationError),
        (403, ProviderAuthenticationError),
        (429, RateLimitError),
        (503, ProviderUnavailable),
    ],
)
def test_typed_status_errors_do_not_leak_body(status, error):
    client = OpenAICompatibleClient(
        "https://example.invalid", "secret-key", "fixture", max_retries=1
    )
    response = Mock(status_code=status, text="secret-key private-document")
    response.json.return_value = {"error": {"message": response.text}}
    with patch("requests.post", return_value=response), pytest.raises(error) as caught:
        client.chat([])
    assert "secret-key" not in str(caught.value)


def test_authentication_failure_is_not_hidden_by_fallback():
    first, second = Mock(), Mock()
    first.chat.side_effect = ProviderAuthenticationError("invalid credentials")
    with pytest.raises(ProviderAuthenticationError):
        MultiProviderLLM([first, second]).chat([])
    second.chat.assert_not_called()


def test_timeout_can_fallback_without_logging_sensitive_message(capsys):
    first = OpenAICompatibleClient(
        "https://example.invalid", "secret-key", "fixture", max_retries=1
    )
    second = Mock()
    second.chat.return_value = "ok"
    with patch("requests.post", side_effect=requests.Timeout("secret-key")):
        assert MultiProviderLLM([first, second]).chat([]) == "ok"
    assert "secret-key" not in capsys.readouterr().out
