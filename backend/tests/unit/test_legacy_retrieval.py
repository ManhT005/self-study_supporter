from unittest.mock import Mock

import pytest

from study_supporter.infrastructure.retrieval.hybrid_adapter import (
    hybrid_search,
    reciprocal_rank_fusion,
)
from study_supporter.domain.documents import Chunk
from study_supporter.ai.retrieval.rrf import reciprocal_rank_fusion as core_rrf


def test_forwarder_is_the_core_function():
    assert reciprocal_rank_fusion is core_rrf


@pytest.mark.parametrize("top_k", [0, -1, True])
def test_invalid_top_k_does_not_embed(top_k):
    embed = Mock()
    with pytest.raises(ValueError):
        hybrid_search("question", Mock(), Mock(), embed, top_k)
    embed.assert_not_called()


def test_golden_hybrid_order_and_limit():
    chunks = [
        Chunk(
            chunk_id=key,
            source="fixture.pdf",
            page_start=1,
            page_end=1,
            text=key,
            sentence_count=1,
        )
        for key in ["a", "b", "c"]
    ]
    vector, bm25 = Mock(), Mock()
    vector.documents.query.return_value = {"ids": [["b", "a"]]}
    bm25.search.return_value = [(chunks[0], 1), (chunks[2], 0.5)]
    bm25.chunk_map = {c.chunk_id: c for c in chunks}
    assert hybrid_search("question", vector, bm25, lambda _: [1, 0], 1) == [chunks[0]]
