import chromadb
from src.rag.schemas import Chunk

class VectorStore:
    def __init__(self, persist_path: str = "data/chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_path)
        self.documents = self.client.get_or_create_collection("documents")
        self.user_memory = self.client.get_or_create_collection("user_memory")

    def add_chunks(self, chunks: list[Chunk], embeddings: list[list[float]]):
        """
        Lưu chunks + embeddings vào collection 'documents'.
        Dùng chunk_id làm ChromaDB id, metadata gồm source/page_start/page_end.
        """
        # TODO: gọi self.documents.add(
        #   ids=[...],           # chunk.chunk_id
        #   embeddings=[...],    # vector tương ứng
        #   documents=[...],     # chunk.text
        #   metadatas=[...]      # dict {"source":..., "page_start":..., "page_end":...}
        # )
        #==================================================
        # chunks
        #     │
        #     ▼
        # chunk_id

        # text

        # metadata

        # embedding

        #     │
        #     ▼

        # documents.add()
        
        self.documents.upsert(
            ids=[
                chunk.chunk_id
                for chunk in chunks
            ],

            embeddings = embeddings,

            documents=[
                chunk.text for chunk in chunks
            ],

            metadatas=[
                {
                    "source": chunk.source,
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                }
                for chunk in chunks
            ]
        )


    def count(self) -> int:
        return self.documents.count()
    
    def get_existing_ids(self, ids: list[str]) -> set[str]:
        """Trả về tập chunk_id nào trong danh sách `ids` đã tồn tại trong DB."""
        if not ids:
            return set()
        existing = self.documents.get(ids=ids)
        return set(existing["ids"])