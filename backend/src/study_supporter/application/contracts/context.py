from dataclasses import dataclass


@dataclass(frozen=True)
class AppContext:
    """Created by authentication, never populated from model tool arguments."""

    user_id: str
    active_document_ids: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.user_id, str) or not self.user_id.strip():
            raise ValueError("Authenticated identity is required")
        if any(not isinstance(doc, str) or not doc.strip() for doc in self.active_document_ids):
            raise ValueError("Invalid document scope")
