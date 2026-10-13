from dataclasses import asdict

import pytest

from study_supporter.application.contracts.context import AppContext
from study_supporter.application.contracts.learning import (
    AnswerRequest,
    IngestionStage,
    ProgressEvent,
    QuizRequest,
)


def test_authenticated_context_and_progress_serialize_without_framework_objects():
    context = AppContext("17", ("42",))
    assert asdict(context) == {"user_id": "17", "active_document_ids": ("42",)}
    event = ProgressEvent("trace", IngestionStage.PARSING, 1, 2)
    assert asdict(event)["stage"] == "PARSING"


@pytest.mark.parametrize("identity", ["", " ", None, 17])
def test_invalid_identity(identity):
    with pytest.raises(ValueError):
        AppContext(identity)


@pytest.mark.parametrize("count", [0, -1, 16, True, 1.5])
def test_quiz_request_limits(count):
    with pytest.raises(ValueError):
        QuizRequest(AppContext("17"), count)


def test_empty_question_and_invalid_progress():
    with pytest.raises(ValueError):
        AnswerRequest(AppContext("17"), " ")
    with pytest.raises(ValueError):
        ProgressEvent("trace", IngestionStage.PARSING, 3, 2)
