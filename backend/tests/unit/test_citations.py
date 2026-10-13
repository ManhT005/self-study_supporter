from unittest.mock import Mock
from study_supporter.application.contracts.context import AppContext
from study_supporter.application.contracts.retrieval import Evidence
from study_supporter.orchestration.legacy_react.tools.retrieve_evidence import RetrieveEvidenceTool


def test_citations_require_actual_retrieved_provenance_and_do_not_stay_stale():
    retrieval = Mock()
    retrieval.execute.return_value = [
        Evidence(
            document_id="doc-a",
            chunk_id="chunk-a",
            source="fixture.pdf",
            page_start=1,
            page_end=2,
            text="content",
            score=1.0,
        )
    ]
    tool = RetrieveEvidenceTool(retrieval, AppContext("A", ("doc-a",)))
    assert "fixture.pdf" in tool.run("question")
    query = retrieval.execute.call_args.args[0]
    assert query.user_id == "A" and query.document_ids == ("doc-a",)
    assert tool.last_evidence[0].chunk_id == "chunk-a"
    tool.run("")
    assert tool.last_evidence == []
