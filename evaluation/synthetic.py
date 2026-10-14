"""Offline contract fixture, never a production provider or a model-quality benchmark."""

import hashlib
import json
import re
from pathlib import Path

from evaluation.adapters.rag_only import RagOnlyAdapter
from evaluation.errors import EvaluationFailure
from evaluation.rag_only import RAG_ONLY_PROMPT_TEMPLATE
from study_supporter.application.contracts.context import AppContext
from study_supporter.application.contracts.learning import AnswerRequest
from study_supporter.application.contracts.retrieval import Evidence
from study_supporter.application.ports.llm import ChatResponse
from study_supporter.application.use_cases.retrieve import RetrieveEvidenceUseCase
from study_supporter.orchestration.legacy_react.adapter import LegacyReActAdapter
from study_supporter.orchestration.legacy_react.orchestrator import ReActOrchestrator
from study_supporter.orchestration.legacy_react.tools.retrieve_evidence import RetrieveEvidenceTool

ABSTENTION = "Không tìm thấy thông tin liên quan trong tài liệu."
STOPWORDS = {
    "là",
    "gì",
    "của",
    "và",
    "có",
    "nào",
    "trong",
    "cho",
    "với",
    "một",
    "các",
    "bao",
    "nhiêu",
}


def _tokens(text):
    return set(re.findall(r"\w+", text.lower())) - STOPWORDS


class _SyntheticLLM:
    def __init__(self, top_k):
        self.top_k = top_k

    def chat(self, messages, system_prompt=None, **kwargs):
        text = messages[-1]["content"]
        if system_prompt:
            if "\nObservation:" in text:
                return ChatResponse(
                    text="Final Answer: " + text.split("\nObservation:", 1)[1].strip()
                )
            question = text.split("Câu hỏi: ", 1)[1].split("\n", 1)[0]
            return ChatResponse(
                text="Action: search_docs\nAction Input: "
                + json.dumps({"query": question, "top_k": self.top_k}, ensure_ascii=False)
            )
        context = text.split("Tài liệu tham khảo:\n", 1)[1].split("\n\nCâu hỏi:", 1)[0]
        return ChatResponse(text=ABSTENTION if context.startswith("(Không tìm") else context)


class SyntheticEnvironment:
    def __init__(self, corpus: Path, top_k: int):
        self.source_hash = "sha256:" + hashlib.sha256(corpus.read_bytes()).hexdigest()
        data = json.loads(corpus.read_text(encoding="utf-8"))
        self.owners, self.chunks, self.top_k = (
            data["owners"],
            tuple(Evidence(**c) for c in data["chunks"]),
            top_k,
        )
        self.retriever = RetrieveEvidenceUseCase(self, self)

    def owns(self, user_id, document_id):
        return self.owners.get(document_id) == user_id

    def retrieve(self, query):
        ranked = sorted(
            (e for e in self.chunks if e.document_id in query.document_ids),
            key=lambda e: (-len(_tokens(query.question) & _tokens(e.text)), e.chunk_id),
        )
        return [e for e in ranked if _tokens(query.question) & _tokens(e.text)][: query.top_k]

    def variant(self, name):
        if name not in {"rag_only", "legacy_react"}:
            raise ValueError("Unknown synthetic variant")

        def execute(case):
            if case.requires_history or case.category in {"quiz", "personalized"}:
                raise EvaluationFailure("INVALID_SCHEMA")
            if any(not self.owns(case.user_fixture, doc) for doc in case.document_ids):
                raise EvaluationFailure("AUTH_SCOPE")
            context = AppContext(case.user_fixture, case.document_ids)
            llm = _SyntheticLLM(self.top_k)
            adapter = (
                RagOnlyAdapter(context, llm, self.retriever, self.top_k)
                if name == "rag_only"
                else LegacyReActAdapter(context, llm, self.retriever, lambda: [])
            )
            return adapter.execute(AnswerRequest(context, case.question))

        return execute

    def prompt_hashes(self):
        # The smoke uses a search-only prompt; it is not the production four-tool baseline.
        prompt = ReActOrchestrator(
            _SyntheticLLM(self.top_k),
            [RetrieveEvidenceTool(self.retriever, AppContext("user_a", ("doc_a",)))],
        ).system_prompt
        return {
            "rag_only": hashlib.sha256(RAG_ONLY_PROMPT_TEMPLATE.encode("utf-8")).hexdigest(),
            "legacy_react": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        }
