from src.agent.tools.base import BaseTool

# Stub tạm — Sprint 4 sẽ thay bằng SQLAlchemy query thật vào bảng progress SQLite.
_progress_store: dict[str, dict] = {}


class GetProgressTool(BaseTool):
    name = "get_progress"
    description = "Lấy tiến độ học tập hiện tại của học sinh (số quiz đã làm, điểm số trung bình)."
    param_descriptions = {
        "user_id": "ID của học sinh cần tra tiến độ",
    }

    def run(self, user_id: str) -> str:
        progress = _progress_store.get(user_id)
        if progress is None:
            return f"Chưa có dữ liệu tiến độ cho user '{user_id}' (học sinh mới)."
        return f"Tiến độ của '{user_id}': {progress}"