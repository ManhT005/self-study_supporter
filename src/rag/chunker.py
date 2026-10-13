import hashlib
import re
from typing import Callable

import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.rag.schemas import Chunk, DocumentPage, SentenceUnit
from src.rag.embedding_provider import EmbeddingProvider


# Ý tưởng thuật toán: Semantic Chunking bằng Breakpoint Detection
# Thay vì cắt chunk theo số ký tự cố định (dễ cắt ngang giữa 1 ý đang nói dở), ta làm thế này:

# 1. Tách toàn bộ tài liệu thành từng câu.
# 2. Embed từng câu riêng lẻ.
# 3. Tính độ khác biệt (cosine distance) giữa embedding của câu liền kề nhau.
# 4. Chỗ nào độ khác biệt đột ngột tăng cao (câu sau nói chuyện khác hẳn câu trước)
# → đó là breakpoint, tức ranh giới tự nhiên giữa 2 ý/2 đoạn.

# 5. Gộp các câu nằm giữa 2 breakpoint liên tiếp thành 1 chunk.

# DocumentPage
#       │
#       ▼
# split_into_sentences()
#       │
#       ▼
# SentenceUnit
#       │
#       ▼
# embed_sentences()
#       │
#       ▼
# SentenceUnit + embedding
#       │
#       ▼
# compute_distances()
#       │
#       ▼
# Khoảng cách giữa các câu


def split_into_sentences(text: str) -> list[str]:
    """
    Tách text thành list câu bằng regex: cắt sau . ! ?
    theo sau bởi khoảng trắng + chữ hoa/chữ có dấu (tránh cắt nhầm 'Fig. 2', 'e.g.').
    """
    pattern = r"(?<=[.!?])\s+(?=[A-ZÀ-Ỹ])"
    raw_sentences = re.split(pattern, text)

    sentences = [s.strip() for s in raw_sentences if len(s.strip()) >= 3]
    return sentences


def flatten_pages_to_sentences(pages: list[DocumentPage]) -> list[SentenceUnit]:
    all_sentences = []
    for page in pages:
        for s in split_into_sentences(page.text):
            all_sentences.append(
                SentenceUnit(source=page.source, text=s, page_number=page.page_number)
            )
    return all_sentences


# embed_sentences trong chunker.py
def _embed_sentence_batch(
    batch: list[SentenceUnit], provider: EmbeddingProvider
) -> list[SentenceUnit]:
    """Embed một batch câu và gán vector vào từng SentenceUnit."""
    texts = [s.text for s in batch]
    vectors = provider.embed(texts, task_type="SEMANTIC_SIMILARITY")
    for s, v in zip(batch, vectors):
        s.embedding = v
    return batch


def _split_into_batches(
    sentences: list[SentenceUnit], batch_size: int
) -> list[list[SentenceUnit]]:
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


def compute_distances(sentences: list[SentenceUnit]) -> list[float]:
    """
    Tính cosine distance giữa embedding của câu i và câu i+1.
    Trả về list có độ dài = len(sentences) - 1.

    Vectorized: dùng NumPy batch matrix operation thay vì Python loop,
    nhanh hơn ~5-10x cho tài liệu nhiều câu.
    """
    if len(sentences) < 2:
        return []

    # Stack tất cả embedding thành matrix (N x D) một lần duy nhất
    embeddings = np.array([s.embedding for s in sentences], dtype=np.float32)

    # Normalize toàn bộ matrix cùng lúc
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1e-10, norms)  # tránh chia cho 0
    normalized = embeddings / norms

    # Cosine similarity giữa câu liền kề = dot product theo từng hàng
    similarities = np.sum(normalized[:-1] * normalized[1:], axis=1)

    # Cosine distance = 1 - similarity
    distances = (1.0 - similarities).tolist()
    return distances


def compute_breakpoints(
    sentences: list[SentenceUnit],
    distances: list[float],
    percentile: float = 95,
) -> set[int]:
    """
    Trả về tập chỉ số i mà tại đó distance[i] (giữa câu i và i+1)
    vượt ngưỡng percentile của toàn bộ tài liệu -> đó là breakpoint.
    """
    if not distances:
        return set()
    threshold = np.percentile(distances, percentile)
    breakpoints = set()
    for i, d in enumerate(distances):
        if d > threshold and not sentences[i].text.rstrip().endswith(":"):
            breakpoints.add(i)
    return breakpoints


def _make_chunk(sentence_group: list[SentenceUnit]) -> Chunk:
    text = " ".join(s.text for s in sentence_group)
    source = sentence_group[0].source
    page_start = sentence_group[0].page_number
    page_end = sentence_group[-1].page_number

    # Hash từ nội dung + vị trí -> cùng 1 tài liệu chạy lại sẽ luôn ra cùng chunk_id
    raw_key = f"{source}-{page_start}-{page_end}-{text}"
    chunk_id = hashlib.md5(raw_key.encode("utf-8")).hexdigest()[:12]

    return Chunk(
        chunk_id=chunk_id,
        source=source,
        page_start=page_start,
        page_end=page_end,
        text=text,
        sentence_count=len(sentence_group),
    )


def group_sentences_into_chunks(
    sentences: list[SentenceUnit],
    breakpoints: set[int],
    min_sentences: int = 2,
    max_chars: int = 800,
) -> list[Chunk]:
    """
    Gộp câu thành chunk dựa trên breakpoint, có 2 điều kiện chặn thêm:
    - min_sentences: không chốt chunk quá ngắn (tránh chunk chỉ có 1 câu cụt lủn)
    - max_chars: ép cắt nếu chunk phình quá dài, kể cả chưa gặp breakpoint
      (tránh 1 đoạn văn dài không đổi ý bị gộp thành 1 chunk khổng lồ)
    """
    chunks = []
    current: list[SentenceUnit] = []

    for i, sentence in enumerate(sentences):
        current.append(sentence)
        current_chars = sum(len(s.text) for s in current)

        hit_breakpoint = i in breakpoints and len(current) >= min_sentences
        hit_max_size = current_chars >= max_chars

        if hit_breakpoint or hit_max_size:
            chunks.append(_make_chunk(current))
            current = []

    if current:  # phần dư cuối cùng
        chunks.append(_make_chunk(current))

    return chunks
