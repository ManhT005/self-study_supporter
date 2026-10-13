"""Requires a disposable migrated PostgreSQL DB in STUDY_TEST_DATABASE_URL."""

import os
import uuid

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from study_supporter.infrastructure.persistence.sqlalchemy.database import Base
from study_supporter.infrastructure.persistence.sqlalchemy.models import User
from study_supporter.infrastructure.persistence.sqlalchemy import document_repository as documents
from study_supporter.infrastructure.persistence.sqlalchemy.progress_repository import ProgressDB
from study_supporter.domain.errors import EvidenceNotFound


@pytest.fixture
def pg_repository(monkeypatch):
    url = os.environ.get("STUDY_TEST_DATABASE_URL")
    if not url:
        pytest.fail("Set STUDY_TEST_DATABASE_URL to a disposable migrated PostgreSQL database")
    engine = create_engine(url)
    assert engine.dialect.name == "postgresql"
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(documents, "SessionLocal", factory)
    marker = uuid.uuid4().hex
    with factory() as session:
        users = [
            User(username=f"fixture-{marker}-{label}", password_hash="fixture")
            for label in ["A", "B"]
        ]
        session.add_all(users)
        session.flush()
        ids = [user.id for user in users]
        session.commit()
    yield engine, factory, ids
    with engine.begin() as connection:
        for user in ids:
            connection.execute(
                text("DELETE FROM quiz_attempts WHERE user_id = :id"), {"id": str(user)}
            )
            connection.execute(text("DELETE FROM users WHERE id = :id"), {"id": user})
    engine.dispose()


def test_postgres_schema_matches_models(pg_repository):
    engine, _, _ = pg_repository
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
            == "p0_0001"
        )
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
    fks = inspect(engine).get_foreign_keys("documents")
    assert any(fk["referred_table"] == "users" for fk in fks)


def test_postgres_ownership_and_progress(pg_repository):
    _, factory, (a, b) = pg_repository
    doc, _ = documents.create_document(a, "fixture.pdf")
    documents.update_document_status(doc, "ready", chunk_count=1, user_id=a)
    assert documents.get_latest_ready_document(b) is None
    with pytest.raises(EvidenceNotFound):
        documents.update_document_graph(doc, {}, user_id=b)
    progress = ProgressDB()
    progress.Session = factory
    with pytest.raises(EvidenceNotFound):
        progress.record_attempt(str(b), "fixture", "Q?", True, doc)
    progress.record_attempt(str(a), "fixture", "Q?", True, doc)
    assert progress.get_summary(str(a))["total_attempts"] == 1
    assert progress.get_summary(str(b))["total_attempts"] == 0


def test_canonical_repository_and_grading_preserve_scoped_data(pg_repository):
    from study_supporter.application.contracts.context import AppContext
    from study_supporter.application.use_cases.learning import SubmitQuizUseCase
    from study_supporter.infrastructure.persistence.sqlalchemy.repositories import (
        DocumentRepository,
    )

    _, factory, (a, b) = pg_repository
    repository = DocumentRepository(factory)
    document = repository.create(str(a), "canonical.pdf", "fixture-hash")
    repository.update(str(a), document["id"], status="ready", chunk_count=1)
    repository.update(str(a), document["id"], concept_graph_json={"nodes": [], "edges": []})
    assert repository.find_hash(str(a), "fixture-hash")["id"] == document["id"]
    assert repository.find_hash(str(b), "fixture-hash") is None
    with pytest.raises(EvidenceNotFound):
        repository.get(str(b), document["id"])
    question = {
        "question": "Q?",
        "options": ["a", "b", "c", "d"],
        "correct_index": 1,
        "explanation": "fixture",
    }
    progress = ProgressDB(factory)
    submit = SubmitQuizUseCase(repository, progress)
    with pytest.raises(EvidenceNotFound):
        submit.execute(AppContext(str(b)), document["id"], question, 1)
    assert submit.execute(AppContext(str(a)), document["id"], question, 1).is_correct
    assert progress.get_summary(str(a))["total_attempts"] == 1
    assert progress.get_summary(str(b))["total_attempts"] == 0
