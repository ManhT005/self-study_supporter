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

    def retriever(self):
        from study_supporter.infrastructure.retrieval.scoped_retriever import ScopedHybridRetriever

        return RetrieveEvidenceUseCase(
            self.document_repository,
            ScopedHybridRetriever(self.document_repository, self.vector_store, self.embedding),
        )

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

    def open_document(self, context, document_id=None, mode="auto"):
        from study_supporter.application.contracts.context import AppContext
        from study_supporter.application.use_cases.answer_question import AnswerQuestionUseCase
        from study_supporter.application.use_cases.learning import (
            SubmitQuizUseCase,
            GetProgressUseCase,
            SaveNoteUseCase,
        )
        from study_supporter.application.use_cases.session import LearningSession
        from study_supporter.infrastructure.persistence.chroma.note_repository import LongTermMemory
        from study_supporter.orchestration.legacy_react.orchestrator import ReActOrchestrator
        from study_supporter.orchestration.legacy_react.tools.retrieve_evidence import (
            RetrieveEvidenceTool,
        )
        from study_supporter.orchestration.legacy_react.tools.generate_quiz import GenerateQuizTool
        from study_supporter.orchestration.legacy_react.tools.save_note import SaveNoteTool
        from study_supporter.orchestration.legacy_react.tools.get_progress import GetProgressTool

        document = (
            self.document_repository.get(context.user_id, document_id)
            if document_id is not None
            else self.document_repository.latest(context.user_id)
        )
        if not document:
            return None
        store = self.vector_store(document)
        chunks = store.load_all_chunks()
        if not chunks:
            return None
        context = AppContext(context.user_id, (str(document["id"]),))
        selection = self.provider(mode)
        search = RetrieveEvidenceTool(self.retriever(), context)
        generator = GenerateQuizTool(selection.client)
        notes = SaveNoteUseCase(
            LongTermMemory(store, lambda query: self.embedding.embed([query], "RETRIEVAL_QUERY")[0])
        )
        progress = GetProgressUseCase(self.progress_repository)
        tools = [
            search,
            generator,
            SaveNoteTool(notes, context.user_id),
            GetProgressTool(progress, context.user_id),
        ]
        runner = ReActOrchestrator(selection.client, tools)
        return LearningSession(
            context,
            document,
            chunks,
            AnswerQuestionUseCase(runner, search),
            generator,
            SubmitQuizUseCase(self.document_repository, self.progress_repository),
            progress,
            self.document_repository,
            selection.client,
            mode=selection.mode,
            notice=selection.notice,
        )
