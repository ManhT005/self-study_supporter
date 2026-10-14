import uuid
from study_supporter.application.contracts.learning import AnswerResult
from study_supporter.domain.errors import EvidenceNotFound


class AnswerQuestionUseCase:
    def __init__(self, runner, evidence_tool):
        self.runner, self.evidence_tool = runner, evidence_tool

    def execute(self, request):
        if request.context != self.evidence_tool.context:
            raise EvidenceNotFound("Document not found")
        self.evidence_tool.last_evidence = []
        state = self.runner.run(request.question)
        return AnswerResult(
            state.final_answer, tuple(self.evidence_tool.last_evidence), uuid.uuid4().hex
        )
