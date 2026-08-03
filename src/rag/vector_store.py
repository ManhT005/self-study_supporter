import os
import chromadb

from src.rag.schemas import Chunk


class VectorStore:
    def __init__(self, persist_path: str = "data/chroma_db", collection_name: str = "documents"):
        """
        collection_name: do caller quyết định (ví dụ f"documents_{document_id}")
        — mỗi tài liệu 1 collection riêng, cách ly hoàn toàn giữa các tài liệu/user,
        không phụ thuộc filter metadata (an toàn hơn khi chunk_id có thể trùng
        giữa 2 tài liệu khác nhau do tính từ content hash).

        Nếu có biến môi trường CHROMA_SERVER_HOST, kết nối tới ChromaDB server
        thật (self-host, có persistent volume) thay vì lưu file cục bộ.
        """
        self.persist_path = persist_path

        chroma_host = os.getenv("CHROMA_SERVER_HOST")
        if chroma_host:
            chroma_port = int(os.getenv("CHROMA_SERVER_PORT", "8000"))
            self.client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
        else:
            self.client = chromadb.PersistentClient(path=persist_path)

        self.documents = self.client.get_or_create_collection(collection_name)
        self.user_memory = self.client.get_or_create_collection("user_memory")

    def get_existing_ids(self, ids: list[str]) -> set[str]:
        if not ids:
            return set()
        existing = self.documents.get(ids=ids)
        return set(existing["ids"])

    def add_chunks(self, chunks: list[Chunk], embeddings: list[list[float]]):
        self.documents.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            embeddings=embeddings,
            documents=[chunk.text for chunk in chunks],
            metadatas=[
                {"source": chunk.source, "page_start": chunk.page_start, "page_end": chunk.page_end}
                for chunk in chunks
            ],
        )

    def count(self) -> int:
        return self.documents.count()

    def load_all_chunks(self) -> list[Chunk]:
        data = self.documents.get(include=["documents", "metadatas"])
        chunks = []
        for chunk_id, text, meta in zip(data["ids"], data["documents"], data["metadatas"]):
            chunks.append(Chunk(
                chunk_id=chunk_id,
                source=meta["source"],
                page_start=meta["page_start"],
                page_end=meta["page_end"],
                text=text,
                sentence_count=0,
            ))
        return chunks