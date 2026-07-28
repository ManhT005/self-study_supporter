from src.rag.hybrid_retriever import hybrid_search
from src.llm.llm_adapter import LLMAdapter


RAG_ONLY_PROMPT_TEMPLATE = """Bạn là một AI Trợ Giảng. Dựa trên các đoạn tài liệu sau, hãy trả lời câu hỏi của học sinh một cách chính xác và đầy đủ. Nếu tài liệu không có thông tin liên quan, hãy nói rõ thay vì bịa đặt.

Tài liệu tham khảo:
{context}

Câu hỏi: {question}

Trả lời:"""


def answer_with_rag_only(
    question: str,
    vector_store,
    bm25_index,
    embed_query_fn,
    llm: LLMAdapter,
    top_k: int = 3,
) -> str:
    """
    Baseline: retrieve + generate 1 lần duy nhất. Không ReAct loop, không tool
    calling, không memory — dùng để so sánh với Agent+RAG (orchestrator.py).
    """
    chunks = hybrid_search(
        query=question,
        vector_store=vector_store,
        bm25_index=bm25_index,
        embed_query_fn=embed_query_fn,
        top_k=top_k,
    )

    if not chunks:
        context = "(Không tìm thấy tài liệu liên quan.)"
    else:
        context = "\n\n".join(
            f"[Nguồn: {c.source}, trang {c.page_start}-{c.page_end}]\n{c.text}"
            for c in chunks
        )

    prompt = RAG_ONLY_PROMPT_TEMPLATE.format(context=context, question=question)
    response = llm.chat([{"role": "user", "content": prompt}])
    return response.text