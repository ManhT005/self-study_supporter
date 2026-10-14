import uuid
import hashlib

from evaluation.rag_only import answer_from_chunks
from study_supporter.application.contracts.agent import AgentResult, RetrievalCall
from study_supporter.application.contracts.context import AppContext
from study_supporter.application.contracts.learning import AnswerRequest
from study_supporter.application.contracts.retrieval import RetrievalQuery
from study_supporter.application.ports.llm import LLMAdapter
from study_supporter.application.ports.retrieval import EvidenceRetrievalPort
from study_supporter.domain.errors import EvidenceNotFound


class RagOnlyAdapter:
    def __init__(
        self, context: AppContext, llm: LLMAdapter, retriever: EvidenceRetrievalPort, top_k: int = 3
    ):
        self.context, self.llm, self.retriever, self.top_k = context, llm, retriever, top_k

    def execute(self, request: AnswerRequest) -> AgentResult:
        if request.context != self.context:
            raise EvidenceNotFound("Document not found")
        evidence = tuple(
            self.retriever.execute(
                RetrievalQuery(
                    request.context.user_id,
                    request.context.active_document_ids,
                    request.question,
                    self.top_k,
                )
            )
        )
        return AgentResult(
            answer_from_chunks(request.question, evidence, self.llm),
            evidence,
            uuid.uuid4().hex,
            steps=1,
            retrieval_calls=(
                RetrievalCall(
                    hashlib.sha256(request.question.encode("utf-8")).hexdigest(),
                    self.top_k,
                    tuple(e.chunk_id for e in evidence),
                ),
            ),
        )
