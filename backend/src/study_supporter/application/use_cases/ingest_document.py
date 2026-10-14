import hashlib
import uuid
from threading import Lock
from weakref import WeakValueDictionary

from study_supporter.application.contracts.learning import (
    DocumentResult,
    IngestionStage,
    ProgressEvent,
    IngestDocumentRequest,
)
from study_supporter.ai.ingestion.chunking import (
    flatten_pages_to_sentences,
    compute_distances,
    compute_breakpoints,
    group_sentences_into_chunks,
)
from study_supporter.domain.upload_validation import validate_pdf_upload
from study_supporter.domain.errors import DocumentUnsupported, EmbeddingUnavailable


class IngestDocumentUseCase:
    def __init__(self, documents, parser, embeddings, vectors):
        self.documents, self.parser, self.embeddings, self.vectors = (
            documents,
            parser,
            embeddings,
            vectors,
        )
        self._locks = WeakValueDictionary()
        self._registry = Lock()

    def execute(self, request: IngestDocumentRequest, on_progress=None) -> DocumentResult:
        trace = uuid.uuid4().hex
        user = request.context.user_id
        digest = hashlib.sha256(request.content).hexdigest()

        def event(stage, done=0, total=0, message=""):
            if on_progress:
                on_progress(ProgressEvent(trace, stage, done, total, message))

        with self._registry:
            lock = self._locks.setdefault((user, digest), Lock())
        document = None
        with lock:
            try:
                event(IngestionStage.VALIDATING)
                validate_pdf_upload(request.filename, request.mime, request.content)
                document = self.documents.find_hash(user, digest)
                if document:
                    store = self.vectors(document)
                    if (
                        document["status"] == "ready"
                        and store.count() == document["chunk_count"]
                        and store.count() > 0
                    ):
                        event(IngestionStage.READY, 1, 1)
                        return DocumentResult(
                            document["id"],
                            document["filename"],
                            document["chunk_count"],
                            document["page_count"] or 0,
                            trace,
                            True,
                        )
                    self.documents.update(user, document["id"], status="processing")
                else:
                    document = self.documents.create(user, request.filename, digest)
                    store = self.vectors(document)
                event(IngestionStage.PARSING)
                parsed = self.parser.parse(
                    document["filename"],
                    request.content,
                    lambda done, total: event(IngestionStage.PARSING, done, total),
                )
                event(IngestionStage.CHUNKING)
                sentences = flatten_pages_to_sentences(parsed.pages)
                if not sentences:
                    raise DocumentUnsupported(
                        "PDF không có câu văn bản sử dụng được; tài liệu scan cần OCR."
                    )
                sentences = self.embeddings.sentences(
                    sentences, lambda done, total: event(IngestionStage.EMBEDDING, done, total)
                )
                chunks = group_sentences_into_chunks(
                    sentences,
                    compute_breakpoints(sentences, compute_distances(sentences)),
                    min_sentences=2,
                    max_chars=800,
                )
                existing = store.get_existing_ids([chunk.chunk_id for chunk in chunks])
                missing = [chunk for chunk in chunks if chunk.chunk_id not in existing]
                if missing:
                    vectors = self.embeddings.chunks(
                        missing, lambda done, total: event(IngestionStage.EMBEDDING, done, total)
                    )
                    if len(vectors) != len(missing) or any(
                        len(vector) != self.embeddings.dimension for vector in vectors
                    ):
                        raise EmbeddingUnavailable(
                            "Embedding dimension does not match the configured model"
                        )
                    event(IngestionStage.INDEXING)
                    store.add_chunks(missing, vectors)
                actual = store.load_all_chunks()
                if {chunk.chunk_id for chunk in actual} != {chunk.chunk_id for chunk in chunks}:
                    raise EmbeddingUnavailable("Incomplete document index")
                self.documents.update(
                    user,
                    document["id"],
                    status="ready",
                    page_count=parsed.total_pages,
                    chunk_count=len(actual),
                )
                event(IngestionStage.READY, 1, 1)
                return DocumentResult(
                    document["id"], document["filename"], len(actual), parsed.total_pages, trace
                )
            except Exception:
                if document:
                    self.documents.update(user, document["id"], status="failed")
                event(IngestionStage.FAILED)
                raise
