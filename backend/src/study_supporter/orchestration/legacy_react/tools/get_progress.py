from study_supporter.application.use_cases.learning import GetProgressUseCase
from study_supporter.application.contracts.context import AppContext
from study_supporter.application.ports.tool import BaseTool


class GetProgressTool(BaseTool):
    name = "get_progress"
    description = "Lấy tiến độ học tập hiện tại của học sinh (số quiz đã làm, điểm số trung bình, các chủ đề đã học)."
    param_descriptions = {}

    def __init__(self, progress_db: GetProgressUseCase, user_id: str):
        self.progress_db = progress_db
        self.user_id = user_id

    def run(self) -> str:
        summary = self.progress_db.execute(AppContext(self.user_id))
        if summary["total_attempts"] == 0:
            return f"Học sinh '{self.user_id}' chưa làm quiz nào."

        return (
            f"Học sinh '{self.user_id}' đã làm {summary['total_attempts']} câu hỏi, "
            f"đúng {summary['correct']} câu (độ chính xác {summary['accuracy']}%). "
            f"Các chủ đề đã học: {', '.join(summary['topics'])}."
        )
