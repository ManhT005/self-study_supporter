"""Opt-in Gemini evaluation on isolated approved snapshots; never the application database."""

import argparse
import json
import re
import os
import subprocess
from pathlib import Path

from evaluation.datasets.v2.scripts.validate_labels import load_labels
from evaluation.live.fixtures import SnapshotFixtures, write_json
from evaluation.live.manifest import environment_metadata, manifest_for
from evaluation.live.runner import LiveCallbacks
from evaluation.live.provider import thinking_settings
from evaluation.live.gates import check_live_report
from evaluation.live.review_export import export_review
from evaluation.runner_v2 import run_comparison
from evaluation.schema import load_dataset, EvaluationRecord
from evaluation.scoring import summarize, paired_summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["online"], required=True)
    parser.add_argument("--purpose", choices=["smoke", "benchmark"], default="smoke")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--work-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model", default="gemini-3.1-flash-lite")
    parser.add_argument(
        "--budget", type=int, default=6, help="Maximum total generateContent attempts; no retries"
    )
    parser.add_argument("--max-output-tokens", type=int, default=768)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--git-sha")
    parser.add_argument("--git-dirty", action="store_true")
    parser.add_argument("--approval-record")
    args = parser.parse_args(argv)
    if (
        args.budget < 1
        or args.repetitions < 1
        or args.top_k < 1
        or not 1 <= args.max_output_tokens <= 2048
    ):
        parser.error("Positive bounded request/token/settings required")
    try:
        if not os.environ.get("GEMINI_API_KEY"):
            raise ValueError("Explicit Gemini credential environment required")
        fixtures = SnapshotFixtures(args.snapshot, args.work_root)
        private_root = fixtures.snapshot.parent
        for path in (Path(args.work_root).resolve(), Path(args.output_dir).resolve()):
            if private_root not in path.parents or path == fixtures.snapshot:
                raise ValueError("Work and review output must stay in the private snapshot sandbox")
        if args.purpose == "benchmark":
            cases = load_labels(args.dataset, fixtures.corpus, acceptance=True)
            approval = (
                json.loads(Path(args.approval_record).read_text(encoding="utf-8"))
                if args.approval_record
                else {}
            )
            if not approval.get("G1") or not approval.get("G2"):
                raise ValueError("Independent G1/G2 approvals required before benchmark")
        else:
            cases = load_dataset(args.dataset)
            if len(cases) > 3 or args.repetitions != 1:
                raise ValueError("Smoke is at most three cases and one repetition")
        if any(c.split == "holdout" for c in cases):
            raise ValueError("Holdout execution remains locked pending the final review protocol")
        if any(not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", c.case_id) for c in cases):
            raise ValueError("Only opaque case IDs may enter shared records")
        sha = (
            args.git_sha or subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        )
        dirty = (
            args.git_dirty
            if args.git_sha
            else bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
        )
        manifest = manifest_for(
            fixtures.corpus,
            args.dataset,
            git_sha=sha,
            git_dirty=dirty,
            model=args.model,
            top_k=args.top_k,
        )
        callbacks = LiveCallbacks(
            fixtures,
            {
                "model": args.model,
                "top_k": args.top_k,
                "max_output_tokens": args.max_output_tokens,
                "answer_timeout": 90,
            },
            max_calls=args.budget,
            max_samples=len(cases) * 2 * args.repetitions,
        )
        report = run_comparison(
            cases,
            {name: callbacks.variant(name) for name in ("rag_only", "legacy_react")},
            manifest,
            repetitions=args.repetitions,
        )
        # Request latency excludes fresh fixture provision/model warmup. Preserve total orchestration time separately.
        for row, telemetry in zip(report["records"], callbacks.telemetry):
            telemetry["sample_elapsed_ms"] = row["elapsed_ms"]
            if telemetry.get("answer_elapsed_ms") is not None:
                row["elapsed_ms"] = telemetry["answer_elapsed_ms"]
        parsed = [EvaluationRecord.model_validate(row) for row in report["records"]]
        report["summary"] = summarize(parsed)
        report["paired_deltas"] = paired_summary(
            parsed, ("rag_only", "legacy_react"), seed=manifest.seed
        )
        report["live"] = {
            "purpose": args.purpose,
            "g1_accepted": False,
            "g2_approved": False,
            "environment": environment_metadata(),
            "budget": {
                "max_calls": args.budget,
                "calls_attempted": callbacks.calls,
                "max_output_tokens": args.max_output_tokens,
                "transport_attempts": 1,
            },
            "thinking_config": thinking_settings(args.model),
            "samples": callbacks.telemetry,
        }
        output = Path(args.output_dir) / report["run_id"]
        output.mkdir(parents=True, exist_ok=False)
        write_json(output / "results.json", report)
        write_json(output / "answers.private.json", callbacks.review_answers)
        failures = check_live_report(report, cases, fixtures.corpus)
        report["live"]["engineering_gate"] = {"passed": not failures, "failures": failures}
        write_json(output / "results.json", report)
        export_review(output / "review", cases, callbacks.review_answers)
        print(
            json.dumps(
                {
                    "run_id": report["run_id"],
                    "purpose": args.purpose,
                    "records": len(parsed),
                    "calls_attempted": callbacks.calls,
                    "summary": report["summary"],
                }
            )
        )
        return 1 if failures else 0
    except Exception:
        print('{"error":"LIVE_EVALUATION_SETUP_FAILED","g1_accepted":false}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
