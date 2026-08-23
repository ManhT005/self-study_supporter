from src.agent.tools.base import BaseTool
from src.memory.long_term import LongTermMemory


class SaveNoteTool(BaseTool):
    name = "save_note"
    description = "Lưu lại 1 ghi chú/điểm cần nhớ về quá trình học tập của học sinh, để dùng lại ở phiên học sau."
    param_descriptions = {
        "note": "Nội dung ghi chú cần lưu",
    }

    def __init__(self, long_term_memory: LongTermMemory, user_id: str):
        self.long_term_memory = long_term_memory
        self.user_id = user_id

    def run(self, note: str) -> str:
        note_id = self.long_term_memory.save_note(self.user_id, note)
        return f"Đã lưu ghi chú (id: {note_id}) cho học sinh '{self.user_id}': {note}"