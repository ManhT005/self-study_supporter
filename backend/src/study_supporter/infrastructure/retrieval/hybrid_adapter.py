from typing import TYPE_CHECKING

from study_supporter.domain.documents import Chunk
from study_supporter.ai.retrieval.rrf import reciprocal_rank_fusion

if TYPE_CHECKING:
    from study_supporter.infrastructure.persistence.chroma.vector_store import VectorStore
    from study_supporter.infrastructure.retrieval.bm25_adapter import BM25Index


def hybrid_search(
    query: str,
    vector_store: "VectorStore",
    bm25_index: "BM25Index",
    embed_query_fn,  # hàm nhận query text -> vector
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

    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    if not bm25_index.chunk_map:
        return []
    query_vector = embed_query_fn(query)

    dense_result = vector_store.documents.query(
        query_embeddings=[query_vector],
        n_results=min(top_k * 2, len(bm25_index.chunk_map)),
    )

    dense_ids = dense_result["ids"][0]

    # ==========================
    # 2. BM25 Search
    # ==========================

    sparse_result = bm25_index.search(
        query,
        top_k=top_k * 2,
    )

    sparse_ids = [chunk.chunk_id for chunk, _ in sparse_result]

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

    top_ids = [chunk_id for chunk_id, _ in ranked_ids[:top_k]]

    # ==========================
    # 5. Map id -> Chunk
    # ==========================

    results = [
        bm25_index.chunk_map[chunk_id] for chunk_id in top_ids if chunk_id in bm25_index.chunk_map
    ]

    return results
