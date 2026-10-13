import pytest

from study_supporter.ai.retrieval.rrf import reciprocal_rank_fusion


@pytest.mark.parametrize(
    "dense,sparse",
    [([], []), (["a"], []), (["a", "b", "a"], ["b", "c"]), (["b"], ["a"])],
)
def test_legacy_golden_vectors(dense, sparse):
    expected = {}
    for ranking in (dense, sparse):
        for rank, chunk_id in enumerate(ranking, 1):
            expected[chunk_id] = expected.get(chunk_id, 0.0) + 1 / (60 + rank)
    assert reciprocal_rank_fusion(dense, sparse) == expected


def test_ties_preserve_dense_first_order_and_duplicate_contributions():
    scores = reciprocal_rank_fusion(["b"], ["a"])
    assert sorted(scores, key=scores.get, reverse=True) == ["b", "a"]
    assert reciprocal_rank_fusion(["a", "a"], []) == {"a": 1 / 61 + 1 / 62}
