"""Live wiring uses real application/SQL/hybrid code with offline model/vector doubles."""

from dataclasses import asdict
from unittest.mock import Mock

import pytest

from apps.api.tests.fixtures import FixtureFactory
from evaluation.datasets.v2.schema_extensions import CorpusSnapshot
from evaluation.live.fixtures import SnapshotFixtures, payload_hashes, write_json
from evaluation.live.manifest import production_prompt_hash, manifest_for
from evaluation.live.variants import execute_variant
from evaluation.schema import EvaluationCase
from study_supporter.application.ports.llm import ChatResponse
from study_supporter.domain.documents import Chunk
from study_supporter.domain.errors import EvidenceNotFound


@pytest.fixture
def sql_snapshot(tmp_path):
    root = tmp_path / "snapshot"
    root.mkdir()
    with FixtureFactory(f"sqlite:///{root / 'app.db'}") as factory:
        users, docs, chunks = {}, {}, []
        for index, name in enumerate(("user_a", "user_b"), 1):
            factory.authentication.register(name, "offline-password")
            context = factory.authentication.authenticate(name, "offline-password")
            doc = factory.document_repository.create(context.user_id, "fixture.pdf", "a" * 64)
            factory.document_repository.update(
                context.user_id, doc["id"], status="ready", page_count=1, chunk_count=1
            )
            users[name] = context.user_id
            alias = "doc_a" if index == 1 else "doc_b"
            docs[alias] = {
                "document_id": str(doc["id"]),
                "user_fixture": name,
                "topic_group": "fixture",
                "content_family": "fixture",
                "pdf_sha256": "a" * 64,
                "page_count": 1,
                "permission_reference": "offline test",
                "approved_by": "test",
            }
            chunks.append(
                {
                    "document": alias,
                    "chunk_id": "fixture-chunk",
                    "page_start": 1,
                    "page_end": 1,
                    "text": "fixture owned evidence",
                    "embedding_sha256": "b" * 64,
                }
            )
    corpus = CorpusSnapshot(
        users=users,
        documents=docs,
        chunks=tuple(chunks),
        embedding_revision="offline-fixture",
        database_revision="p0_0001",
        payload_hashes=payload_hashes(root),
    )
    write_json(root / "corpus.json", corpus.model_dump(mode="json"))
    return SnapshotFixtures(root, tmp_path / "work")


def context_case(corpus, document="doc_a"):
    return EvaluationCase(
        case_id="FACT-1",
        category="factual",
        question="owned evidence?",
        user_fixture="user_a",
        document_ids=(document,),
        expected_doc_ids=(document,),
        relevant_chunk_ids=("fixture-chunk",),
        source_hash=corpus.source_hash,
        labeler="offline fixture",
    )


def populated_factory(root, corpus):
    factory = FixtureFactory(f"sqlite:///{root / 'app.db'}")
    for alias, doc in corpus.documents.items():
        store = factory.vector_store({"id": int(doc.document_id)})
        store.chunks = [
            Chunk(
                chunk_id=c.chunk_id,
                text=c.text,
                source="fixture.pdf",
                page_start=c.page_start,
                page_end=c.page_end,
                sentence_count=1,
            )
            for c in corpus.chunks
            if c.document == alias
        ]
    return factory


def test_real_sql_clone_resets_progress_between_variants_and_repetitions(sql_snapshot):
    fixture = sql_snapshot
    for _ in range(3):
        with fixture.lease() as root, populated_factory(root, fixture.corpus) as factory:
            user = fixture.corpus.users["user_a"]
            assert factory.progress_repository.get_summary(user)["total_attempts"] == 0
            factory.progress_repository.record_attempt(user, "topic", "question", True, 1)
            assert factory.progress_repository.get_summary(user)["total_attempts"] == 1
    fixture.verify()


def test_pinned_variants_reuse_production_hybrid_and_full_four_tool_prompt(sql_snapshot):
    fixture = sql_snapshot
    llm = Mock()
    llm.usage = [{"input_tokens": 3, "output_tokens": 4}]
    llm.chat.side_effect = [
        ChatResponse(text='Action: search_docs\nAction Input: {"query":"owned evidence"}'),
        ChatResponse(text="Final Answer: owned"),
    ]
    with fixture.lease() as root, populated_factory(root, fixture.corpus) as factory:
        result = execute_variant(
            factory, fixture.corpus, context_case(fixture.corpus), "legacy_react", llm
        )
        assert result.evidences[0].document_id == "doc_a"
        assert asdict(result.usage) == {"input_tokens": 3, "output_tokens": 4, "cost_usd": None}
        prompt = llm.chat.call_args.kwargs["system_prompt"]
        assert all(
            name in prompt for name in ("search_docs", "generate_quiz", "get_progress", "save_note")
        )
        import hashlib

        assert hashlib.sha256(prompt.encode("utf-8")).hexdigest() == production_prompt_hash()


def test_scope_is_enforced_by_sql_before_vector_or_model_access(sql_snapshot):
    fixture = sql_snapshot
    with fixture.lease() as root, populated_factory(root, fixture.corpus) as factory:
        vectors = Mock(wraps=factory.vector_store)
        factory.vector_store = vectors
        llm = Mock()
        with pytest.raises(EvidenceNotFound):
            execute_variant(
                factory, fixture.corpus, context_case(fixture.corpus, "doc_b"), "legacy_react", llm
            )
        vectors.assert_not_called()
        llm.chat.assert_not_called()


def test_manifest_preserves_full_prompt_and_model_index_identity(sql_snapshot, tmp_path):
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text("offline fixture", encoding="utf-8")
    manifest = manifest_for(
        sql_snapshot.corpus, dataset, git_sha="a" * 40, git_dirty=False, model="gemini-2.5-flash"
    )
    assert manifest.execution_mode == "online" and manifest.provider == "gemini"
    assert manifest.prompt_hashes["legacy_react"] == production_prompt_hash()
    assert manifest.index_hash == sql_snapshot.corpus.index_hash
    assert "synthetic" not in manifest.embedding_id
