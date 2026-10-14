"""Fail closed on missing consensus, unsupported source references and split leakage."""

import argparse
import json
from collections import Counter
from pathlib import Path

from evaluation.datasets.v2.schema_extensions import BenchmarkCase, CorpusSnapshot

CATEGORIES = {"factual", "multi_hop", "synonyms", "unanswerable", "quiz", "personalized", "privacy"}


def validate_cases(cases, corpus: CorpusSnapshot, *, acceptance=False):
    if not cases or len({c.case_id for c in cases}) != len(cases):
        raise ValueError("Missing or duplicate benchmark cases")
    chunks = {(c.document, c.chunk_id): c for c in corpus.chunks}
    splits = {}
    for case in cases:
        if case.source_hash != corpus.source_hash or case.user_fixture not in corpus.users:
            raise ValueError("Unknown account or source snapshot mismatch")
        for alias in case.document_ids:
            if alias not in corpus.documents:
                raise ValueError("Unknown source document")
            doc = corpus.documents[alias]
            if doc.user_fixture != case.user_fixture and case.expected_error != "AUTH_SCOPE":
                raise ValueError("Foreign document must be an explicit denial probe")
            for key in (
                "doc:" + alias,
                "topic:" + doc.topic_group,
                "content:" + doc.content_family,
                "pdf:" + doc.pdf_sha256,
            ):
                if key in splits and splits[key] != case.split:
                    raise ValueError("Document/topic/content leakage across splits")
                splits[key] = case.split
        if case.requires_history and case.history_fixture not in corpus.history_fixtures:
            raise ValueError("Missing isolated history fixture")
        if (
            case.requires_history
            and corpus.history_fixtures[case.history_fixture].get("user_fixture")
            != case.user_fixture
        ):
            raise ValueError("History fixture belongs to a different account")
        if any(
            not any((doc, chunk) in chunks for doc in case.expected_doc_ids)
            for chunk in case.relevant_chunk_ids
        ):
            raise ValueError("Gold chunk does not exist in expected source")
        supported = set()
        for support in case.fact_support:
            chunk = chunks.get((support.document, support.chunk_id))
            if (
                chunk is None
                or support.document not in case.expected_doc_ids
                or support.chunk_id not in case.relevant_chunk_ids
                or not chunk.page_start <= support.page_start <= support.page_end <= chunk.page_end
                or " ".join(support.quote.split()) not in " ".join(chunk.text.split())
                or support.fact_index >= len(case.reference_facts)
            ):
                raise ValueError("Invalid fact support chunk/page/quote")
            supported.add(support.fact_index)
        if supported != set(range(len(case.reference_facts))):
            raise ValueError("Every reference fact requires attributable source support")
    if acceptance and (
        len(cases) < 100
        or {c.category for c in cases} != CATEGORIES
        or {c.split for c in cases} != {"development", "validation", "holdout"}
    ):
        raise ValueError("G1 requires >=100 cases, seven strata and three disjoint splits")
    if (
        acceptance
        and len({corpus.documents[d].topic_group for c in cases for d in c.document_ids}) < 5
    ):
        raise ValueError("G1 requires at least five source topics")
    return {
        "n_cases": len(cases),
        "by_category": dict(Counter(c.category for c in cases)),
        "by_split": dict(Counter(c.split for c in cases)),
        "adjudicated": sum(c.annotations[0].label != c.annotations[1].label for c in cases),
        "g1_accepted": False,
        "structurally_ready_for_review": acceptance,
    }


def load_labels(path, corpus, *, acceptance=False):
    cases = tuple(
        BenchmarkCase.model_validate_json(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    validate_cases(cases, corpus, acceptance=acceptance)
    return cases


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--acceptance", action="store_true")
    args = parser.parse_args(argv)
    try:
        corpus = CorpusSnapshot.model_validate_json(Path(args.corpus).read_text(encoding="utf-8"))
        cases = load_labels(args.dataset, corpus, acceptance=args.acceptance)
        print(json.dumps(validate_cases(cases, corpus, acceptance=args.acceptance)))
        return 0
    except (ValueError, OSError):
        print(json.dumps({"valid": False, "error": "INVALID_BENCHMARK_LABELS"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
