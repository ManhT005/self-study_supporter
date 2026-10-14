"""Fail closed on versioned synthetic structural regressions; never grade live model quality."""

import argparse
import itertools
import json
import math
import hashlib
from pathlib import Path

from pydantic import Field

from evaluation.schema import (
    EvaluationCase,
    EvaluationRecord,
    RunManifest,
    StrictModel,
    dataset_hash,
    load_dataset,
)
from evaluation.scoring import paired_summary, score_result, summarize
from study_supporter.application.contracts.agent import AgentResult, RetrievalCall, ToolCall
from study_supporter.application.contracts.retrieval import Evidence


class GoldenPolicy(StrictModel):
    golden_version: str
    metric_schema_version: str
    manifest: dict
    dataset_path: str
    repetitions: int = Field(ge=1)
    cases: dict[str, dict] = Field(min_length=1)
    summary: dict = Field(min_length=1)
    metric_cases: tuple[dict, ...] = Field(min_length=1)


class _Selection(StrictModel):
    case_ids: tuple[str, ...] = Field(min_length=1)
    repetitions: int = Field(ge=1)


class _Report(StrictModel):
    run_id: str = Field(min_length=1)
    manifest: RunManifest
    selection: _Selection
    records: tuple[EvaluationRecord, ...] = Field(min_length=1)
    summary: dict
    paired_deltas: dict


def _matches(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and _matches(actual[key], value) for key, value in expected.items()
        )
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return type(actual) in (int, float) and math.isclose(actual, expected, abs_tol=1e-12)
    return type(actual) is type(expected) and actual == expected


def _semantic_scores(item, source_hash):
    case = EvaluationCase(
        case_id=item["id"],
        category="factual" if item["gold"] else "unanswerable",
        question="synthetic semantic fixture",
        user_fixture="user_a",
        document_ids=("doc_a",),
        expected_doc_ids=("doc_a",),
        relevant_chunk_ids=tuple(item["gold"]),
        allowed_tools=tuple(item.get("allowed_tools", ["search_docs"])),
        required_tools=tuple(item.get("required_tools", [])),
        must_abstain=not item["gold"],
        source_hash=source_hash,
        labeler="semantic-golden/v1",
    )
    result = AgentResult(
        "synthetic",
        tuple(Evidence(c, "doc_a", "fixture", "synthetic", 1, 1) for c in item["evidence"]),
        "synthetic",
        tool_calls=tuple(ToolCall(name) for name in item.get("tool_calls", [])),
        retrieval_calls=tuple(
            RetrievalCall("0" * 64, item["top_k"], tuple(chunks)) for chunks in item["searches"]
        ),
    )
    return score_result(case, result, item["top_k"], tool_capable=item.get("tool_capable"))


