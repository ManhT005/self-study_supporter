"""Deterministic structural metrics, deliberately separate from answer-quality judgment."""

import math
import random
from statistics import mean

from evaluation.schema import EvaluationCase, EvaluationRecord
from study_supporter.application.contracts.agent import AgentResult


def score_result(
    case: EvaluationCase,
    result: AgentResult | None,
    top_k: int,
    *,
    tool_capable: bool | None = None,
) -> dict:
    scores = {
        "citation_scope_validity": None,
        "tool_selection_allowed": None,
        "tool_validation_rate": None,
    }
    if case.relevant_chunk_ids:
        ranked = (
            list(result.retrieval_calls[0].chunk_ids[:top_k])
            if result and result.retrieval_calls
            else [e.chunk_id for e in result.evidences[:top_k]]
            if result
            else []
        )
        gold = set(case.relevant_chunk_ids)
        # Count a chunk only once even when an adapter accidentally repeats it.
        seen = set()
        gains = []
        for chunk in ranked:
            gains.append(int(chunk in gold and chunk not in seen))
            seen.add(chunk)
        first = next((i + 1 for i, gain in enumerate(gains) if gain), None)
        dcg = sum(gain / math.log2(i + 2) for i, gain in enumerate(gains))
        ideal = sum(1 / math.log2(i + 2) for i in range(min(len(gold), top_k)))
        hit = float(first is not None)
        recall = len(gold.intersection(ranked)) / len(gold)
        mrr = 1 / first if first else 0.0
        scores.update(
            hit_rate_at_k=hit,
            recall_at_k=recall,
            mrr_at_k=mrr,
            ndcg_at_k=dcg / ideal,
            initial_hit_rate_at_k=hit,
            initial_recall_at_k=recall,
            initial_mrr_at_k=mrr,
            initial_ndcg_at_k=dcg / ideal,
        )
        searched = (
            {chunk for call in result.retrieval_calls for chunk in call.chunk_ids}
            if result and result.retrieval_calls
            else {e.chunk_id for e in result.evidences}
            if result
            else set()
        )
        evidence_union = {e.chunk_id for e in result.evidences} if result else set()
        scores["any_search_hit"] = float(bool(gold.intersection(searched)))
        scores["union_evidence_recall"] = len(gold.intersection(evidence_union)) / len(gold)
    if case.required_tools and tool_capable is True:
        called = {call.name for call in result.tool_calls} if result else set()
        scores["required_tool_coverage"] = len(called.intersection(case.required_tools)) / len(
            set(case.required_tools)
        )
    if result:
        scores["citation_scope_validity"] = (
            mean(float(e.document_id in case.expected_doc_ids) for e in result.evidences)
            if result.evidences
            else None
        )
        if result.tool_calls:
            scores["tool_selection_allowed"] = float(
                all(call.name in case.allowed_tools for call in result.tool_calls)
            )
        # Name allowlists cannot establish schema validity or successful dispatch.
        scores["tool_validation_rate"] = (
            mean(float(call.validation == "validated") for call in result.tool_calls)
            if result.tool_calls and all(c.validation != "not_observed" for c in result.tool_calls)
            else None
        )
    if case.must_abstain:
        scores["abstention_correctness"] = (
            float(result.abstained) if result and result.abstained is not None else None
        )
    return scores


def record_outcome(record: EvaluationRecord) -> str:
    if record.expected_error:
        return (
            "expected_denied"
            if record.status == "error" and record.error_code == record.expected_error
            else "unexpected_failed"
        )
    return {"completed": "completed", "error": "unexpected_failed", "incomplete": "incomplete"}[
        record.status
    ]


def summarize(records: list[EvaluationRecord]) -> dict:
    summary = {}
    metric_names = sorted({key for record in records for key in record.scores})
    for variant in sorted({r.variant for r in records}):
        items = [r for r in records if r.variant == variant]
        elapsed = sorted(r.elapsed_ms for r in items)
        summary[variant] = {
            "n_total": len(items),
            "n_valid": sum(r.status == "completed" for r in items),
            "n_failed": sum(r.status == "error" for r in items),
            "n_completed": sum(record_outcome(r) == "completed" for r in items),
            "n_expected_denied": sum(record_outcome(r) == "expected_denied" for r in items),
            "n_unexpected_failed": sum(record_outcome(r) == "unexpected_failed" for r in items),
            "n_incomplete": sum(record_outcome(r) == "incomplete" for r in items),
            "latency_ms": {
                "p50": elapsed[math.ceil(len(elapsed) * 0.5) - 1],
                "p95": elapsed[math.ceil(len(elapsed) * 0.95) - 1],
            },
            "metrics": {},
        }
        for name in metric_names:
            eligible = [r.scores[name] for r in items if name in r.scores]
            observed = [value for value in eligible if value is not None]
            summary[variant]["metrics"][name] = {
                "mean": mean(observed) if observed else None,
                "n_eligible": len(eligible),
                "n_observed": len(observed),
                "n_unknown": len(eligible) - len(observed),
            }
    return summary


def paired_bootstrap(
    records: list[EvaluationRecord],
    metric: str,
    baseline: str,
    candidate: str,
    *,
    seed: int,
    samples: int = 1000,
) -> dict:
    if samples < 1:
        raise ValueError("Bootstrap samples must be positive")
    pairs = {}
    for record in records:
        if record.variant in {baseline, candidate}:
            pairs.setdefault((record.case_id, record.repetition), {})[record.variant] = (
                record.scores.get(metric)
            )
    by_case = {}
    n_pairs = 0
    for (case_id, _), values in pairs.items():
        base, other = values.get(baseline), values.get(candidate)
        if base is not None and other is not None:
            by_case.setdefault(case_id, []).append(other - base)
            n_pairs += 1
    # Repetitions of a case are correlated; resample cases after averaging their paired deltas.
    deltas = [mean(values) for values in by_case.values()]
    rng = random.Random(seed)
    estimates = (
        sorted(mean(rng.choices(deltas, k=len(deltas))) for _ in range(samples)) if deltas else []
    )
    return {
        "mean_delta": mean(deltas) if deltas else None,
        "ci95": [estimates[int(0.025 * (samples - 1))], estimates[int(0.975 * (samples - 1))]]
        if estimates
        else None,
        "n_cases": len(deltas),
        "n_pairs": n_pairs,
        "n_total_pairs": len(pairs),
        "n_unknown_pairs": len(pairs) - n_pairs,
        "bootstrap_samples": samples,
    }


def paired_summary(records: list[EvaluationRecord], variants, *, seed: int) -> dict:
    baseline = "rag_only" if "rag_only" in variants else sorted(variants)[0]
    metrics = sorted({key for record in records for key in record.scores})
    return {
        "baseline": baseline,
        "candidates": {
            name: {
                metric: paired_bootstrap(records, metric, baseline, name, seed=seed)
                for metric in metrics
            }
            for name in variants
            if name != baseline
        },
    }
