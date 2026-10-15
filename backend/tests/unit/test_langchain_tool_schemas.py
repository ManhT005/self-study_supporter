import pytest
from pydantic import ValidationError

from study_supporter.orchestration.langchain_agent.models import (
    ProgressInput,
    QuizInput,
    SaveNoteInput,
    SearchInput,
)


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


@pytest.mark.parametrize(
    "schema,args",
    [
        (QuizInput, {"topic": " "}),
        (QuizInput, {"topic": "x", "num_questions": 0}),
        (QuizInput, {"topic": "x", "num_questions": 16}),
        (QuizInput, {"topic": "x", "correct_answer_index": 0}),
        (SaveNoteInput, {"note": " "}),
        (SaveNoteInput, {"note": "x" * 4001}),
        (SaveNoteInput, {"note": "x", "confirmed": True}),
        (SaveNoteInput, {"note": "x", "user_id": "B"}),
        (SaveNoteInput, {"note": "x", "operation_id": ""}),
    ],
)
def test_quiz_and_note_boundaries(schema, args):
    with pytest.raises(ValidationError):
        schema.model_validate(args)


def test_only_safe_model_editable_fields_are_exposed():
    allowed = {
        SearchInput: {"query", "top_k"},
        ProgressInput: set(),
        QuizInput: {"topic", "num_questions"},
        SaveNoteInput: {"note", "operation_id"},
    }
    for schema, fields in allowed.items():
        assert set(schema.model_json_schema()["properties"]) == fields
        assert schema.model_json_schema()["additionalProperties"] is False
