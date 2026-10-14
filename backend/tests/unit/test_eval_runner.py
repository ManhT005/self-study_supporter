import json
import math
import platform
from pathlib import Path
from unittest.mock import Mock

import pytest

from evaluation.adapters.rag_only import RagOnlyAdapter
from evaluation.metrics import compute_summary
from evaluation.runner_v2 import run_comparison
from evaluation.schema import RunManifest, dataset_hash, load_dataset
from evaluation.scoring import paired_bootstrap, score_result
from evaluation.synthetic import SyntheticEnvironment
from study_supporter.application.contracts.agent import AgentResult
from study_supporter.application.contracts.context import AppContext
from study_supporter.application.contracts.learning import AnswerRequest
from study_supporter.application.contracts.retrieval import Evidence
from study_supporter.application.ports.llm import ChatResponse
from study_supporter.domain.provider_errors import ProviderUnavailable

DATASET = Path(__file__).resolve().parents[3] / "evaluation/datasets/v1/smoke.jsonl"


def environment_and_manifest():
    environment = SyntheticEnvironment(DATASET.parent / "fixtures/corpus.json", 3)
    manifest = RunManifest(
        git_sha="a" * 40,
        git_dirty=False,
        dataset_sha256=dataset_hash(DATASET),
        source_hash=environment.source_hash,
        execution_mode="offline",
        provider="synthetic",
        model_id="synthetic-echo-v1",
        prompt_hashes=environment.prompt_hashes(),
        embedding_id="none",
        index_hash=environment.source_hash,
        top_k=3,
        seed=42,
        python_version=platform.python_version(),
        platform=platform.platform(),
    )
    return environment, manifest


def test_all_cases_are_paired_repeated_and_scope_failures_are_explicit(monkeypatch):
    import socket

    def no_network(*args, **kwargs):
        raise AssertionError("Offline evaluation attempted a network call")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    env, manifest = environment_and_manifest()
    cases = load_dataset(DATASET)
    variants = {name: env.variant(name) for name in manifest.prompt_hashes}
    report = run_comparison(cases, variants, manifest, repetitions=2)
    assert len(report["records"]) == 60  # Entire dataset, without an implicit five-case sample.
    assert report["selection"]["case_ids"] == [c.case_id for c in cases]
    for name in variants:
        summary = report["summary"][name]
        assert summary["n_total"] == 30 and summary["n_valid"] == 26 and summary["n_failed"] == 4
        assert summary["metrics"]["expected_error_match"]["mean"] == 1.0
        assert summary["metrics"]["abstention_correctness"]["n_unknown"] == 4
        assert summary["metrics"]["tool_validation_rate"]["mean"] is None
    scopes = [r for r in report["records"] if r["category"] == "privacy"]
    assert all(r["error_code"] == "AUTH_SCOPE" and not r["citations"] for r in scopes)
    second = run_comparison(cases, variants, manifest, repetitions=2)
    keys = ("case_id", "variant", "repetition", "scores", "status", "retrieved_chunk_ids")
    assert [tuple(r[k] for k in keys) for r in report["records"]] == [
        tuple(r[k] for k in keys) for r in second["records"]
    ]


def test_provider_failure_remains_in_retrieval_denominator_and_is_sanitized():
    env, manifest = environment_and_manifest()
    cases = load_dataset(DATASET)[:2]

    def failure(case):
        raise ProviderUnavailable("api-key-SECRET hidden thought and raw PDF")

    report = run_comparison(
        cases, {"rag_only": failure, "legacy_react": env.variant("legacy_react")}, manifest
    )
    stats = report["summary"]["rag_only"]
    assert stats["n_failed"] == 2 and stats["n_valid"] == 0
    assert stats["metrics"]["recall_at_k"] == {
        "mean": 0.0,
        "n_eligible": 2,
        "n_observed": 2,
        "n_unknown": 0,
    }
    safe = json.dumps(report)
    assert "SECRET" not in safe and "hidden thought" not in safe and "raw PDF" not in safe
    assert "question" not in report["records"][0] and "answer" not in report["records"][0]
    assert all(
        r["error_code"] == "PROVIDER_ERROR" for r in report["records"] if r["variant"] == "rag_only"
    )


