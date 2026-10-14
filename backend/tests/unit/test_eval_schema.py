import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from evaluation.schema import EvaluationCase, load_dataset

ROOT = Path(__file__).resolve().parents[3]
DATASET = ROOT / "evaluation/datasets/v1/smoke.jsonl"


def test_smoke_has_unique_labels_and_reproducible_source_hash(tmp_path):
    from evaluation.datasets.v1.fixtures.build_dataset import build
    from evaluation.synthetic import SyntheticEnvironment

    build(tmp_path)
    assert (tmp_path / "smoke.jsonl").read_bytes() == DATASET.read_bytes()
    assert (tmp_path / "fixtures/corpus.json").read_bytes() == (
        DATASET.parent / "fixtures/corpus.json"
    ).read_bytes()
    cases = load_dataset(DATASET)
    source_hash = SyntheticEnvironment(DATASET.parent / "fixtures/corpus.json", 3).source_hash
    assert len(cases) == 15 and all(c.source_hash == source_hash for c in cases)
    assert {c.category for c in cases} == {
        "factual",
        "synonyms",
        "multi_hop",
        "unanswerable",
        "privacy",
    }


@pytest.mark.parametrize(
    "change",
    [
        {"unexpected": "field"},
        {"question": " "},
        {"source_hash": "unversioned"},
        {"requires_history": True},
        {"must_abstain": True},
        {"document_ids": ["doc_a", "doc_a"]},
    ],
)
def test_invalid_labels_are_rejected(change):
    item = json.loads(DATASET.read_text(encoding="utf-8").splitlines()[0])
    with pytest.raises(ValidationError):
        EvaluationCase.model_validate({**item, **change})


def test_duplicate_case_ids_and_document_split_leakage_are_rejected(tmp_path):
    item = json.loads(DATASET.read_text(encoding="utf-8").splitlines()[0])
    path = tmp_path / "cases.jsonl"
    for second in [item, {**item, "case_id": "OTHER", "split": "holdout"}]:
        path.write_text(json.dumps(item) + "\n" + json.dumps(second), encoding="utf-8")
        with pytest.raises(ValueError):
            load_dataset(path)
