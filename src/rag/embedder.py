from src.rag.schemas import Chunk
from src.rag.embedding_provider import EmbeddingProvider


def embed_chunks(chunks: list[Chunk], provider: EmbeddingProvider) -> list[list[float]]:
    texts = [c.text for c in chunks]
    return provider.embed(texts, task_type="RETRIEVAL_DOCUMENT")