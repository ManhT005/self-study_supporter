"""Offline timing harness; synthetic SQL/PDF/BM25/ReAct, no provider or Chroma IO."""

import argparse
import hashlib
import json
import math
import platform
import subprocess
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory

import fitz

from study_supporter.application.contracts.context import AppContext
from study_supporter.application.contracts.learning import IngestDocumentRequest
from study_supporter.application.ports.llm import ChatResponse, LLMAdapter
from study_supporter.application.telemetry import capture_timings, timed
from study_supporter.bootstrap import ApplicationFactory
from study_supporter.config import Settings
from study_supporter.infrastructure.llm.factory import ProviderSelection
from study_supporter.infrastructure.persistence.chroma.vector_store import VectorStore
from study_supporter.infrastructure.persistence.sqlalchemy.database import Base
from study_supporter.infrastructure.persistence.sqlalchemy.models import User

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = "r1-synthetic-pdf-v1:3-pages:transactions-retrieval-replay"


class SyntheticEmbeddings:
    dimension = 1024

    @timed("embedding")
    def embed(self, texts, task_type):
        # No learned model; reproducible, nonzero vectors for the chunking pipeline.
        vectors = []
        for text in texts:
            digest = hashlib.sha256(text.encode()).digest()
            vectors.append([1.0 + digest[i % 32] / 255.0 for i in range(self.dimension)])
        return vectors


class SyntheticLLM(LLMAdapter):
    def chat(self, messages, system_prompt=None, stop_sequences=None):
        if "Observation:" not in messages[-1]["content"]:
            return ChatResponse(
                'Action: search_docs\nAction Input: {"query": "transaction replay", "top_k": 3}'
            )
        return ChatResponse("Final Answer: Synthetic fixture response.")


class SyntheticCollection:
    def __init__(self):
        self.rows = {}

    def upsert(self, ids, embeddings, documents, metadatas):
        for key, text, meta in zip(ids, documents, metadatas):
            self.rows[key] = (text, meta)

    def get(self, ids=None, include=None):
        selected = list(self.rows) if ids is None else [key for key in ids if key in self.rows]
        return {
            "ids": selected,
            "documents": [self.rows[key][0] for key in selected],
            "metadatas": [self.rows[key][1] for key in selected],
        }

    def count(self):
        return len(self.rows)

    def query(self, query_embeddings, n_results):
        # Rank fixture IDs only; this is explicitly not a vector relevance benchmark.
        return {"ids": [list(self.rows)[:n_results]]}


class SyntheticStore(VectorStore):
    def __init__(self):
        # Exercise VectorStore.load_all_chunks against an in-memory Chroma-shaped double.
        self.documents = SyntheticCollection()
        self.user_memory = SyntheticCollection()


class SyntheticFactory(ApplicationFactory):
    def __init__(self, settings):
        self.stores = {}
        super().__init__(
            settings,
            embedding=SyntheticEmbeddings(),
            provider_factory=lambda settings, mode: ProviderSelection(SyntheticLLM(), "synthetic"),
        )

    def vector_store(self, document):
        return self.stores.setdefault(document["id"], SyntheticStore())


def fixture_pdf():
    with fitz.open() as document:
        for text in (
            "Transactions commit durable state. A transaction rollback preserves earlier state.",
            "Retrieval finds source evidence. Evidence supports source linked answers.",
            "Replay returns a stored result. Transaction replay must avoid duplicate attempts.",
        ):
            page = document.new_page()
            page.insert_text((72, 72), text)
        return document.tobytes(no_new_id=True)


def percentile(values, quantile):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * quantile) - 1)]


def summarize(records):
    groups = {}
    for record in records:
        groups.setdefault((record["phase"], record["operation"]), []).append(record)
    return [
        {
            "phase": phase,
            "operation": operation,
            "samples": len(rows),
            "errors": sum(row["status"] != "ok" for row in rows),
            "p50_ms": percentile([row["duration_ms"] for row in rows], 0.5),
            "p95_ms": percentile([row["duration_ms"] for row in rows], 0.95),
        }
        for (phase, operation), rows in sorted(groups.items())
    ]


def run_profile(repetitions=5):
    if type(repetitions) is not int or not 1 <= repetitions <= 100:
        raise ValueError("Repetitions must be between 1 and 100")
    records = []
    content = fixture_pdf()
    with TemporaryDirectory(prefix="r1-profile-") as directory:
        settings = Settings(database_url=f"sqlite:///{directory}/profile.db")
        with SyntheticFactory(settings) as factory:
            # Disposable synthetic fixture only; deployment schema remains Alembic-owned.
            Base.metadata.create_all(factory.database.engine)
            with factory.database.sessions() as session:
                session.add(User(id=1, username="fixture", password_hash="fixture-only"))
                session.commit()
            context = AppContext("1")

            def capture(phase):
                return capture_timings(
                    lambda event: records.append({"phase": phase, **event.to_dict()})
                )

            with capture("ingestion"):
                document = factory.ingestion.execute(
                    IngestDocumentRequest(context, "fixture.pdf", content, "application/pdf")
                )
            for _ in range(repetitions):
                with capture("cold_session"):
                    learning = factory.open_document(context, document.document_id)
                    result = learning.answer("How does transaction replay work?")
                    if not result.evidences:
                        raise RuntimeError("Synthetic retrieval did not produce evidence")
                with capture("warm_session"):
                    learning.answer("How does transaction replay work?")
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True))
    return {
        "schema_version": 1,
        "work_package": "WP-01",
        "commit_sha": sha,
        "working_tree_dirty": dirty,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "environment": {"python": platform.python_version(), "platform": platform.system()},
        "package_versions": {
            name: version(name) for name in ("numpy", "rank-bm25", "sqlalchemy", "pymupdf")
        },
        "fixture_id": FIXTURE,
        "fixture_sha256": hashlib.sha256(content).hexdigest(),
        "model": "synthetic-sha256-1024D; scripted-llm",
        "storage": "disposable SQLite; in-memory Chroma double",
        "repetitions": repetitions,
        "reviewer": None,
        "result": "SYNTHETIC_ONLY",
        "limitations": [
            "Not real BGE/LLM/Chroma latency or an AI quality result.",
            "Cold means a new learning session, not a cold process/model.",
            "Samples use inclusive wall time; nested spans must not be summed.",
            "Few samples cannot establish a pilot SLO; human review is pending.",
        ],
        "summary": summarize(records),
        "records": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--output", type=Path, default=ROOT / "data/r1/baseline-profile.json")
    args = parser.parse_args()
    if not 1 <= args.repetitions <= 100:
        parser.error("--repetitions must be between 1 and 100")
    report = run_profile(args.repetitions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Synthetic profile: {len(report['records'])} spans; {args.output.name}")


if __name__ == "__main__":
    main()
