from collections import defaultdict

from src.rag.vector_store import VectorStore
from src.rag.bm25_index import BM25Index
from src.rag.schemas import Chunk

def reciprocal_rank_fusion(
    dense_ranked_ids: list[str],
    sparse_ranked_ids: list[str],
    k: int = 60,
) -> dict[str, float]:
    """
    Nhận 2 list id đã sort theo rank (index 0 = hạng 1),
    trả về dict {chunk_id: rrf_score}.
    """
    # TODO: với mỗi list, lặp qua index (rank = index + 1),
    # cộng dồn 1/(k + rank) vào scores[chunk_id]
    scores = defaultdict(float)

    for ranked_list in (dense_ranked_ids, sparse_ranked_ids):
        for index, chunk_id in enumerate(ranked_list):
            rank = index + 1
            scores[chunk_id] += 1 / (k + rank)

    return dict(scores)


def hybrid_search(
    query: str,
    vector_store: VectorStore,
    bm25_index: BM25Index,
    embed_query_fn,     # hàm nhận query text -> vector
    top_k: int = 5,
) -> list[Chunk]:
    # TODO:
    # 1. dense: embed_query_fn(query) -> query_vector
    #    vector_store.documents.query(query_embeddings=[query_vector], n_results=top_k*2)
    #    lấy ra list id theo đúng thứ tự trả về (đã là rank rồi)
    # 2. sparse: bm25_index.search(query, top_k=top_k*2) -> lấy list id theo thứ tự
    # 3. gọi reciprocal_rank_fusion(dense_ids, sparse_ids)
    # 4. sort theo score giảm dần, lấy top_k id đầu
    # 5. map ngược id -> Chunk object (cần tra trong bm25_index.chunks hoặc metadata)
    """
    Hybrid Retrieval:
        Dense Search
            +
        BM25
            ↓
        Reciprocal Rank Fusion
    """

    # ==========================
    # 1. Dense Search
    # ==========================

    query_vector = embed_query_fn(query)

    dense_result = vector_store.documents.query(
        query_embeddings=[query_vector],
        n_results=top_k * 2,
    )

    dense_ids = dense_result["ids"][0]

    # ==========================
    # 2. BM25 Search
    # ==========================

    sparse_result = bm25_index.search(
        query,
        top_k=top_k * 2,
    )

    sparse_ids = [
        chunk.chunk_id
        for chunk, _ in sparse_result
    ]

    # ==========================
    # 3. Reciprocal Rank Fusion
    # ==========================

    rrf_scores = reciprocal_rank_fusion(
        dense_ids,
        sparse_ids,
    )

    # ==========================
    # 4. Chọn Top K
    # ==========================

    ranked_ids = sorted(
        rrf_scores.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    top_ids = [
        chunk_id
        for chunk_id, _ in ranked_ids[:top_k]
    ]

    # ==========================
    # 5. Map id -> Chunk
    # ==========================

    results = [
        bm25_index.chunk_map[chunk_id]
        for chunk_id in top_ids
        if chunk_id in bm25_index.chunk_map
    ]

    return results