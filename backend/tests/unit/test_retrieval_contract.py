from unittest.mock import Mock

import pytest

from study_supporter.application.contracts.retrieval import Evidence, RetrievalQuery
from study_supporter.application.use_cases.retrieve import RetrieveEvidenceUseCase
from study_supporter.domain.errors import EvidenceNotFound


@pytest.mark.parametrize("top_k", [0, -1, True, 1.5])
def test_invalid_top_k(top_k):
    with pytest.raises(ValueError):
        RetrievalQuery("A", ("doc-a",), "question", top_k)


def test_foreign_document_never_reaches_retriever():
    access, retriever = Mock(), Mock()
    access.owns.return_value = False
    with pytest.raises(EvidenceNotFound):
        RetrieveEvidenceUseCase(access, retriever).execute(
            RetrievalQuery("B", ("doc-a",), "question")
        )
    retriever.retrieve.assert_not_called()


def test_foreign_evidence_rejected_and_limit_respected():
    access, retriever = Mock(), Mock()
    access.owns.return_value = True
    item = Evidence("chunk", "doc-a", "text", "fixture.pdf", 1, 1)
    retriever.retrieve.return_value = [item, item]
    query = RetrievalQuery("A", ("doc-a",), "question", 1)
    assert RetrieveEvidenceUseCase(access, retriever).execute(query) == [item]
    retriever.retrieve.return_value = [Evidence("x", "doc-b", "text", "b.pdf", 1, 1)]
    with pytest.raises(EvidenceNotFound):
        RetrieveEvidenceUseCase(access, retriever).execute(query)
