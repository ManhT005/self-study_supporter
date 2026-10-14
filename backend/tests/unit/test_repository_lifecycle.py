import subprocess
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from study_supporter.infrastructure.persistence.sqlalchemy.database import Base
from study_supporter.infrastructure.persistence.sqlalchemy.models import User
from study_supporter.infrastructure.persistence.sqlalchemy.repositories import DocumentRepository
from study_supporter.domain.errors import EvidenceNotFound


def test_repository_returns_detached_data_and_checks_every_update():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions.begin() as session:
        session.add_all(
            [
                User(id=1, username="A", password_hash="fixture"),
                User(id=2, username="B", password_hash="fixture"),
            ]
        )
    repo = DocumentRepository(sessions)
    doc = repo.create("1", "fixture.pdf", "sha256-fixture")
    assert doc["chroma_collection_name"] == f"documents_{doc['id']}"
    assert repo.find_hash("2", "sha256-fixture") is None
    with pytest.raises(EvidenceNotFound):
        repo.update("2", doc["id"], status="ready", chunk_count=1)
    repo.update("1", doc["id"], status="ready", chunk_count=1)
    assert repo.latest("1")["id"] == doc["id"]
    engine.dispose()


def test_canonical_import_does_not_construct_engine():
    code = "from unittest.mock import patch; import sqlalchemy; p=patch('sqlalchemy.create_engine',side_effect=AssertionError('import-time engine')); p.start(); import study_supporter.infrastructure.persistence.sqlalchemy.database, study_supporter.infrastructure.persistence.sqlalchemy.repositories, study_supporter.infrastructure.persistence.sqlalchemy.lifecycle"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
