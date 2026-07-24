from src.agent.tools.base import BaseTool
from src.memory.progress_db import ProgressDB


class GetProgressTool(BaseTool):
    name = "get_progress"
    description = "Lấy tiến độ học tập hiện tại của học sinh (số quiz đã làm, điểm số trung bình, các chủ đề đã học)."
    param_descriptions = {
        "user_id": "ID của học sinh cần tra tiến độ",
    }

    def __init__(self, progress_db: ProgressDB):
        self.progress_db = progress_db

    def run(self, user_id: str) -> str:
        summary = self.progress_db.get_summary(user_id)
        if summary["total_attempts"] == 0:
            return f"Học sinh '{user_id}' chưa làm quiz nào."

        return (
            f"Học sinh '{user_id}' đã làm {summary['total_attempts']} câu hỏi, "
            f"đúng {summary['correct']} câu (độ chính xác {summary['accuracy']}%). "
            f"Các chủ đề đã học: {', '.join(summary['topics'])}."
        )