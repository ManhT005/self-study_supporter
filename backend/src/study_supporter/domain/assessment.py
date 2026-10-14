from pydantic import BaseModel, Field


class QuizQuestion(BaseModel):
    question: str
    options: list[str] = Field(min_length=4, max_length=4)
    correct_answer_index: int = Field(strict=True, ge=0, le=3)
    explanation: str


class QuizList(BaseModel):
    questions: list[QuizQuestion]
