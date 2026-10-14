import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from evaluation.gates import check_report, main as gate_main
from evaluation.runner_v2 import main as runner_main

ROOT = Path(__file__).resolve().parents[3]
GOLDEN = json.loads((ROOT / "evaluation/golden/v1.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    return runner_main(
        ["--repetitions", "3", "--output-dir", str(tmp_path_factory.mktemp("eval-golden"))]
    )


def test_tc_gate_01_frozen_report_and_semantics_pass_without_network(report, monkeypatch):
    import socket

    def no_network(*args, **kwargs):
        raise AssertionError("Offline gate attempted a network call")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    assert check_report(report, GOLDEN) == []
    assert len(report["records"]) == 90
    assert sum(s["n_completed"] for s in report["summary"].values()) == 78
    assert sum(s["n_expected_denied"] for s in report["summary"].values()) == 12
    assert sum(s["n_unexpected_failed"] for s in report["summary"].values()) == 0


def test_tc_gate_02_semantic_regression_is_detected_even_when_smoke_hits_every_chunk(
    report, monkeypatch
):
    from evaluation import gates

    real_score = gates.score_result

    def broken_recall(*args, **kwargs):
        scores = real_score(*args, **kwargs)
        if "recall_at_k" in scores:
            scores["recall_at_k"] = scores["hit_rate_at_k"]
        return scores

    monkeypatch.setattr(gates, "score_result", broken_recall)
    assert "metric_semantics:TC-EVAL-01a" in check_report(report, GOLDEN)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_case",
        "duplicate",
        "wrong_score",
        "unknown_forced_valid",
        "missing_metric_version",
        "bad_hash",
        "missing_expected_error",
        "unexpected_error",
        "denied_evidence",
        "bad_page",
        "paired_statistics",
        "foreign_retrieval",
    ],
)
def test_negative_structural_reports_fail(report, mutation):
    altered = copy.deepcopy(report)
    if mutation == "missing_case":
        altered["records"].pop()
    elif mutation == "duplicate":
        altered["records"][-1] = altered["records"][0]
    elif mutation == "wrong_score":
        altered["records"][0]["scores"]["recall_at_k"] = 0.25
    elif mutation == "unknown_forced_valid":
        altered["records"][0]["scores"]["tool_validation_rate"] = 1.0
    elif mutation == "missing_metric_version":
        altered["manifest"].pop("metric_schema_version")
    elif mutation == "bad_hash":
        altered["manifest"]["prompt_hashes"]["rag_only"] = "a" * 64
    elif mutation == "missing_expected_error":
        row = next(r for r in altered["records"] if r["error_code"] == "AUTH_SCOPE")
        row.update(status="completed", error_code=None)
    elif mutation == "unexpected_error":
        altered["records"][0].update(status="error", error_code="PROVIDER_ERROR")
    elif mutation == "denied_evidence":
        row = next(r for r in altered["records"] if r["error_code"] == "AUTH_SCOPE")
        row["retrieved_chunk_ids"] = ["foreign"]
    elif mutation == "bad_page":
        altered["records"][0]["retrieved_evidence"][0]["page_start"] = 999
    elif mutation == "paired_statistics":
        altered["paired_deltas"]["candidates"]["legacy_react"]["recall_at_k"]["mean_delta"] = 0.5
    elif mutation == "foreign_retrieval":
        altered["records"][0]["retrieval_calls"][0]["chunk_ids"] = ["security-password"]
    assert check_report(altered, GOLDEN)


def test_cli_exits_nonzero_for_bad_metrics_and_malformed_json(report, tmp_path):
    altered = copy.deepcopy(report)
    altered["records"].pop()
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(altered), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.gates", "--report", str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1 and not json.loads(result.stdout)["passed"]
    path.write_text("raw-secret-malformed", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.gates", "--report", str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 2 and "raw-secret" not in result.stdout + result.stderr


@pytest.mark.parametrize("selection", [None, "bad", {"repetitions": 3, "case_ids": None}])
def test_malformed_report_shape_fails_closed(report, selection):
    altered = {**report, "selection": selection}
    assert check_report(altered, GOLDEN) == ["invalid_report_or_golden"]


def test_ci_path_file_references_the_actual_generated_report(tmp_path, capsys):
    pointer = tmp_path / "report-path.txt"
    runner_main(
        ["--repetitions", "3", "--output-dir", str(tmp_path), "--report-path-file", str(pointer)]
    )
    assert Path(pointer.read_text(encoding="utf-8").strip()).is_file()
    assert gate_main(["--report-path-file", str(pointer)]) == 0


def test_expected_denial_not_observed_is_an_unexpected_failure():
    from evaluation.schema import EvaluationRecord
    from evaluation.scoring import summarize

    record = EvaluationRecord(
        run_id="run",
        case_id="SCOPE-001",
        category="privacy",
        variant="legacy_react",
        repetition=0,
        status="completed",
        elapsed_ms=1,
        expected_error="AUTH_SCOPE",
        scores={"expected_error_match": 0.0},
    )
    summary = summarize([record])["legacy_react"]
    assert summary["n_unexpected_failed"] == 1
    assert summary["n_completed"] == summary["n_expected_denied"] == summary["n_incomplete"] == 0
