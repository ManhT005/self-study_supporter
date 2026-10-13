from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from study_supporter.application.contracts.context import AppContext
from study_supporter.application.contracts.learning import AnswerRequest
from study_supporter.application.use_cases.answer_question import AnswerQuestionUseCase
from study_supporter.domain.errors import EvidenceNotFound


def test_answer_rejects_foreign_context_and_never_prefixes_identity_to_query():
    runner = Mock()
    runner.run.return_value = SimpleNamespace(final_answer="Fixture answer")
    context = AppContext("A", ("doc-a",))
    evidence = SimpleNamespace(context=context, last_evidence=["stale citation"])
    service = AnswerQuestionUseCase(runner, evidence)
    with pytest.raises(EvidenceNotFound):
        service.execute(AnswerRequest(AppContext("B", ("doc-a",)), "question"))
    runner.run.assert_not_called()
    result = service.execute(AnswerRequest(context, "question"))
    runner.run.assert_called_once_with("question")
    assert result.answer == "Fixture answer" and result.evidences == () and result.trace_id
