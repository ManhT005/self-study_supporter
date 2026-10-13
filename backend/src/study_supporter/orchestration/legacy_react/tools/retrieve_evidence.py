from study_supporter.application.contracts.retrieval import RetrievalQuery
from study_supporter.orchestration.legacy_react.tools.base import BaseTool


class RetrieveEvidenceTool(BaseTool):
    name = "search_docs"
    description = "Tìm kiếm thông tin liên quan trong tài liệu học tập đã upload."
    param_descriptions = {
        "query": "Câu hỏi hoặc từ khóa cần tìm kiếm trong tài liệu",
        "top_k": "Số lượng đoạn văn bản liên quan cần trả về (mặc định 3)",
    }

    def __init__(self, retriever, context):
        self.retriever, self.context = retriever, context
        self.last_evidence = []

    def run(self, query: str, top_k: int = 3) -> str:
        self.last_evidence = []
        if not query.strip():
            return "Lỗi: câu truy vấn rỗng, không thể tìm kiếm."
        self.last_evidence = list(
            self.retriever.execute(
                RetrievalQuery(
                    self.context.user_id, self.context.active_document_ids, query.strip(), top_k
                )
            )
        )
        if not self.last_evidence:
            return "Không tìm thấy thông tin liên quan trong tài liệu."
        result = []
        for evidence in self.last_evidence:
            page = (
                f"trang {evidence.page_start}"
                if evidence.page_start == evidence.page_end
                else f"trang {evidence.page_start}-{evidence.page_end}"
            )
            result.append(f"[Nguồn: {evidence.source}, {page}]\n{evidence.text}")
        return "\n\n".join(result)
