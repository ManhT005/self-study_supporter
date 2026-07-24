from src.agent.tools.base import BaseTool

# Lưu tạm trong RAM — mất khi tắt chương trình. Sprint 4 sẽ thay bằng
# ChromaDB collection "user_memory" với đúng interface run() này, không
# cần sửa orchestrator.py hay cách Agent gọi tool.
_notes_store: dict[str, list[str]] = {}


class SaveNoteTool(BaseTool):
    name = "save_note"
    description = "Lưu lại 1 ghi chú/điểm cần nhớ về quá trình học tập của học sinh, để dùng lại ở phiên học sau."
    param_descriptions = {
        "user_id": "ID của học sinh",
        "note": "Nội dung ghi chú cần lưu",
    }

    def run(self, user_id: str, note: str) -> str:
        _notes_store.setdefault(user_id, []).append(note)
        return f"Đã lưu ghi chú cho user '{user_id}': {note}"