from dataclasses import asdict

from study_supporter.application.contracts.context import AppContext
from study_supporter.application.contracts.learning import AnswerRequest, AnswerResult
from study_supporter.application.ports.agent import AgentPort
from study_supporter.domain.errors import EvidenceNotFound


class AnswerQuestionUseCase:
    def __init__(self, agent: AgentPort, context: AppContext):
        self.agent, self.context = agent, context

    def execute(self, request: AnswerRequest) -> AnswerResult:
        if request.context != self.context:
            raise EvidenceNotFound("Document not found")
        result = self.agent.execute(request)
        if any(e.document_id not in self.context.active_document_ids for e in result.evidences):
            raise EvidenceNotFound("Evidence outside requested documents")
        return AnswerResult(
            result.answer,
            result.evidences,
            result.trace_id,
            asdict(result.usage) if result.usage is not None else None,
        )
