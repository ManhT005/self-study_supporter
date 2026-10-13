"""Explicit core composition; legacy infrastructure is wired by the UI adapter."""

from study_supporter.application.ports.retrieval import (
    DocumentAccessPort,
    RetrieverPort,
)
from study_supporter.application.use_cases.retrieve import RetrieveEvidenceUseCase


def retrieval_service(access: DocumentAccessPort, retriever: RetrieverPort):
    return RetrieveEvidenceUseCase(access, retriever)
