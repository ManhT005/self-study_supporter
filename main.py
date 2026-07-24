import os
from dotenv import load_dotenv
from google import genai

from src.rag.pdf_parser import parse_pdf
from src.rag.chunker import (
    compute_breakpoints,
    compute_distances,
    embed_sentences,
    flatten_pages_to_sentences,
    group_sentences_into_chunks,
)
from src.rag.embedder import embed_chunks
from src.rag.vector_store import VectorStore
from src.rag.bm25_index import BM25Index
from src.rag.hybrid_retriever import hybrid_search
from src.rag.embedding_provider import GeminiEmbeddingProvider, LocalEmbeddingProvider  # , LocalEmbeddingProvider


if __name__ == "__main__":
    load_dotenv()
    os.environ["HF_TOKEN"] = os.getenv("HF_TOKEN", "")
    gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    # 🔀 Chỉ cần đổi dòng này để swap provider (Gemini <-> Local)
    # provider = GeminiEmbeddingProvider(gemini_client)
    provider = LocalEmbeddingProvider()

    # ---------- 1. Parse + Chunk ----------
    pages = parse_pdf("data/demo_docs/DSA.pdf")
    sentences = flatten_pages_to_sentences(pages)

    sample = sentences[:]  # full document
    sample = embed_sentences(sample, provider)  # <-- truyền provider, KHÔNG truyền client

    distances = compute_distances(sample)
    breakpoints = compute_breakpoints(sample, distances, percentile=95)
    chunks = group_sentences_into_chunks(sample, breakpoints, min_sentences=2, max_chars=800)

    print(f"Tổng số câu: {len(sentences)}")
    print(f"Tổng số chunk: {len(chunks)}")

    # ---------- 2. Embed chunk + lưu ChromaDB (idempotent) ----------
    store = VectorStore()

    existing_ids = store.get_existing_ids([c.chunk_id for c in chunks])
    new_chunks = [c for c in chunks if c.chunk_id not in existing_ids]

    if new_chunks:
        vectors = embed_chunks(new_chunks, provider)  # <-- truyền provider
        store.add_chunks(new_chunks, vectors)
        print(f"Đã embed và lưu {len(new_chunks)} chunk mới ({len(chunks) - len(new_chunks)} đã có, bỏ qua).")
    else:
        print("Tất cả chunk đã tồn tại trong DB, không gọi API embedding.")

    # ---------- 3. Hybrid Search ----------
    def embed_query_fn(query: str) -> list[float]:
        return provider.embed([query], task_type="RETRIEVAL_QUERY")[0]

    bm25_index = BM25Index(chunks)

    query = "Dữ liệu là gì?"
    top_chunks = hybrid_search(query, store, bm25_index, embed_query_fn, top_k=3)

    print(f"\n--- Kết quả cho câu hỏi: '{query}' ---\n")
    for c in top_chunks:
        print(f"--- {c.chunk_id} (p.{c.page_start}-{c.page_end}) ---")
        print(c.text[:200])
        print()