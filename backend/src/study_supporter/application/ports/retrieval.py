from collections.abc import Sequence
from typing import Protocol

from study_supporter.application.contracts.retrieval import Evidence, RetrievalQuery


class RetrieverPort(Protocol):
    def retrieve(self, query: RetrievalQuery) -> Sequence[Evidence]: ...


class EvidenceRetrievalPort(Protocol):
    def execute(self, query: RetrievalQuery) -> Sequence[Evidence]: ...


class DocumentAccessPort(Protocol):
    def owns(self, user_id: str, document_id: str) -> bool: ...


class EmbeddingPort(Protocol):
    @property
    def model_id(self) -> str: ...
    @property
    def dimension(self) -> int: ...
    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...
