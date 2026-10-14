from dataclasses import dataclass, field
from enum import Enum

from study_supporter.application.contracts.context import AppContext
from study_supporter.application.contracts.retrieval import Evidence


class IngestionStage(str, Enum):
    VALIDATING = "VALIDATING"
    PARSING = "PARSING"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    INDEXING = "INDEXING"
    READY = "READY"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ProgressEvent:
    trace_id: str
    stage: IngestionStage
    done: int = 0
    total: int = 0
    message: str = ""

    def __post_init__(self):
        if not self.trace_id or not 0 <= self.done <= self.total:
            raise ValueError("Invalid progress event")


@dataclass(frozen=True)
class IngestDocumentRequest:
    context: AppContext
    filename: str
    content: bytes = field(repr=False)
    mime: str | None = None


@dataclass(frozen=True)
class DocumentResult:
    document_id: int
    filename: str
    chunk_count: int
    page_count: int
    trace_id: str
    reused: bool = False


@dataclass(frozen=True)
class AnswerRequest:
    context: AppContext
    question: str

    def __post_init__(self):
        if not self.question.strip():
            raise ValueError("Question must not be empty")


@dataclass(frozen=True)
class AnswerResult:
    answer: str
    evidences: tuple[Evidence, ...]
    trace_id: str
    usage: dict | None = None


@dataclass(frozen=True)
class QuizRequest:
    context: AppContext
    num_questions: int = 1
    topic_label: str = "Chủ đề chung"
    topic_description: str = ""

    def __post_init__(self):
        if type(self.num_questions) is not int or not 1 <= self.num_questions <= 15:
            raise ValueError("Quiz requires 1–15 questions")


@dataclass(frozen=True)
class QuizGrade:
    is_correct: bool
    correct_index: int
    explanation: str
