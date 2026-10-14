from collections.abc import Callable, Sequence
from typing import Protocol

from study_supporter.application.contracts.agent import AgentResult
from study_supporter.application.contracts.learning import AnswerRequest
from study_supporter.application.contracts.context import AppContext
from study_supporter.application.ports.llm import LLMAdapter
from study_supporter.application.ports.retrieval import EvidenceRetrievalPort
from study_supporter.application.ports.tool import BaseTool

AgentToolsFactory = Callable[[], Sequence[BaseTool]]


class AgentPort(Protocol):
    def execute(self, request: AnswerRequest) -> AgentResult: ...


class AgentFactory(Protocol):
    def __call__(
        self,
        context: AppContext,
        llm: LLMAdapter,
        retriever: EvidenceRetrievalPort,
        tools_factory: AgentToolsFactory,
    ) -> AgentPort: ...
