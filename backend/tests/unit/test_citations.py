from unittest.mock import Mock, patch

from src.agent.tools.search_docs import SearchDocsTool
from src.rag.schemas import Chunk


def test_citations_require_actual_retrieved_provenance_and_do_not_stay_stale():
    chunk = Chunk(
        chunk_id="chunk-a",
        source="fixture.pdf",
        page_start=1,
        page_end=2,
        text="content",
        sentence_count=2,
    )
    tool = SearchDocsTool(Mock(), Mock(), Mock(), document_id="doc-a")
    with patch("src.agent.tools.search_docs.hybrid_search", return_value=[chunk]):
        tool.run("question")
    assert tool.last_evidence[0].document_id == "doc-a"
    assert tool.last_evidence[0].chunk_id == "chunk-a"
    tool.run("")
    assert tool.last_evidence == []
