"""Immutable local snapshots and disposable per-invocation SQL/Chroma clones."""

import hashlib
import json
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from evaluation.datasets.v2.schema_extensions import CorpusSnapshot


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def payload_hashes(root):
    root = Path(root)
    return {
        path.relative_to(root).as_posix(): file_hash(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "corpus.json"
    }


class SnapshotFixtures:
    def __init__(self, snapshot, work_root):
        self.snapshot, self.work_root = Path(snapshot).resolve(), Path(work_root).resolve()
        if (
            self.snapshot == self.work_root
            or self.snapshot in self.work_root.parents
            or self.work_root in self.snapshot.parents
        ):
            raise ValueError("Snapshot and writable work root must be disjoint")
        self.corpus = CorpusSnapshot.model_validate_json(
            (self.snapshot / "corpus.json").read_text(encoding="utf-8")
        )
        self._corpus_hash = file_hash(self.snapshot / "corpus.json")
        if not self.corpus.payload_hashes or "app.db" not in self.corpus.payload_hashes:
            raise ValueError("Frozen SQL/Chroma payload fingerprints required")
        self.verify()

    def verify(self):
        if file_hash(self.snapshot / "corpus.json") != self._corpus_hash:
            raise ValueError("Frozen corpus metadata changed")
        if payload_hashes(self.snapshot) != self.corpus.payload_hashes:
            raise ValueError("Frozen fixture payload changed")

    @contextmanager
    def lease(self):
        self.verify()
        self.work_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="sample-", dir=self.work_root) as directory:
            target = Path(directory).resolve()
            if target.parent != self.work_root:
                raise ValueError("Writable sample escaped work root")
            shutil.copytree(self.snapshot, target / "fixture")
            try:
                yield target / "fixture"
            finally:
                self.verify()


def factory_for(root, *, embedding=None):
    from study_supporter.bootstrap import ApplicationFactory
    from study_supporter.config import Settings

    return ApplicationFactory(
        Settings(
            database_url="sqlite:///" + (Path(root).resolve() / "app.db").as_posix(),
            chroma_path=str(Path(root).resolve() / "chroma"),
            chroma_host="",
        ),
        embedding=embedding,
    )


def read_corpus(root):
    return CorpusSnapshot.model_validate_json(
        (Path(root) / "corpus.json").read_text(encoding="utf-8")
    )


def write_json(path, value):
    Path(path).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
