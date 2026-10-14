"""One isolated invocation; subprocess exit releases SQL/Chroma before clone cleanup."""

import argparse
import os
import time
from dataclasses import asdict
from pathlib import Path

from evaluation.errors import error_code
from evaluation.live.fixtures import factory_for, read_corpus, write_json
from evaluation.live.provider import PinnedGemini, RequestBudget
from evaluation.live.variants import execute_variant, validate_scope
from evaluation.schema import EvaluationCase
from study_supporter.domain.errors import EvidenceNotFound


def run_worker(root, case, variant, settings, journal):
    corpus = read_corpus(root)
    llm = None
    answer_started = None
    started = time.perf_counter()
    try:
        with factory_for(root) as factory:
            factory.verify_schema()
            try:
                validate_scope(factory, corpus, case)
            except EvidenceNotFound:
                return {
                    "error_code": "AUTH_SCOPE",
                    "telemetry": {
                        "answer_elapsed_ms": (time.perf_counter() - started) * 1000,
                        "calls_attempted": 0,
                    },
                }
            if settings.get("provider_blocked") or settings["max_calls"] <= 0:
                return {
                    "error_code": "PROVIDER_ERROR",
                    "telemetry": {
                        "answer_elapsed_ms": (time.perf_counter() - started) * 1000,
                        "calls_attempted": 0,
                        "failure_reason": "PROVIDER_DISABLED_AFTER_FAILURE"
                        if settings.get("provider_blocked")
                        else "BUDGET_EXHAUSTED",
                    },
                }
            # Loading/warming is accounted separately from the answer and never calls a cloud embedder.
            factory.embedding.embed(["benchmark warmup"], "RETRIEVAL_QUERY")
            init_ms = (time.perf_counter() - started) * 1000
            llm = PinnedGemini(
                settings["model"],
                RequestBudget(settings["max_calls"], settings["answer_timeout"], journal),
                api_key=os.environ.get("GEMINI_API_KEY", ""),
                max_output_tokens=settings["max_output_tokens"],
                blocked=settings.get("provider_blocked", False),
            )
            answer_started = time.perf_counter()
            result = execute_variant(factory, corpus, case, variant, llm, settings["top_k"])
            return {
                "result": asdict(result),
                "telemetry": {
                    "init_elapsed_ms": init_ms,
                    "answer_elapsed_ms": (time.perf_counter() - answer_started) * 1000,
                    "calls_attempted": llm.budget.calls,
                    "model_versions": sorted(llm.model_versions),
                },
            }
    except Exception as exc:
        return {
            "error_code": error_code(exc),
            "telemetry": {
                "answer_elapsed_ms": (time.perf_counter() - answer_started) * 1000
                if answer_started
                else None,
                "calls_attempted": llm.budget.calls if llm else 0,
                "failure_reason": llm.failure_reason if llm else "FIXTURE_INITIALIZATION_FAILED",
                "failure_http_status": llm.failure_http_status if llm else None,
                "failure_type": llm.failure_type if llm else None,
                "model_versions": sorted(llm.model_versions) if llm else [],
                "partial_usage_observations": llm.usage if llm else [],
            },
        }
    finally:
        if llm:
            llm.close()


def main(argv=None):
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        data = json.loads(Path(args.input).read_text(encoding="utf-8"))
        case = EvaluationCase.model_validate(data["case"])
        result = run_worker(data["root"], case, data["variant"], data["settings"], data["journal"])
        write_json(args.output, result)
        return 0
    except Exception:
        write_json(
            args.output, {"error_code": "INVALID_SCHEMA", "telemetry": {"calls_attempted": 0}}
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
