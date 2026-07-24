from pydantic import BaseModel, Field
from typing import Literal


class ScratchpadEntry(BaseModel):
    """1 dòng trong 'nhật ký suy luận' của Agent — Thought, Action, hoặc Observation."""
    type: Literal["thought", "action", "observation"]
    content: str
    tool_name: str | None = None
    tool_args: dict | None = None


class AgentState(BaseModel):
    """
    Bộ nhớ làm việc (working memory) của Agent trong 1 lượt hỏi-đáp.
    Không phải long-term memory (đó là Sprint 4) — state này chỉ sống trong
    phạm vi 1 vòng lặp ReAct, từ lúc nhận câu hỏi tới lúc ra Final Answer.
    """
    user_query: str
    scratchpad: list[ScratchpadEntry] = Field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 5
    final_answer: str | None = None
    is_done: bool = False

    def add_thought(self, content: str) -> None:
        self.scratchpad.append(ScratchpadEntry(type="thought", content=content))

    def add_action(self, tool_name: str, tool_args: dict) -> None:
        self.scratchpad.append(ScratchpadEntry(
            type="action",
            content=f"{tool_name}({tool_args})",
            tool_name=tool_name,
            tool_args=tool_args,
        ))

    def add_observation(self, content: str) -> None:
        self.scratchpad.append(ScratchpadEntry(type="observation", content=content))

    def render_scratchpad(self) -> str:
        """
        Render toàn bộ lịch sử suy luận thành text, để đưa vào prompt cho LLM
        ở vòng lặp kế tiếp — đây là cách 'nhắc' LLM nhớ nó đã làm gì rồi.
        """
        lines = []
        for entry in self.scratchpad:
            if entry.type == "thought":
                lines.append(f"Thought: {entry.content}")
            elif entry.type == "action":
                lines.append(f"Action: {entry.tool_name}")
                lines.append(f"Action Input: {entry.tool_args}")
            elif entry.type == "observation":
                lines.append(f"Observation: {entry.content}")
        return "\n".join(lines)

    def is_max_iterations_reached(self) -> bool:
        return self.iteration >= self.max_iterations