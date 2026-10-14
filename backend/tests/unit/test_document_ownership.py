import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from study_supporter.infrastructure.persistence.sqlalchemy.database import Base
from study_supporter.infrastructure.persistence.sqlalchemy.models import Document, QuizAttempt, User
from study_supporter.infrastructure.persistence.sqlalchemy import document_repository as documents
from study_supporter.infrastructure.persistence.sqlalchemy.progress_repository import ProgressDB
from study_supporter.domain.errors import EvidenceNotFound


@pytest.fixture
def repository(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)  # Test fixture only; application boot uses Alembic.
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr(documents, "SessionLocal", session_factory)
    with session_factory() as session:
        session.add_all(
            [
                User(id=1, username="A", password_hash="fixture"),
                User(id=2, username="B", password_hash="fixture"),
            ]
        )
        session.commit()
    yield session_factory
    engine.dispose()


def test_b_cannot_read_update_or_record_against_a_document(repository):
    doc_id, collection = documents.create_document(1, "fixture.pdf")
    assert collection == f"documents_{doc_id}"
    documents.update_document_status(doc_id, "ready", chunk_count=1, user_id=1)
    assert documents.get_latest_ready_document(2) is None
    with pytest.raises(EvidenceNotFound):
        documents.update_document_status(doc_id, "failed", user_id=2)
    with pytest.raises(EvidenceNotFound):
        documents.update_document_graph(doc_id, {"nodes": []}, user_id=2)
    progress = ProgressDB()
    progress.Session = repository
    with pytest.raises(EvidenceNotFound):
        progress.record_attempt("2", "topic", "Q?", True, doc_id)
    progress.record_attempt("1", "topic", "Q?", True, doc_id)
    assert progress.get_summary("2")["total_attempts"] == 0
    assert progress.get_summary("1")["total_attempts"] == 1
    with repository() as session:
        assert session.query(Document).filter_by(id=doc_id).one().status == "ready"
        assert session.query(QuizAttempt).count() == 1


def test_no_false_ready_or_invalid_attempt(repository):
    doc_id, _ = documents.create_document(1, "blank.pdf")
    with pytest.raises(ValueError, match="indexed chunks"):
        documents.update_document_status(doc_id, "ready", chunk_count=0, user_id=1)
    progress = ProgressDB()
    progress.Session = repository
    with pytest.raises(ValueError):
        progress.record_attempt("1", "topic", "Q?", None, doc_id)
    with repository() as session:
        assert session.query(QuizAttempt).count() == 0
