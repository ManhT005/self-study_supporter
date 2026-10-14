import uuid
from study_supporter.application.contracts.learning import AnswerResult


class AnswerQuestionUseCase:
    def __init__(self, runner, evidence_tool):
        self.runner, self.evidence_tool = runner, evidence_tool

    def execute(self, request):
        self.evidence_tool.last_evidence = []
        state = self.runner.run(request.question)
        return AnswerResult(
            state.final_answer, tuple(self.evidence_tool.last_evidence), uuid.uuid4().hex
        )