@pytest.mark.parametrize("limit", [1, 6, None])
def test_limit_is_explicit_and_does_not_change_pairing(limit):
    env, manifest = environment_and_manifest()
    report = run_comparison(
        load_dataset(DATASET),
        {n: env.variant(n) for n in manifest.prompt_hashes},
        manifest,
        limit=limit,
    )
    assert len(report["records"]) == 2 * (limit if limit is not None else 15)


def test_snapshot_mismatch_and_missing_prompt_hash_are_rejected_before_running():
    env, manifest = environment_and_manifest()
    variant = Mock()
    with pytest.raises(ValueError):
        run_comparison(load_dataset(DATASET), {"rag_only": variant}, manifest)
    with pytest.raises(ValueError):
        run_comparison(
            load_dataset(DATASET),
            {n: variant for n in manifest.prompt_hashes},
            manifest.model_copy(update={"source_hash": "sha256:" + "b" * 64}),
        )
    variant.assert_not_called()


def test_rag_adapter_generates_from_the_exact_single_retrieval_it_records():
    context = AppContext("A", ("doc-a",))
    retriever, llm = Mock(), Mock()
    first = Evidence("first", "doc-a", "one snapshot", "a.pdf", 1, 1)
    second = Evidence("second", "doc-a", "another snapshot", "a.pdf", 2, 2)
    retriever.execute.side_effect = [[first], [second]]
    llm.chat.return_value = ChatResponse(text="answer")
    result = RagOnlyAdapter(context, llm, retriever).execute(AnswerRequest(context, "question"))
    assert result.evidences == (first,) and retriever.execute.call_count == 1
    prompt = llm.chat.call_args.args[0][0]["content"]
    assert "one snapshot" in prompt and "another snapshot" not in prompt


def test_retrieval_metrics_count_first_relevant_rank_and_do_not_reward_duplicates():
    case = load_dataset(DATASET)[0]
    evidence = tuple(
        Evidence(chunk, "doc_a", "text", "a.pdf", 1, 1)
        for chunk in ("irrelevant", "math-definition", "math-definition")
    )
    scores = score_result(case, AgentResult("answer", evidence, "trace"), 3)
    assert scores["recall_at_k"] == 1 and scores["mrr_at_k"] == 0.5
    assert scores["ndcg_at_k"] == pytest.approx(1 / math.log2(3))


def test_missing_malformed_and_out_of_range_judge_scores_remain_in_denominators():
    scores = [
        {"faithfulness": 5, "relevance": 4},
        None,
        {"faithfulness": 0, "relevance": 0},
        {"faithfulness": 6, "relevance": 3},
        {"faithfulness": True, "relevance": 3},
        {"faithfulness": "5", "relevance": 3},
    ]
    items = [{"category": "factual", "rag_only": {"score": s}, "agent_rag": {}} for s in scores]
    summary = compute_summary(items)
    stats = summary["overall"]["rag_only"]
    assert stats["n_total"] == 6 and stats["n_valid"] == 1 and stats["n_failed"] == 5
    assert stats["avg_faithfulness"] == 5 and stats["avg_relevance"] == 4
    assert summary["overall"]["agent_rag"]["n_failed"] == 6
    assert summary["by_category"]["factual"]["rag_only"] == stats


def test_paired_bootstrap_resamples_cases_and_reports_missing_pairs():
    from evaluation.schema import EvaluationRecord

    records = []
    for case_id, delta in [("one", 0.5), ("two", 1.0)]:
        for repetition in range(3):
            for variant, value in [("base", 0.0), ("candidate", delta)]:
                records.append(
                    EvaluationRecord(
                        run_id="run",
                        case_id=case_id,
                        category="factual",
                        variant=variant,
                        repetition=repetition,
                        status="completed",
                        elapsed_ms=1,
                        scores={"metric": value},
                    )
                )
    records.append(
        EvaluationRecord(
            run_id="run",
            case_id="missing",
            category="factual",
            variant="base",
            repetition=0,
            status="error",
            elapsed_ms=1,
            scores={"metric": None},
        )
    )
    result = paired_bootstrap(records, "metric", "base", "candidate", seed=42)
    assert result["mean_delta"] == 0.75 and result["ci95"] == [0.5, 1.0]
    assert result["n_cases"] == 2 and result["n_pairs"] == 6 and result["n_unknown_pairs"] == 1
    assert result == paired_bootstrap(records, "metric", "base", "candidate", seed=42)
