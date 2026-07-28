import uuid
from src.rag.vector_store import VectorStore


class LongTermMemory:
    """
    Lưu ghi chú/thông tin quan trọng vào ChromaDB collection 'user_memory',
    tách biệt hoàn toàn với collection 'documents' (nội dung tài liệu học tập).
    """

    def __init__(self, vector_store: VectorStore, embed_query_fn):
        self.vector_store = vector_store
        self.embed_query_fn = embed_query_fn  # dùng để embed cả lúc lưu lẫn lúc query

    def save_note(self, user_id: str, note: str) -> str:
        note_id = str(uuid.uuid4())[:12]
        embedding = self.embed_query_fn(note)

        self.vector_store.user_memory.upsert(
            ids=[note_id],
            embeddings=[embedding],
            documents=[note],
            metadatas=[{"user_id": user_id}],
        )
        return note_id

    def search_notes(self, user_id: str, query: str, top_k: int = 3) -> list[str]:
        query_embedding = self.embed_query_fn(query)

        results = self.vector_store.user_memory.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"user_id": user_id},  # chỉ tìm trong ghi chú của đúng user này
        )

        if not results["documents"] or not results["documents"][0]:
            return []
        return results["documents"][0]