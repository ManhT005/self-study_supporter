import hashlib

from study_supporter.application.contracts.agent import AgentUsage, RetrievalCall
from study_supporter.application.contracts.retrieval import RetrievalQuery
from study_supporter.domain.errors import EvidenceNotFound


class Telemetry:
    def __init__(self):
        self.evidences = {}
        self.retrieval_calls = []
        self.tool_calls = []
        self.usages = []

    def record_retrieval(self, query: RetrievalQuery, evidence):
        # Defense in depth even when an injected retriever violates its port contract.
        if any(item.document_id not in query.document_ids for item in evidence):
            raise EvidenceNotFound("Evidence outside requested documents")
        evidence = tuple(evidence[: query.top_k])
        self.retrieval_calls.append(
            RetrievalCall(
                hashlib.sha256(query.question.encode()).hexdigest(),
                query.top_k,
                tuple(item.chunk_id for item in evidence),
            )
        )
        for item in evidence:
            self.evidences.setdefault((item.document_id, item.chunk_id), item)
        return evidence

    def usage(self):
        if not self.usages or any(item is None for item in self.usages):
            return None
        return AgentUsage(
            input_tokens=sum(item["input_tokens"] for item in self.usages),
            output_tokens=sum(item["output_tokens"] for item in self.usages),
        )
