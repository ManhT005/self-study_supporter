"""Paired, adapter-based evaluation. CLI is synthetic/offline; live callbacks are opt-in."""

import argparse
import hashlib
import json
import platform
import random
import subprocess
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from pathlib import Path

from evaluation.errors import error_code
from evaluation.schema import (
    CitationRecord,
    EvaluationCase,
    EvaluationRecord,
    RunManifest,
    RetrievalRecord,
    dataset_hash,
    load_dataset,
)
from evaluation.scoring import paired_summary, score_result, summarize
from study_supporter.application.contracts.agent import AgentResult

Variant = Callable[[EvaluationCase], AgentResult]


def run_comparison(
    cases: Sequence[EvaluationCase],
    variants: Mapping[str, Variant],
    manifest: RunManifest,
    *,
    repetitions: int = 1,
    limit: int | None = None,
) -> dict:
    if not cases or not variants or repetitions < 1 or (limit is not None and limit < 1):
        raise ValueError("Nonempty cases/variants and positive repetition/limit are required")
    if any(case.source_hash != manifest.source_hash for case in cases):
        raise ValueError("Cases and manifest must use the same frozen source snapshot")
    if set(variants) != set(manifest.prompt_hashes):
        raise ValueError("Every variant requires a pinned prompt hash")
    selected = cases[:limit] if limit is not None else cases
    if len({case.case_id for case in selected}) != len(selected):
        raise ValueError("Duplicate case IDs")
    run_id = uuid.uuid4().hex
    rng = random.Random(manifest.seed)
    records = []
    for case in selected:
        for repetition in range(repetitions):
            order = list(variants)
            rng.shuffle(order)
            for name in order:
                started = time.perf_counter()
                try:
                    result = variants[name](case)
                    if not isinstance(result, AgentResult):
                        raise ValueError("Variant must return AgentResult")
                    elapsed = (time.perf_counter() - started) * 1000
                    scores = score_result(
                        case,
                        result,
                        manifest.top_k,
                        tool_capable=manifest.tool_capabilities.get(name),
                    )
                    if case.expected_error:
                        scores["expected_error_match"] = 0.0
                    record = EvaluationRecord(
                        run_id=run_id,
                        case_id=case.case_id,
                        category=case.category,
                        variant=name,
                        repetition=repetition,
                        status=result.status.value,
                        elapsed_ms=elapsed,
                        trace_id=result.trace_id,
                        answer_sha256=hashlib.sha256(result.answer.encode("utf-8")).hexdigest(),
                        retrieved_chunk_ids=tuple(e.chunk_id for e in result.evidences),
                        citations=tuple(
                            CitationRecord(
                                document_id=e.document_id,
                                chunk_id=e.chunk_id,
                                page_start=e.page_start,
                                page_end=e.page_end,
                            )
                            for e in result.evidences
                        ),
                        retrieved_evidence=tuple(
                            CitationRecord(
                                document_id=e.document_id,
                                chunk_id=e.chunk_id,
                                page_start=e.page_start,
                                page_end=e.page_end,
                            )
                            for e in result.evidences
                        ),
                        expected_error=case.expected_error,
                        steps=result.steps,
                        retrieval_calls=tuple(
                            RetrievalRecord(**asdict(c)) for c in result.retrieval_calls
                        ),
                        tools_used=tuple(c.name for c in result.tool_calls),
                        usage=asdict(result.usage) if result.usage is not None else None,
                        scores=scores,
                    )
                except Exception as exc:
                    elapsed = (time.perf_counter() - started) * 1000
                    code = error_code(exc)
                    scores = score_result(
                        case,
                        None,
                        manifest.top_k,
                        tool_capable=manifest.tool_capabilities.get(name),
                    )
                    if case.expected_error:
                        scores["expected_error_match"] = float(code == case.expected_error)
                    record = EvaluationRecord(
                        run_id=run_id,
                        case_id=case.case_id,
                        category=case.category,
                        variant=name,
                        repetition=repetition,
                        status="error",
                        elapsed_ms=elapsed,
                        error_code=code,
                        expected_error=case.expected_error,
                        scores=scores,
                    )
                records.append(record)
    return {
        "run_id": run_id,
        "manifest": manifest.model_dump(mode="json"),
        "selection": {"case_ids": [c.case_id for c in selected], "repetitions": repetitions},
        "records": [r.model_dump(mode="json") for r in records],
        "summary": summarize(records),
        "paired_deltas": paired_summary(records, variants, seed=manifest.seed),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="evaluation/datasets/v1/smoke.jsonl")
    parser.add_argument("--corpus", default="evaluation/datasets/v1/fixtures/corpus.json")
    parser.add_argument("--output-dir", default="data/evaluations")
    parser.add_argument("--report-path-file", help="Write the exact generated JSON path for CI")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument(
        "--split", choices=["development", "validation", "holdout"], default="development"
    )
    args = parser.parse_args(argv)
    if args.repetitions < 1 or args.top_k < 1 or (args.limit is not None and args.limit < 1):
        parser.error("repetitions, top-k and limit must be positive")
    # Validate labels before constructing even an offline environment.
    all_cases = load_dataset(args.dataset)
    cases = tuple(c for c in all_cases if c.split == args.split)
    if not cases:
        parser.error("Selected split is empty")
    from evaluation.synthetic import SyntheticEnvironment

    environment = SyntheticEnvironment(Path(args.corpus), args.top_k)
    variants = {name: environment.variant(name) for name in ("rag_only", "legacy_react")}
    git_root = Path(__file__).resolve().parents[1]
    manifest = RunManifest(
        git_sha=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=git_root, text=True
        ).strip(),
        git_dirty=bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=git_root, text=True
            ).strip()
        ),
        dataset_sha256=dataset_hash(args.dataset),
        source_hash=environment.source_hash,
        execution_mode="offline",
        provider="synthetic",
        model_id="synthetic-echo-v1",
        prompt_hashes=environment.prompt_hashes(),
        tool_capabilities={"rag_only": False, "legacy_react": True},
        embedding_id="none/synthetic-lexical-v1",
        index_hash=environment.source_hash,
        top_k=args.top_k,
        seed=args.seed,
        python_version=platform.python_version(),
        platform=platform.platform(),
    )
    report = run_comparison(
        cases, variants, manifest, repetitions=args.repetitions, limit=args.limit
    )
    output = Path(args.output_dir) / report["run_id"]
    output.mkdir(parents=True, exist_ok=False)
    (output / "results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if args.report_path_file:
        Path(args.report_path_file).write_text(
            str(output / "results.json") + "\n", encoding="utf-8"
        )
    print(
        json.dumps(
            {"output": str(output), "execution_mode": "offline", "summary": report["summary"]},
            indent=2,
        )
    )
    return report


if __name__ == "__main__":
    main()
