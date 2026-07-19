from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ChatResponse:
    text: str
    usage: dict | None = None          # {"input_tokens":.., "output_tokens":.., "total_tokens":..}
    finish_reason: str | None = None   # "stop" | "length" | "tool_calls" | ...
    tool_calls: list | None = None     # dự phòng cho Sprint 3 (ReAct Agent) — chưa dùng ở Sprint 2
    raw: object | None = None          # response gốc, "cửa thoát hiểm" khi cần field chưa map


class LLMAdapter(ABC):
    """
    Interface chung cho mọi LLM provider. Agent (Sprint 3) chỉ nói chuyện qua
    interface này — không biết và không cần biết đang chạy Gemini hay Ollama.
    """

    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        system_prompt: str | None = None,
        stop_sequences: list[str] | None = None,
    ) -> ChatResponse:
        """
        messages: [{"role": "user"|"assistant", "content": str}, ...]
        Trả về ChatResponse, không phải str thô — để mở rộng thêm field
        (usage, tool_calls...) mà không phải đổi lại mọi nơi gọi chat().
        """
        ...

    # --- Chỗ dành sẵn cho Sprint 3, CHƯA implement ở đây ---
    # def call_with_tools(self, messages, tools: list[dict], system_prompt=None) -> ChatResponse:
    #     """Sẽ thêm khi làm ReAct loop — không phải sửa lại GeminiClient/OllamaClient
    #     đã viết ở Sprint 2, chỉ cần bổ sung method mới vào class con."""
    #     raise NotImplementedError