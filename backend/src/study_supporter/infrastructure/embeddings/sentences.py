from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable
from study_supporter.domain.documents import SentenceUnit
from study_supporter.infrastructure.embeddings.providers import EmbeddingProvider
from study_supporter.domain.errors import EmbeddingUnavailable


def _embed_sentence_batch(
    batch: list[SentenceUnit], provider: EmbeddingProvider
) -> list[SentenceUnit]:
    """Embed một batch câu và gán vector vào từng SentenceUnit."""
    texts = [s.text for s in batch]
    vectors = provider.embed(texts, task_type="SEMANTIC_SIMILARITY")
    if len(vectors) != len(batch) or any(not vector for vector in vectors):
        raise EmbeddingUnavailable("Embedding provider returned incomplete vectors")
    for s, v in zip(batch, vectors):
        s.embedding = v
    return batch


def _split_into_batches(sentences: list[SentenceUnit], batch_size: int) -> list[list[SentenceUnit]]:
    """Chia sentences thành các batch có kích thước cố định, hiệu quả hơn chia theo page."""
    return [sentences[i : i + batch_size] for i in range(0, len(sentences), batch_size)]


def embed_sentences(
    sentences: list[SentenceUnit],
    provider: EmbeddingProvider,
    use_parallel: bool = False,
    max_workers: int = 4,
    batch_size: int = 64,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[SentenceUnit]:
    if not sentences:
        return []

    total = len(sentences)

    # File nhỏ (<= 1 batch): embed trực tiếp, không cần overhead threading
    if total <= batch_size:
        result = _embed_sentence_batch(sentences, provider)
        if on_progress:
            on_progress(total, total)
        return result

    batches = _split_into_batches(sentences, batch_size)
    embedded_count = 0

    if not use_parallel or len(batches) <= 2:
        # Tuần tự cho ít batch hoặc khi không dùng parallel
        for batch in batches:
            _embed_sentence_batch(batch, provider)
            embedded_count += len(batch)
            if on_progress:
                on_progress(embedded_count, total)
        return sentences

    # Parallel: submit batches theo thứ tự, collect kết quả
    # Dùng dict để giữ thứ tự gốc khi futures complete không theo thứ tự
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_embed_sentence_batch, batch, provider): idx
            for idx, batch in enumerate(batches)
        }
        for future in as_completed(futures):
            future.result()  # raise exception nếu có lỗi
            embedded_count += len(batches[futures[future]])
            if on_progress:
                on_progress(embedded_count, total)

    return sentences
