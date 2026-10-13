from collections.abc import Sequence

from study_supporter.application.contracts.retrieval import Evidence, RetrievalQuery
from study_supporter.application.ports.retrieval import (
    DocumentAccessPort,
    RetrieverPort,
)
from study_supporter.domain.errors import EvidenceNotFound


class RetrieveEvidenceUseCase:
    def __init__(self, access: DocumentAccessPort, retriever: RetrieverPort):
        self.access = access
        self.retriever = retriever

    def execute(self, query: RetrievalQuery) -> Sequence[Evidence]:
        if not all(self.access.owns(query.user_id, doc) for doc in query.document_ids):
            raise EvidenceNotFound("Document not found")
        evidence = self.retriever.retrieve(query)
        if any(item.document_id not in query.document_ids for item in evidence):
            raise EvidenceNotFound("Evidence outside requested documents")
        return evidence[: query.top_k]
