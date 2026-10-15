import pytest
from pydantic import ValidationError

from study_supporter.orchestration.langchain_agent.models import ProgressInput, SearchInput


@pytest.mark.parametrize(
    "args",
    [
        {"query": " "},
        {"query": "x", "top_k": 0},
        {"query": "x", "top_k": 999},
        {"query": "x", "top_k": True},
        {"query": "x", "top_k": "3"},
        {"query": "x", "user_id": "B"},
        {"query": "x", "document_ids": ["B"]},
        {"query": "x", "session_key": "secret"},
        {"query": "x", "collection_name": "B"},
    ],
)
def test_search_rejects_invalid_or_untrusted_scope(args):
    with pytest.raises(ValidationError):
        SearchInput.model_validate(args)


def test_search_defaults_and_empty_progress_schema():
    assert SearchInput(query="  hello  ").model_dump() == {"query": "hello", "top_k": 3}
    assert ProgressInput.model_json_schema()["properties"] == {}
    with pytest.raises(ValidationError):
        ProgressInput(user_id="B")
