from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Credentials(DTO):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=6, max_length=72)

    @field_validator("username")
    @classmethod
    def valid_username(cls, value):
        if len(value.strip()) < 3:
            raise ValueError("Username requires three characters")
        return value.strip()

    @field_validator("password")
    @classmethod
    def valid_password(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password exceeds bcrypt byte limit")
        return value


class Identity(DTO):
    username: str


class ErrorDTO(DTO):
    code: str
    message: str
    request_id: str


class DocumentDTO(DTO):
    id: int
    filename: str
    status: Literal["processing", "ready", "failed"]
    page_count: int | None
    chunk_count: int | None


class CitationDTO(DTO):
    chunk_id: str
    document_id: str
    text: str
    source: str
    page_start: int | None
    page_end: int | None
    score: float | None = None


class ChatRequest(DTO):
    question: str = Field(min_length=1, max_length=4000)
    mode: Literal["auto", "gemini", "ollama"] = "auto"

    @field_validator("question")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Question is empty")
        return value.strip()


class ChatResponse(DTO):
    answer: str
    citations: list[CitationDTO]
    trace_id: str


class ReaderChunk(DTO):
    chunk_id: str
    text: str
    page_start: int | None
    page_end: int | None


class QuizSetup(DTO):
    num_questions: int = Field(default=5, ge=1, le=15, strict=True)
    topic: str = Field(default="Chủ đề chung", min_length=1, max_length=200)
    mode: Literal["auto", "gemini", "ollama"] = "auto"


class QuizQuestionDTO(DTO):
    question: str
    options: tuple[str, str, str, str]
    topic: str


class QuizDTO(DTO):
    quiz_id: str
    questions: list[QuizQuestionDTO]


class QuizSubmit(DTO):
    question_index: int = Field(ge=0, strict=True)
    selected_index: int = Field(ge=0, le=3, strict=True)


class GradeDTO(DTO):
    is_correct: bool
    correct_index: int
    explanation: str


class ProgressDTO(DTO):
    total_attempts: int
    correct: int
    accuracy: float | None
    topics: list[str]


class PathDTO(DTO):
    concepts: list[str]
    has_cycle: bool


class ModeRequest(DTO):
    mode: Literal["auto", "gemini", "ollama"] = "auto"


class NoteRequest(DTO):
    note: str = Field(min_length=1, max_length=4000)


class MessageDTO(DTO):
    message: str
