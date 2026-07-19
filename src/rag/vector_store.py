import chromadb
from src.rag.schemas import Chunk

class VectorStore:
    def __init__(self, persist_path: str = "data/chroma_db"):
        self.persist_path = persist_path
        self.client = chromadb.PersistentClient(path=persist_path)
        self.documents = self.client.get_or_create_collection("documents")
        self.user_memory = self.client.get_or_create_collection("user_memory")

    def save_provider_info(self, provider_name: str, dimension: int) -> None:
        info_path = os.path.join(self.persist_path, "provider_info.json")
        with open(info_path, "w") as f:
            json.dump({"provider": provider_name, "dimension": dimension}, f)

    def check_provider_compatibility(self, provider_name: str, dimension: int) -> None:
        info_path = os.path.join(self.persist_path, "provider_info.json")
        if not os.path.exists(info_path):
            return  # DB mới, chưa có thông tin, bỏ qua

        with open(info_path) as f:
            saved = json.load(f)

        if saved["provider"] != provider_name or saved["dimension"] != dimension:
            raise ValueError(
                f"Provider không khớp! DB được tạo bằng '{saved['provider']}' "
                f"({saved['dimension']} chiều), nhưng đang dùng '{provider_name}' "
                f"({dimension} chiều). Hãy dùng đúng provider ban đầu, hoặc xóa "
                f"data/chroma_db/ để re-index lại từ đầu."
            )

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
    
    def load_all_chunks(self) -> list[Chunk]:
        """
        Tái tạo lại list Chunk từ dữ liệu đã lưu trong ChromaDB,
        không cần parse/chunk/embed lại từ PDF gốc.
        """
        data = self.documents.get(include=["documents", "metadatas"])
        chunks = []
        for chunk_id, text, meta in zip(data["ids"], data["documents"], data["metadatas"]):
            chunks.append(Chunk(
                chunk_id=chunk_id,
                source=meta["source"],
                page_start=meta["page_start"],
                page_end=meta["page_end"],
                text=text,
                sentence_count=0,  # không cần thiết cho việc test tool, để tạm 0
            ))
        return chunks