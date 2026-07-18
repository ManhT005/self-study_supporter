import hashlib
import re
import numpy as np
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
    pattern = r'(?<=[.!?])\s+(?=[A-ZÀ-Ỹ])'
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
def embed_sentences(sentences: list[SentenceUnit], provider: EmbeddingProvider) -> list[SentenceUnit]:
    texts = [s.text for s in sentences]
    vectors = provider.embed(texts, task_type="SEMANTIC_SIMILARITY")
    for s, v in zip(sentences, vectors):
        s.embedding = v
    return sentences


def compute_distances(sentences: list[SentenceUnit]) -> list[float]:
    """
    Tính cosine distance giữa embedding của câu i và câu i+1.
    Trả về list có độ dài = len(sentences) - 1.
    """
    distances = []
    for i in range(len(sentences) - 1):
        a = np.array(sentences[i].embedding)
        b = np.array(sentences[i + 1].embedding)

        cosine_similarity = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        cosine_distance = 1 - cosine_similarity
        distances.append(float(cosine_distance))

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