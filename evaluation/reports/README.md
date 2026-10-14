# Generated evaluation reports

Raw reports belong under ignored `data/evaluations/<run_id>/results.json`. The v2
report includes the manifest, selected IDs, repetition count, individual statuses,
structured error codes, first-seen evidence IDs, ordered retrieval calls, safe tool
names, nullable usage, explicit metric denominators and case-level paired bootstrap
intervals. It excludes question/answer/PDF text, filenames, tool arguments, raw
exceptions and scratchpads. Trace and query/answer hashes support correlation.

Publish reviewed summaries in `docs/reports/ai-eval/`, identifying execution mode,
Git SHA/dirty status, dataset/source/prompt hashes, model/provider/index, settings,
counts, failures, missing telemetry and open acceptance gates. A synthetic report
verifies framework behavior and cannot establish model quality or production latency.
Live callbacks must also sanitize manifest identifiers and supply an authorized,
frozen document/index snapshot; the harness cannot independently verify a caller's
declared provider, checkpoint isolation or model settings.

Metric schema version 2 corrects standard Recall@k and adds an explicit hit rate,
initial ranking vs any-search/union coverage, required-tool coverage and exclusive
outcome counts. Earlier reports without `metric_schema_version` retain version 1's
hit-rate interpretation of `recall_at_k`; do not relabel their numbers as standard
recall. V2 telemetry separates candidate `retrieved_evidence` from unmeasured
`supporting_citations=null`, while retaining `citations` as a candidate alias.
Use `n_unexpected_failed` for unexpected failures, not compatibility `n_failed`.

The synthetic golden gate independently checks IDs/pages against the frozen corpus,
recomputes per-record scores, summary and paired statistics, and rejects fabricated
supporting-citation labels. A structurally valid reference is not proof of claim
support; no human/judge citation precision is inferred from this gate.
