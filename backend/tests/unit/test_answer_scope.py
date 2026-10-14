from unittest.mock import Mock

import pytest

from study_supporter.application.contracts.context import AppContext
from study_supporter.application.contracts.agent import AgentResult, AgentUsage
from study_supporter.application.contracts.learning import AnswerRequest
from study_supporter.application.contracts.retrieval import Evidence
from study_supporter.application.use_cases.answer_question import AnswerQuestionUseCase
from study_supporter.domain.errors import EvidenceNotFound


def test_answer_rejects_foreign_context_and_never_prefixes_identity_to_query():
    agent = Mock()
    agent.execute.return_value = AgentResult("Fixture answer", (), "trace")
    context = AppContext("A", ("doc-a",))
    service = AnswerQuestionUseCase(agent, context)
    with pytest.raises(EvidenceNotFound):
        service.execute(AnswerRequest(AppContext("B", ("doc-a",)), "question"))
    agent.execute.assert_not_called()
    result = service.execute(AnswerRequest(context, "question"))
    agent.execute.assert_called_once_with(AnswerRequest(context, "question"))
    assert result.answer == "Fixture answer" and result.evidences == () and result.trace_id


def test_answer_preserves_agent_trace_usage_and_rejects_foreign_evidence():
    agent = Mock()
    context = AppContext("A", ("doc-a",))
    agent.execute.return_value = AgentResult("answer", (), "correlation", usage=AgentUsage(3, 4))
    service = AnswerQuestionUseCase(agent, context)
    result = service.execute(AnswerRequest(context, "question"))
    assert result.trace_id == "correlation"
    assert result.usage == {"input_tokens": 3, "output_tokens": 4, "cost_usd": None}
    agent.execute.return_value = AgentResult(
        "answer", (Evidence("foreign", "doc-b", "secret", "b.pdf", 1, 1),), "trace"
    )
    with pytest.raises(EvidenceNotFound):
        service.execute(AnswerRequest(context, "question"))
