from unittest.mock import Mock

import pytest

from study_supporter.application.contracts.context import AppContext
from study_supporter.application.use_cases.learning import SubmitQuizUseCase


def test_scoring_and_recording_use_authenticated_context():
    documents, progress = Mock(), Mock()
    case = SubmitQuizUseCase(documents, progress)
    question = dict(question="Q?", options=["a", "b", "c", "d"], correct_index=2, explanation="why")
    grade = case.execute(AppContext("B", ("9",)), 9, question, 1)
    assert not grade.is_correct
    documents.get.assert_called_once_with("B", 9)
    assert progress.record_attempt.call_args.args[0] == "B"
    assert progress.record_attempt.call_args.args[3] is False


def test_invalid_question_is_never_recorded():
    documents, progress = Mock(), Mock()
    with pytest.raises(ValueError):
        SubmitQuizUseCase(documents, progress).execute(
            AppContext("B"), 9, dict(question="Q?", options=["a", "b"], correct_index=0), 0
        )
    progress.record_attempt.assert_not_called()
