from typing import Callable

from src.rag.schemas import Chunk
from src.rag.embedding_provider import EmbeddingProvider


def embed_chunks(
    chunks: list[Chunk],
    provider: EmbeddingProvider,
    batch_size: int = 64,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[list[float]]:
    """
    Embed tất cả chunks, chia thành batches để tránh OOM cho file lớn.

    on_progress(embedded_count, total): callback cập nhật UI.
    """
    if not chunks:
        return []

    total = len(chunks)

    # File nhỏ: embed 1 lần
    if total <= batch_size:
        vectors = provider.embed([c.text for c in chunks], task_type="RETRIEVAL_DOCUMENT")
        if on_progress:
            on_progress(total, total)
        return vectors

    # File lớn: chia batch
    all_vectors: list[list[float]] = []
    for i in range(0, total, batch_size):
        batch_texts = [c.text for c in chunks[i:i + batch_size]]
        batch_vectors = provider.embed(batch_texts, task_type="RETRIEVAL_DOCUMENT")
        all_vectors.extend(batch_vectors)
        if on_progress:
            on_progress(min(i + batch_size, total), total)

    return all_vectors