def check_report(report: dict, golden: dict) -> list[str]:
    """Return safe failure codes, without echoing report contents or parser exceptions."""
    try:
        policy = GoldenPolicy.model_validate(golden)
        parsed = _Report.model_validate(report)
        manifest, records = parsed.manifest, list(parsed.records)
        dataset = Path(__file__).resolve().parents[1] / policy.dataset_path
        if dataset_hash(dataset) != manifest.dataset_sha256:
            return ["frozen_dataset"]
        labels_by_id = {case.case_id: case for case in load_dataset(dataset)}
        corpus_bytes = (dataset.parent / "fixtures/corpus.json").read_bytes()
        if "sha256:" + hashlib.sha256(corpus_bytes).hexdigest() != manifest.source_hash:
            return ["frozen_source"]
        source = json.loads(corpus_bytes)
        known_evidence = {(e["document_id"], e["chunk_id"]): e for e in source["chunks"]}
    except (OSError, ValueError, KeyError, TypeError):
        return ["invalid_report_or_golden"]
    failures = []
    if report["manifest"].get("metric_schema_version") != policy.metric_schema_version:
        failures.append("metric_schema_version")
    if manifest.execution_mode != "offline" or not _matches(report["manifest"], policy.manifest):
        failures.append("frozen_manifest")
    if (
        parsed.selection.repetitions != policy.repetitions
        or set(parsed.selection.case_ids) != set(policy.cases)
        or len(parsed.selection.case_ids) != len(policy.cases)
    ):
        failures.append("case_selection")
    variants = set(policy.summary)
    expected = set(itertools.product(policy.cases, variants, range(policy.repetitions)))
    actual = [(r.case_id, r.variant, r.repetition) for r in records]
    if set(actual) != expected or len(actual) != len(expected):
        failures.append("paired_case_membership")
    for record in records:
        labels = policy.cases.get(record.case_id)
        if labels is None:
            continue
        if record.run_id != report.get("run_id") or record.category != labels["category"]:
            failures.append("record_identity")
        if record.expected_error != labels.get("expected_error"):
            failures.append("expected_error_label")
        if record.expected_error:
            if record.status != "error" or record.error_code != record.expected_error:
                failures.append("expected_denial_missing")
            if (
                record.retrieved_chunk_ids
                or record.retrieved_evidence
                or record.citations
                or record.retrieval_calls
                or record.tools_used
                or record.steps
                or record.answer_sha256
            ):
                failures.append("denial_contains_activity_or_evidence")
        elif record.status != "completed" or record.error_code is not None:
            failures.append("unexpected_execution_failure")
        if record.supporting_citations is not None or record.citations != record.retrieved_evidence:
            failures.append("unverified_citation_support")
        if record.usage is not None:
            failures.append("synthetic_usage_must_be_unknown")
        if record.expected_error and record.scores.get("expected_error_match") != 1.0:
            failures.append("expected_error_score")
        case = labels_by_id.get(record.case_id)
        if case:
            for evidence in record.retrieved_evidence:
                known = known_evidence.get((evidence.document_id, evidence.chunk_id))
                if (
                    not known
                    or evidence.document_id not in case.expected_doc_ids
                    or (evidence.page_start, evidence.page_end)
                    != (known["page_start"], known["page_end"])
                ):
                    failures.append("invalid_retrieved_provenance")
            if record.retrieved_chunk_ids != tuple(e.chunk_id for e in record.retrieved_evidence):
                failures.append("retrieved_ids_mismatch")
            allowed_chunks = {
                chunk for (doc, chunk) in known_evidence if doc in case.expected_doc_ids
            }
            if any(set(call.chunk_ids) - allowed_chunks for call in record.retrieval_calls):
                failures.append("invalid_retrieval_call_provenance")
            result = (
                None
                if record.status == "error"
                else AgentResult(
                    "",
                    tuple(
                        Evidence(
                            e.chunk_id, e.document_id, "", "synthetic", e.page_start, e.page_end
                        )
                        for e in record.retrieved_evidence
                    ),
                    record.trace_id or "synthetic",
                    tool_calls=tuple(ToolCall(name) for name in record.tools_used),
                    retrieval_calls=tuple(
                        RetrievalCall(c.query_sha256, c.top_k, c.chunk_ids)
                        for c in record.retrieval_calls
                    ),
                )
            )
            recomputed = score_result(
                case,
                result,
                manifest.top_k,
                tool_capable=manifest.tool_capabilities.get(record.variant),
            )
            if case.expected_error:
                recomputed["expected_error_match"] = float(
                    record.status == "error" and record.error_code == case.expected_error
                )
            if record.scores != recomputed:
                failures.append("record_metric_mismatch")
    computed = summarize(records)
    if report.get("summary") != computed:
        failures.append("summary_record_mismatch")
    if not _matches(computed, policy.summary):
        failures.append("golden_structural_thresholds")
    if report["paired_deltas"] != paired_summary(records, variants, seed=manifest.seed):
        failures.append("paired_statistics_mismatch")
    for item in policy.metric_cases:
        try:
            scores = _semantic_scores(item, manifest.source_hash)
            if any(
                not _matches(scores.get(name), value) for name, value in item["expected"].items()
            ):
                failures.append("metric_semantics:" + item["id"])
        except (ValueError, KeyError, TypeError):
            failures.append("invalid_semantic_fixture")
    return sorted(set(failures))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--report")
    source.add_argument("--report-path-file")
    parser.add_argument("--golden", default="evaluation/golden/v1.json")
    args = parser.parse_args(argv)
    try:
        path = args.report or Path(args.report_path_file).read_text(encoding="utf-8").strip()
        report = json.loads(Path(path).read_text(encoding="utf-8"))
        golden = json.loads(Path(args.golden).read_text(encoding="utf-8"))
        failures = check_report(report, golden)
    except (OSError, ValueError, TypeError, KeyError):
        print(json.dumps({"passed": False, "failures": ["invalid_report_or_golden"]}))
        return 2
    print(json.dumps({"passed": not failures, "failures": failures}))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
