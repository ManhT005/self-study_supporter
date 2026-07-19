from src.agent.tools.base import BaseTool
from src.rag.hybrid_retriever import hybrid_search


class SearchDocsTool(BaseTool):
    name = "search_docs"
    description = "Tìm kiếm thông tin liên quan trong tài liệu học tập đã upload."
    param_descriptions = {
        "query": "Câu hỏi hoặc từ khóa cần tìm kiếm trong tài liệu",
        "top_k": "Số lượng đoạn văn bản liên quan cần trả về (mặc định 3)",
    }

    def __init__(self, vector_store, bm25_index, embed_query_fn):
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.embed_query_fn = embed_query_fn

    def run(self, query: str, top_k: int = 3) -> str:
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
            page = (
                f"trang {chunk.page_start}"
                if chunk.page_start == chunk.page_end
                else f"trang {chunk.page_start}-{chunk.page_end}"
            )
            results.append(f"[Nguồn: {chunk.source}, {page}]\n{chunk.text}")

        return "\n\n".join(results)