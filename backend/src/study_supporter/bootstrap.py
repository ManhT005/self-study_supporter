"""Explicit core composition; legacy infrastructure is wired by the UI adapter."""

from threading import RLock

from study_supporter.config import Settings

from study_supporter.application.ports.retrieval import (
    DocumentAccessPort,
    RetrieverPort,
)
from study_supporter.application.use_cases.retrieve import RetrieveEvidenceUseCase


def retrieval_service(access: DocumentAccessPort, retriever: RetrieverPort):
    return RetrieveEvidenceUseCase(access, retriever)


class SharedEmbedding:
    """One lazy model, no account state; serialize model construction and execution."""

    model_id = "BAAI/bge-m3"
    dimension = 1024

    def __init__(self, settings: Settings):
        self.settings = settings
        self._provider = None
        self._lock = RLock()

    def embed(self, texts, task_type):
        from study_supporter.domain.errors import EmbeddingUnavailable
        from study_supporter.infrastructure.embeddings.providers import LocalEmbeddingProvider

        with self._lock:
            if self._provider is None:
                try:
                    self._provider = LocalEmbeddingProvider(self.settings.embedding_model)
                except Exception as exc:
                    raise EmbeddingUnavailable(
                        "Không tải được model embedding. Kiểm tra cache và kết nối mạng."
                    ) from exc
            return self._provider.embed(texts, task_type)


class ApplicationFactory:
    """Process resources only. Account-bound tools are created for each session later."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.embedding = SharedEmbedding(settings)
        from study_supporter.infrastructure.persistence.sqlalchemy.database import Database
        from study_supporter.infrastructure.persistence.sqlalchemy.repositories import (
            DocumentRepository,
            UserRepository,
        )
        from study_supporter.infrastructure.persistence.sqlalchemy.progress_repository import (
            ProgressDB,
        )
        from study_supporter.application.use_cases.authenticate import Authentication
        from study_supporter.application.use_cases.documents import OwnedDocuments

        self.database = Database(settings)
        self.document_repository = DocumentRepository(self.database.sessions)
        self.documents = OwnedDocuments(self.document_repository)
        self.authentication = Authentication(UserRepository(self.database.sessions))
        self.progress_repository = ProgressDB(self.database.sessions)
        from study_supporter.application.use_cases.ingest_document import IngestDocumentUseCase
        from study_supporter.infrastructure.documents.pymupdf_parser import PdfParser
        from study_supporter.infrastructure.embeddings.pipeline import EmbeddingPipeline

        self.ingestion = IngestDocumentUseCase(
            self.document_repository,
            PdfParser(),
            EmbeddingPipeline(self.embedding),
            self.vector_store,
        )

    def vector_store(self, document):
        from study_supporter.infrastructure.persistence.chroma.vector_store import VectorStore

        return VectorStore(self.settings.chroma_path, document["chroma_collection_name"])

    def verify_schema(self):
        from study_supporter.infrastructure.persistence.sqlalchemy.lifecycle import verify_schema

        verify_schema(self.database)

    def close(self):
        self.database.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def provider(self, mode="auto"):
        from study_supporter.infrastructure.llm.factory import select_provider

        return select_provider(self.settings, mode)
