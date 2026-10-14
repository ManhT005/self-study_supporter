from study_supporter.domain.assessment import QuizQuestion
from study_supporter.application.contracts.learning import QuizGrade


class SubmitQuizUseCase:
    def __init__(self, documents, progress):
        self.documents, self.progress = documents, progress

    def execute(self, context, document_id, question, selected_index):
        self.documents.get(context.user_id, document_id)
        validated = QuizQuestion(
            question=question["question"],
            options=question["options"],
            correct_answer_index=question["correct_index"],
            explanation=question.get("explanation", ""),
        )
        if type(selected_index) is not int or not 0 <= selected_index <= 3:
            raise ValueError("Invalid selected option")
        correct = selected_index == validated.correct_answer_index
        self.progress.record_attempt(
            context.user_id,
            question.get("topic", "Chủ đề chung"),
            validated.question,
            correct,
            document_id,
        )
        return QuizGrade(correct, validated.correct_answer_index, validated.explanation)


class SaveNoteUseCase:
    def __init__(self, notes):
        self.notes = notes

    def execute(self, context, note):
        return self.notes.save_note(context.user_id, note)


class GetProgressUseCase:
    def __init__(self, progress):
        self.progress = progress

    def execute(self, context):
        return self.progress.get_summary(context.user_id)
