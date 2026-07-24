class ShortTermMemory:
    """Lưu lịch sử hội thoại trong 1 phiên làm việc — thuần RAM, không persist."""

    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self.history: list[dict] = []  # [{"role": "user"/"assistant", "content": str}, ...]

    def add_turn(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
        # Giữ tối đa max_turns lượt gần nhất, tránh context quá dài khi gửi cho LLM
        if len(self.history) > self.max_turns * 2:  # *2 vì mỗi lượt có cả user+assistant
            self.history = self.history[-self.max_turns * 2:]

    def get_history(self) -> list[dict]:
        return self.history.copy()

    def clear(self) -> None:
        self.history = []