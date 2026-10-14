from study_supporter.application.ports.tool import BaseTool
from study_supporter.infrastructure.retrieval.hybrid_adapter import hybrid_search
from study_supporter.application.contracts.retrieval import Evidence


class SearchDocsTool(BaseTool):
    name = "search_docs"
    description = "Tìm kiếm thông tin liên quan trong tài liệu học tập đã upload."
    param_descriptions = {
        "query": "Câu hỏi hoặc từ khóa cần tìm kiếm trong tài liệu",
        "top_k": "Số lượng đoạn văn bản liên quan cần trả về (mặc định 3)",
    }

    def __init__(self, vector_store, bm25_index, embed_query_fn, document_id: str | None = None):
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.embed_query_fn = embed_query_fn
        self.document_id = document_id
        self.last_evidence: list[Evidence] = []

    def run(self, query: str, top_k: int = 3) -> str:
        self.last_evidence = []
        query = query.strip()
        if not query:
            return "Lỗi: câu truy vấn rỗng, không thể tìm kiếm."

        chunks = hybrid_search(
            query=query,
            vector_store=self.vector_store,
            bm25_index=self.bm25_index,
            embed_query_fn=self.embed_query_fn,
            top_k=top_k,
        )

        if not chunks:
            return "Không tìm thấy thông tin liên quan trong tài liệu."

        results = []
        for chunk in chunks:
            if (
                self.document_id
                and chunk.chunk_id
                and chunk.source
                and chunk.page_start
                and chunk.page_end
            ):
                self.last_evidence.append(
                    Evidence(
                        chunk.chunk_id,
                        self.document_id,
                        chunk.text,
                        chunk.source,
                        chunk.page_start,
                        chunk.page_end,
                    )
                )
            page = (
                f"trang {chunk.page_start}"
                if chunk.page_start == chunk.page_end
                else f"trang {chunk.page_start}-{chunk.page_end}"
            )
            results.append(f"[Nguồn: {chunk.source}, {page}]\n{chunk.text}")

        return "\n\n".join(results)
