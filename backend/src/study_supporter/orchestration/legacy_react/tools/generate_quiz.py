from study_supporter.orchestration.legacy_react.tools.base import BaseTool
from study_supporter.application.use_cases.generate_quiz import GenerateQuizUseCase
from study_supporter.domain.assessment import QuizQuestion as QuizQuestion, QuizList as QuizList


class GenerateQuizTool(GenerateQuizUseCase, BaseTool):
    """Compatibility tool: all generation/validation lives in the use case."""

    pass
