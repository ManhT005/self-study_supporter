# Synthetic structural golden revision 1

`v1.json` pins metric schema **2**, the exact labeled smoke/corpus/prompt hashes,
synthetic provider, lexical index, top-k 3, seed 42, declared tool capabilities,
15 case IDs and three repetitions. Expected values are structural fixture outcomes,
not model-quality, hardware-latency or real-provider thresholds. Any change to labels,
prompts or metric semantics requires an explicit reviewed golden revision.

The gate requires all 90 unique case/variant/repetition records: 78 completed,
12 expected `AUTH_SCOPE` denials and zero unexpected failures/incomplete outcomes.
It checks candidate IDs/pages against the approved corpus, denial records without
evidence/tool activity, preserved unknown validation/refusal/usage, recomputed
per-record scores/summary/paired statistics, and hand-written semantic examples for
partial multi-hop recall, duplicate suppression, MRR, empty gold, retries and
required/allowed/no-tool distinctions. No final context or citation support is guessed.

```powershell
.venv/Scripts/python -m evaluation.runner_v2 --repetitions 3 --report-path-file data/evaluations/report-path.txt
.venv/Scripts/python -m evaluation.gates --report-path-file data/evaluations/report-path.txt
# Direct file input is also supported:
.venv/Scripts/python -m evaluation.gates --report data/evaluations/<run_id>/results.json
```

Exit 0 means structural pass, 1 means a violated golden expectation, and 2 means
unreadable/malformed report or policy input. Diagnostics contain failure codes and
approved fixture IDs, never raw parser exceptions or report payloads. CI uploads its
offline artifact with `if: always()` so failures are reviewable. Unit tests corrupt
metrics, membership, hashes, denials, unknown telemetry, provenance and paired stats;
they also verify the CLI's actual nonzero exit codes.

No-side-effect guarantees for authorization are separately exercised through real
SQL ownership and HTTP/application paths with deterministic vector/model doubles.
A quiet denial record alone cannot prove absence of external writes. Live fixture
isolation, real-model prompt injection, independent ≥100-case annotations and
human citation/answer review remain separate Phase 1 acceptance work.
