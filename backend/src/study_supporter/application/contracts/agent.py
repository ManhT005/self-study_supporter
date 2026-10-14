"""Framework-independent execution results; never expose a reasoning scratchpad."""

from dataclasses import dataclass
from enum import Enum

from study_supporter.application.contracts.retrieval import Evidence


class AgentStatus(str, Enum):
    COMPLETED = "completed"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True)
class AgentUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


@dataclass(frozen=True)
class ToolCall:
    name: str
    # Legacy text dispatch does not prove schema validation or tool success.
    validation: str = "not_observed"


@dataclass(frozen=True)
class RetrievalCall:
    query_sha256: str
    top_k: int
    chunk_ids: tuple[str, ...]


@dataclass(frozen=True)
class AgentResult:
    answer: str
    evidences: tuple[Evidence, ...]
    trace_id: str
    status: AgentStatus = AgentStatus.COMPLETED
    steps: int = 0
    tool_calls: tuple[ToolCall, ...] = ()
    usage: AgentUsage | None = None
    # Unknown is distinct from a measured refusal or a measured non-refusal.
    abstained: bool | None = None
    retrieval_calls: tuple[RetrievalCall, ...] = ()

    def __post_init__(self):
        if not isinstance(self.answer, str) or not self.trace_id or self.steps < 0:
            raise ValueError("Invalid agent result")
        if any(
            not isinstance(value, tuple)
            for value in (self.evidences, self.tool_calls, self.retrieval_calls)
        ):
            raise ValueError("Agent result collections must be immutable tuples")
