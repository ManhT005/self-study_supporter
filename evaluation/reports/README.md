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
