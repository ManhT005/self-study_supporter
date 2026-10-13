import hashlib
from types import SimpleNamespace

import pytest

from study_supporter.application.contracts.context import AppContext
from study_supporter.application.contracts.learning import IngestDocumentRequest, IngestionStage
from study_supporter.application.use_cases.ingest_document import IngestDocumentUseCase
from study_supporter.domain.documents import DocumentPage
from study_supporter.domain.errors import EmbeddingUnavailable


class Documents:
    def __init__(self):
        self.rows = []

    def find_hash(self, user, digest):
        return next(
            (row for row in self.rows if row["user"] == user and row["file_hash"] == digest), None
        )

    def create(self, user, filename, digest):
        row = dict(
            id=len(self.rows) + 1,
            user=user,
            filename=filename,
            file_hash=digest,
            status="processing",
            chunk_count=0,
            page_count=0,
        )
        self.rows.append(row)
        return row

    def update(self, user, document_id, **values):
        row = next(row for row in self.rows if row["id"] == document_id and row["user"] == user)
        row.update(values)


class Store:
    def __init__(self):
        self.chunks = []

    def count(self):
        return len(self.chunks)

    def get_existing_ids(self, ids):
        return {c.chunk_id for c in self.chunks} & set(ids)

    def add_chunks(self, chunks, embeddings):
        self.chunks.extend(chunks)

    def load_all_chunks(self):
        return self.chunks


class Embeddings:
    dimension = 2
    fail = False

    def sentences(self, sentences, callback):
        for sentence in sentences:
            sentence.embedding = [1.0, 0.0]
        return sentences

    def chunks(self, chunks, callback):
        if self.fail:
            raise EmbeddingUnavailable("fixture failure")
        return [[1.0, 0.0] for _ in chunks]


def pipeline():
    docs, stores, embeddings = Documents(), {}, Embeddings()
    parser = SimpleNamespace(
        parse=lambda name, data, callback: SimpleNamespace(
            pages=[DocumentPage(source=name, page_number=1, text="One sentence.")], total_pages=1
        )
    )
    case = IngestDocumentUseCase(
        docs, parser, embeddings, lambda doc: stores.setdefault(doc["id"], Store())
    )
    return case, docs, stores, embeddings


def test_golden_chunk_id_progress_and_scoped_hash_dedupe():
    case, docs, stores, _ = pipeline()
    events = []
    request = IngestDocumentRequest(
        AppContext("A"), "fixture.pdf", b"%PDF-fixture", "application/pdf"
    )
    result = case.execute(request, events.append)
    expected = hashlib.md5(b"fixture.pdf-1-1-One sentence.").hexdigest()[:12]
    assert stores[result.document_id].chunks[0].chunk_id == expected
    assert len({event.trace_id for event in events}) == 1
    assert events[-1].stage == IngestionStage.READY
    assert case.execute(request).reused and len(docs.rows) == 1
    other = case.execute(
        IngestDocumentRequest(AppContext("B"), request.filename, request.content, request.mime)
    )
    assert other.document_id != result.document_id


def test_failure_retry_reuses_document_and_never_reports_false_ready():
    case, docs, _, embeddings = pipeline()
    request = IngestDocumentRequest(AppContext("A"), "fixture.pdf", b"%PDF-fixture")
    embeddings.fail = True
    events = []
    with pytest.raises(EmbeddingUnavailable):
        case.execute(request, events.append)
    assert docs.rows[0]["status"] == "failed"
    assert events[-1].stage == IngestionStage.FAILED
    assert all(event.stage != IngestionStage.READY for event in events)
    embeddings.fail = False
    assert case.execute(request).document_id == docs.rows[0]["id"]
    assert len(docs.rows) == 1
