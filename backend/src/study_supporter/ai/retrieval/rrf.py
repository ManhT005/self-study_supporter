"""Baseline reciprocal rank fusion, preserving legacy duplicate/tie semantics."""

from collections import defaultdict


def reciprocal_rank_fusion(
    dense_ranked_ids: list[str], sparse_ranked_ids: list[str], k: int = 60
) -> dict[str, float]:
    scores: dict[str, float] = defaultdict(float)
    for ranked_list in (dense_ranked_ids, sparse_ranked_ids):
        for index, chunk_id in enumerate(ranked_list):
            scores[chunk_id] += 1 / (k + index + 1)
    return dict(scores)
