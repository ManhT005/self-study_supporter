import json
import subprocess
from pathlib import Path

import pytest

from evaluation.datasets.v2.schema_extensions import BenchmarkCase, CorpusSnapshot
from evaluation.datasets.v2.scripts.validate_labels import validate_cases


def corpus_fixture():
    return CorpusSnapshot(
        embedding_revision="offline-fixture",
        database_revision="p0_0001",
        users={"user_a": "1", "user_b": "2"},
        documents={
            "doc_a": {
                "document_id": "1",
                "user_fixture": "user_a",
                "topic_group": "topic_a",
                "content_family": "content_a",
                "pdf_sha256": "a" * 64,
                "page_count": 2,
                "permission_reference": "synthetic test",
                "approved_by": "test-only",
            }
        },
        chunks=(
            {
                "document": "doc_a",
                "chunk_id": "chunk_a",
                "page_start": 1,
                "page_end": 1,
                "text": "fixture reference fact",
                "embedding_sha256": "b" * 64,
            },
        ),
    )


def case_fixture(corpus, **changes):
    label = {
        "expected_doc_ids": ["doc_a"],
        "relevant_chunk_ids": ["chunk_a"],
        "reference_facts": ["fixture reference fact"],
        "must_abstain": False,
        "allowed_tools": ["search_docs"],
        "required_tools": ["search_docs"],
        "expected_error": None,
    }
    item = {
        "case_id": "FACT-1",
        "category": "factual",
        "question": "fixture question?",
        "user_fixture": "user_a",
        "document_ids": ["doc_a"],
        "labeler": "test-consensus",
        "source_hash": corpus.source_hash,
        **label,
        "annotations": [
            {"annotator": name, "independently_submitted": True, "label": label}
            for name in ("test-author-a", "test-author-b")
        ],
        "fact_support": [
            {
                "fact_index": 0,
                "document": "doc_a",
                "chunk_id": "chunk_a",
                "quote": "reference fact",
                "page_start": 1,
                "page_end": 1,
            }
        ],
        **changes,
    }
    return item


def test_bl_data_02_source_fact_support_is_checked_but_not_claimed_as_human_acceptance():
    corpus = corpus_fixture()
    case = BenchmarkCase.model_validate(case_fixture(corpus))
    result = validate_cases([case], corpus)
    assert result["n_cases"] == 1 and result["g1_accepted"] is False
    with pytest.raises(ValueError):
        validate_cases([case], corpus, acceptance=True)


@pytest.mark.parametrize(
    "mutation",
    ["duplicate_annotator", "missing_vote", "not_independent", "disagreement", "wrong_consensus"],
)
def test_bl_data_01_06_invalid_or_unreconciled_annotations_are_rejected(mutation):
    item = case_fixture(corpus_fixture())
    if mutation == "duplicate_annotator":
        item["annotations"][1]["annotator"] = item["annotations"][0]["annotator"]
    elif mutation == "missing_vote":
        item["annotations"].pop()
    elif mutation == "not_independent":
        item["annotations"][1]["independently_submitted"] = False
    elif mutation == "disagreement":
        item["annotations"][1]["label"] = {
            **item["annotations"][1]["label"],
            "reference_facts": ["different"],
        }
    else:
        item["reference_facts"] = ["unsupported gold"]
    with pytest.raises(ValueError):
        BenchmarkCase.model_validate(item)


def test_disagreement_requires_a_third_adjudicator_and_explicit_resolved_gold():
    corpus = corpus_fixture()
    item = case_fixture(corpus)
    item["annotations"][1]["label"] = {
        **item["annotations"][1]["label"],
        "reference_facts": ["different"],
    }
    item["adjudicator"] = "test-author-c"
    item["adjudicated_label"] = item["annotations"][0]["label"]
    case = BenchmarkCase.model_validate(item)
    assert validate_cases([case], corpus)["adjudicated"] == 1


@pytest.mark.parametrize(
    "mutation", ["source_hash", "user", "chunk", "page", "quote", "unsupported_fact"]
)
def test_bl_data_02_04_05_scope_source_and_support_fail_closed(mutation):
    corpus = corpus_fixture()
    item = case_fixture(corpus)
    if mutation == "source_hash":
        item["source_hash"] = "sha256:" + "c" * 64
    elif mutation == "user":
        item["user_fixture"] = "user_b"
    elif mutation == "chunk":
        item["fact_support"][0]["chunk_id"] = "missing"
    elif mutation == "page":
        item["fact_support"][0]["page_start"] = 2
    elif mutation == "quote":
        item["fact_support"][0]["quote"] = "invented quote"
    else:
        item["fact_support"] = []
    with pytest.raises(ValueError):
        validate_cases([BenchmarkCase.model_validate(item)], corpus)


def test_bl_data_03_document_topic_content_and_hash_cannot_cross_splits():
    corpus = corpus_fixture()
    first = BenchmarkCase.model_validate(case_fixture(corpus))
    second = BenchmarkCase.model_validate(case_fixture(corpus, case_id="FACT-2", split="holdout"))
    with pytest.raises(ValueError):
        validate_cases([first, second], corpus)
    with pytest.raises(ValueError):
        validate_cases([first, first], corpus)


def test_bl_data_07_private_pdf_labels_and_snapshots_are_not_tracked():
    root = Path(__file__).resolve().parents[3]
    tracked = subprocess.check_output(["git", "ls-files", "data", "*.pdf"], cwd=root, text=True)
    assert not tracked.strip()
    result = subprocess.run(
        ["git", "check-ignore", "data/eval_private/v2/corpus.json"], cwd=root, capture_output=True
    )
    assert result.returncode == 0


@pytest.mark.parametrize("category", ["quiz", "personalized", "multi_hop"])
def test_category_specific_gold_requires_quiz_history_or_multiple_evidence(category):
    with pytest.raises(ValueError):
        BenchmarkCase.model_validate(case_fixture(corpus_fixture(), category=category))


def test_validator_cli_sanitizes_invalid_private_inputs(tmp_path, capsys):
    from evaluation.datasets.v2.scripts.validate_labels import main

    path = tmp_path / "bad.jsonl"
    path.write_text("private-secret-not-json", encoding="utf-8")
    assert main(["--dataset", str(path), "--corpus", str(path)]) == 1
    output = capsys.readouterr().out
    assert (
        "private-secret" not in output and json.loads(output)["error"] == "INVALID_BENCHMARK_LABELS"
    )
