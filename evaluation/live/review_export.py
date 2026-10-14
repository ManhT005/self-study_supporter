"""Private blinded review packets, with a separate confidential variant assignment map."""

import random
import secrets

from evaluation.live.fixtures import write_json


def export_review(output, cases, answers, *, seed=42, limit=24):
    output.mkdir(parents=True, exist_ok=False)
    by_id = {case.case_id: case for case in cases}
    groups = {}
    for case in cases:
        groups.setdefault(case.category, []).append(case.case_id)
    selected = []
    selection_rng = random.Random(seed)
    for values in groups.values():
        selection_rng.shuffle(values)
    while len(selected) < min(limit, len(cases)):
        for category in sorted(groups):
            if groups[category] and len(selected) < limit:
                selected.append(groups[category].pop(0))
        if not any(groups.values()):
            break
    packets, assignments = [], []
    rng = secrets.SystemRandom()
    for case_id in selected:
        case = by_id[case_id]
        candidates = [a for a in answers if a["case_id"] == case_id]
        rng.shuffle(candidates)
        for item in candidates:
            review_id = f"REVIEW-{len(packets) + 1:04d}"
            packets.append(
                {
                    "review_id": review_id,
                    "case_id": case_id,
                    "question": case.question,
                    "reference_facts": case.reference_facts,
                    "answer": item["answer"],
                    "evidence": item["evidence"],
                    "rubric": "faithfulness/completeness/citation_support/abstention; independent reviewer required",
                }
            )
            assignments.append({"review_id": review_id, "variant": item["variant"]})
    write_json(output / "packets.private.json", packets)
    write_json(output / "assignments.private.json", assignments)
    write_json(
        output / "coverage.private.json",
        {
            "selected_case_ids": selected,
            "n_packets": len(packets),
            "missing_answers": sum(
                2 - sum(a["case_id"] == cid for a in answers)
                for cid in selected
                if not by_id[cid].expected_error
            ),
            "expected_denial_cases": sum(bool(by_id[cid].expected_error) for cid in selected),
            "reviewed": False,
        },
    )
