"""Separate engineering checks for live reports; never synthetic golden or Phase 1 signoff."""

from evaluation.schema import EvaluationRecord, RunManifest


def check_live_report(report, cases, corpus):
    failures = []
    manifest = RunManifest.model_validate(report["manifest"])
    records = [EvaluationRecord.model_validate(r) for r in report["records"]]
    if (
        manifest.execution_mode != "online"
        or manifest.source_hash != corpus.source_hash
        or manifest.index_hash != corpus.index_hash
    ):
        failures.append("FROZEN_MANIFEST_MISMATCH")
    budget = report["live"]["budget"]
    if budget["calls_attempted"] > budget["max_calls"] or budget["transport_attempts"] != 1:
        failures.append("REQUEST_BUDGET_VIOLATION")
    by_id = {case.case_id: case for case in cases}
    known = {(c.document, c.chunk_id): c for c in corpus.chunks}
    telemetry = report["live"]["samples"]
    if len(telemetry) != len(records):
        failures.append("MISSING_SAMPLE_TELEMETRY")
    versions = {version for sample in telemetry for version in sample.get("model_versions", [])}
    if len(versions) > 1:
        failures.append("PROVIDER_MODEL_VERSION_DRIFT")
    for row in records:
        case = by_id[row.case_id]
        if case.expected_error and (row.status != "error" or row.error_code != case.expected_error):
            failures.append("EXPECTED_DENIAL_MISSING")
        if not case.expected_error and row.status != "completed":
            failures.append("LIVE_SAMPLE_FAILED")
        for evidence in row.retrieved_evidence:
            ref = known.get((evidence.document_id, evidence.chunk_id))
            if (
                not ref
                or evidence.document_id not in case.expected_doc_ids
                or (evidence.page_start, evidence.page_end) != (ref.page_start, ref.page_end)
            ):
                failures.append("UNAUTHORIZED_OR_UNKNOWN_EVIDENCE")
        if row.supporting_citations is not None:
            failures.append("UNREVIEWED_CITATION_SUPPORT")
    return sorted(set(failures))
