"""Offline HTTP fixture: real application factory, PDF parser, SQL and use cases.

Only vectors and AI providers are deterministic doubles, never a production mode.
"""

from types import SimpleNamespace

from sqlalchemy import text

from study_supporter.bootstrap import ApplicationFactory
from study_supporter.config import Settings
from study_supporter.infrastructure.persistence.sqlalchemy.database import Base
from scripts.docker_smoke import FakeEmbedding, FakeLLM
from study_supporter.infrastructure.llm.factory import ProviderSelection


class MemoryVectors:
    def __init__(self):
        self.chunks = []
        self.notes = []
        self.documents = SimpleNamespace(
            query=lambda **kwargs: {"ids": [[c.chunk_id for c in self.chunks]]}
        )
        self.user_memory = SimpleNamespace(upsert=lambda **kwargs: self.notes.append(kwargs))

    def count(self):
        return len(self.chunks)

    def get_existing_ids(self, ids):
        return {c.chunk_id for c in self.chunks} & set(ids)

    def add_chunks(self, chunks, embeddings):
        self.chunks.extend(chunks)

    def load_all_chunks(self):
        return list(self.chunks)


class FixtureFactory(ApplicationFactory):
    def __init__(self, database_url):
        self.stores = {}
        super().__init__(
            Settings(database_url=database_url),
            embedding=FakeEmbedding(),
            provider_factory=lambda settings, mode: ProviderSelection(FakeLLM(), "ollama"),
        )
        # Test-only schema fixture; deployed adapters always require Alembic.
        Base.metadata.create_all(self.database.engine)
        with self.database.engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) PRIMARY KEY)"
                )
            )
            if not connection.execute(text("SELECT version_num FROM alembic_version")).first():
                connection.execute(text("INSERT INTO alembic_version VALUES ('p0_0001')"))

    def vector_store(self, document):
        return self.stores.setdefault(document["id"], MemoryVectors())
