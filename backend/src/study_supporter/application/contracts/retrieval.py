from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalQuery:
    """user_id must originate from authenticated context, never from model args."""

    user_id: str
    document_ids: tuple[str, ...]
    question: str
    top_k: int = 5

    def __post_init__(self):
        if not isinstance(self.user_id, str) or not self.user_id.strip():
            raise ValueError("Authenticated user_id is required")
        if not self.document_ids or any(not doc for doc in self.document_ids):
            raise ValueError("At least one document_id is required")
        if not self.question.strip():
            raise ValueError("Question must not be empty")
        if type(self.top_k) is not int or self.top_k < 1:
            raise ValueError("top_k must be a positive integer")


@dataclass(frozen=True)
class Evidence:
    chunk_id: str
    document_id: str
    text: str
    source: str
    page_start: int | None
    page_end: int | None
    score: float | None = None
