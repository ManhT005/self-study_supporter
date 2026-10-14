"""Opt-in ingest of an approved PDF into a NEW disposable snapshot, never application data."""

import argparse
import hashlib
import os
import secrets
import subprocess
import sys
from pathlib import Path

from evaluation.datasets.v2.schema_extensions import ApprovedDocument, CorpusSnapshot, IndexedChunk
from evaluation.live.fixtures import factory_for, file_hash, payload_hashes, write_json


def migrate_new_snapshot(root):
    root = Path(root).resolve()
    env = dict(os.environ)
    from study_supporter.config import Settings

    for field in Settings.__dataclass_fields__:
        env.pop(field.upper(), None)
    env["DATABASE_URL"] = "sqlite:///" + (root / "app.db").as_posix()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(Path(__file__).resolve().parents[2] / "backend/alembic.ini"),
            "upgrade",
            "head",
        ],
        env=env,
        capture_output=True,
        timeout=60,
    )
    if result.returncode:
        raise ValueError("Isolated migration failed")


def prepare(pdf, root, *, permission_reference, embedding_revision, factory_builder=None):
    from study_supporter.application.contracts.learning import IngestDocumentRequest
    from study_supporter.domain.documents import Chunk
    import numpy as np

    pdf, root = Path(pdf).resolve(), Path(root).resolve()
    if root.exists() or not pdf.is_file():
        raise ValueError("A new snapshot directory and approved PDF are required")
    root.mkdir(parents=True)
    migrate_new_snapshot(root)
    with (factory_builder or factory_for)(root) as factory:
        factory.verify_schema()
        contexts = {}
        for alias in ("user_a", "user_b"):
            factory.authentication.register(alias, secrets.token_urlsafe(24))
            # Read back the fixture identity from the actual SQL account registry.
            from sqlalchemy import select
            from study_supporter.infrastructure.persistence.sqlalchemy.models import User
            from study_supporter.application.contracts.context import AppContext

            with factory.database.sessions() as session:
                identity = session.execute(
                    select(User.id).where(User.username == alias)
                ).scalar_one()
            contexts[alias] = AppContext(str(identity))
        result = factory.ingestion.execute(
            IngestDocumentRequest(contexts["user_a"], pdf.name, pdf.read_bytes(), "application/pdf")
        )
        first = factory.document_repository.get(contexts["user_a"].user_id, result.document_id)
        store = factory.vector_store(first)
        vectors = store.documents.get(include=["documents", "metadatas", "embeddings"])
        second = factory.document_repository.create(
            contexts["user_b"].user_id, pdf.name, file_hash(pdf)
        )
        # Clone the already-built production index for the cross-account probe. No second model/index algorithm.
        duplicate = factory.vector_store(second)
        chunks = [
            Chunk(
                chunk_id=cid,
                text=text,
                source=meta["source"],
                page_start=meta["page_start"],
                page_end=meta["page_end"],
                sentence_count=0,
            )
            for cid, text, meta in zip(vectors["ids"], vectors["documents"], vectors["metadatas"])
        ]
        duplicate.add_chunks(chunks, [list(v) for v in vectors["embeddings"]])
        factory.document_repository.update(
            contexts["user_b"].user_id,
            second["id"],
            status="ready",
            page_count=first["page_count"],
            chunk_count=len(chunks),
        )
        docs, indexed = {}, []
        for alias, document, user in (("doc_a", first, "user_a"), ("doc_b", second, "user_b")):
            docs[alias] = ApprovedDocument(
                document_id=str(document["id"]),
                user_fixture=user,
                topic_group="approved-source",
                content_family="approved-source",
                pdf_sha256=file_hash(pdf),
                page_count=first["page_count"],
                permission_reference=permission_reference,
                approved_by="user",
            )
            for chunk, vector in zip(chunks, vectors["embeddings"]):
                indexed.append(
                    IndexedChunk(
                        document=alias,
                        chunk_id=chunk.chunk_id,
                        page_start=chunk.page_start,
                        page_end=chunk.page_end,
                        text=chunk.text,
                        embedding_sha256=hashlib.sha256(
                            np.asarray(vector, dtype="<f4").tobytes()
                        ).hexdigest(),
                    )
                )
        corpus = CorpusSnapshot(
            embedding_revision=embedding_revision,
            database_revision="p0_0001",
            users={key: context.user_id for key, context in contexts.items()},
            documents=docs,
            chunks=tuple(indexed),
        )
        # Flush/stop the isolated Chroma system before freezing its on-disk payload.
        store.client._system.stop()
        corpus = corpus.model_copy(update={"payload_hashes": payload_hashes(root)})
        write_json(root / "corpus.json", corpus.model_dump(mode="json"))
    return corpus


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--permission-reference", required=True)
    parser.add_argument("--embedding-revision", required=True)
    args = parser.parse_args(argv)
    try:
        prepare(
            args.pdf,
            args.snapshot,
            permission_reference=args.permission_reference,
            embedding_revision=args.embedding_revision,
        )
        print('{"prepared":true,"provider_calls":0,"g1_accepted":false}')
        return 0
    except Exception:
        print('{"prepared":false,"error":"SNAPSHOT_PREPARATION_FAILED"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
