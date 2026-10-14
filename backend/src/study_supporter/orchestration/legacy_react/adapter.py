"""Request-local bridge around the unchanged legacy parser, prompts and tool loop."""

import uuid
import hashlib
from collections.abc import Callable, Sequence

from study_supporter.application.contracts.agent import (
    AgentResult,
    AgentStatus,
    RetrievalCall,
    ToolCall,
)
from study_supporter.application.contracts.context import AppContext
from study_supporter.application.contracts.learning import AnswerRequest
from study_supporter.application.contracts.retrieval import Evidence, RetrievalQuery
from study_supporter.application.ports.llm import LLMAdapter
from study_supporter.application.ports.tool import BaseTool
from study_supporter.application.ports.retrieval import EvidenceRetrievalPort
from study_supporter.domain.errors import EvidenceNotFound
from study_supporter.orchestration.legacy_react.orchestrator import ReActOrchestrator
from study_supporter.orchestration.legacy_react.tools.retrieve_evidence import RetrieveEvidenceTool


class _EvidenceRecorder:
    def __init__(self, retriever: EvidenceRetrievalPort):
        self.retriever = retriever
        self.evidences: dict[tuple[str, str], Evidence] = {}
        self.calls: list[RetrievalCall] = []

    def execute(self, query: RetrievalQuery) -> Sequence[Evidence]:
        evidence = tuple(self.retriever.execute(query))
        self.calls.append(
            RetrievalCall(
                hashlib.sha256(query.question.encode("utf-8")).hexdigest(),
                query.top_k,
                tuple(e.chunk_id for e in evidence),
            )
        )
        for item in evidence:
            self.evidences.setdefault((item.document_id, item.chunk_id), item)
        return evidence


class LegacyReActAdapter:
    def __init__(
        self,
        context: AppContext,
        llm: LLMAdapter,
        retriever: EvidenceRetrievalPort,
        tools_factory: Callable[[], Sequence[BaseTool]],
    ):
        self.context, self.llm = context, llm
        self.retriever, self.tools_factory = retriever, tools_factory

    def execute(self, request: AnswerRequest) -> AgentResult:
        if request.context != self.context:
            raise EvidenceNotFound("Document not found")
        recorder = _EvidenceRecorder(self.retriever)
        tools = [RetrieveEvidenceTool(recorder, self.context), *self.tools_factory()]
        known_tools = {tool.name for tool in tools}
        state = ReActOrchestrator(self.llm, tools).run(request.question)
        return AgentResult(
            answer=state.final_answer or "",
            evidences=tuple(recorder.evidences.values()),
            trace_id=uuid.uuid4().hex,
            status=AgentStatus.COMPLETED if state.is_done else AgentStatus.INCOMPLETE,
            steps=state.iteration,
            tool_calls=tuple(
                ToolCall(entry.tool_name if entry.tool_name in known_tools else "unknown_tool")
                for entry in state.scratchpad
                if entry.type == "action" and entry.tool_name
            ),
            retrieval_calls=tuple(recorder.calls),
        )
