from src.agent.tools.base import BaseTool
from src.memory.long_term import LongTermMemory


class SaveNoteTool(BaseTool):
    name = "save_note"
    description = "Lưu lại 1 ghi chú/điểm cần nhớ về quá trình học tập của học sinh, để dùng lại ở phiên học sau."
    param_descriptions = {
        "user_id": "ID của học sinh",
        "note": "Nội dung ghi chú cần lưu",
    }

    def __init__(self, long_term_memory: LongTermMemory):
        self.long_term_memory = long_term_memory

    def run(self, user_id: str, note: str) -> str:
        note_id = self.long_term_memory.save_note(user_id, note)
        return f"Đã lưu ghi chú (id: {note_id}) cho học sinh '{user_id}': {note}"