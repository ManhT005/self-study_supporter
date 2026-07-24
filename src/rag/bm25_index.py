from rank_bm25 import BM25Okapi
from src.rag.schemas import Chunk

class BM25Index:
    def __init__(self, chunks: list[Chunk]):
        # TODO: tokenize text của từng chunk (đơn giản: .lower().split())
        # build self.bm25 = BM25Okapi(tokenized_corpus)
        
        self.chunks = chunks

        # Dùng để map chunk_id -> Chunk khi hybrid search
        self.chunk_map = {
            chunk.chunk_id: chunk
            for chunk in chunks
        }

        # Tokenize toàn bộ corpus
        tokenized_corpus = [
            chunk.text.lower().split()
            for chunk in chunks
        ]

        self.bm25 = BM25Okapi(tokenized_corpus)

    def search(self, query: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
        # TODO: tokenize query giống cách tokenize corpus
        # gọi self.bm25.get_scores(tokenized_query)
        # trả về list (chunk, score) đã sort giảm dần, lấy top_k
        """
        Trả về danh sách (Chunk, BM25 score) đã sort giảm dần.
        """

        tokenized_query = query.lower().split()

        scores = self.bm25.get_scores(tokenized_query)

        ranked = sorted(
            zip(self.chunks, scores),
            key=lambda x: x[1],
            reverse=True,
        )

        return ranked[:top_k]