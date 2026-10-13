from unittest.mock import Mock

from study_supporter.infrastructure.retrieval.hybrid_adapter import hybrid_search


def test_empty_index_does_not_embed_or_call_chroma():
    vector, sparse, embed = Mock(), Mock(), Mock()
    sparse.chunk_map = {}
    assert hybrid_search("question", vector, sparse, embed, 50) == []
    embed.assert_not_called()
    vector.documents.query.assert_not_called()
