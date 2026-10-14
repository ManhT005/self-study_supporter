from study_supporter.application.use_cases.learning import SaveNoteUseCase
from study_supporter.application.contracts.context import AppContext
from study_supporter.application.ports.tool import BaseTool


class SaveNoteTool(BaseTool):
    name = "save_note"
    description = "Lưu lại 1 ghi chú/điểm cần nhớ về quá trình học tập của học sinh, để dùng lại ở phiên học sau."
    param_descriptions = {
        "note": "Nội dung ghi chú cần lưu",
    }

    def __init__(self, long_term_memory: SaveNoteUseCase, user_id: str):
        self.long_term_memory = long_term_memory
        self.user_id = user_id

    def run(self, note: str) -> str:
        note_id = self.long_term_memory.execute(AppContext(self.user_id), note)
        return f"Đã lưu ghi chú (id: {note_id}) cho học sinh '{self.user_id}': {note}"
