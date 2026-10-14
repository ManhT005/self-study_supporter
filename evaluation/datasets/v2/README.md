# Approved real-model benchmark data

Public Git contains validators and annotation instructions. Actual PDFs, indexed
chunk text, reference facts, annotation votes and review packets belong under
ignored `data/eval_private/v2/`. Never copy the smoke's labels as benchmark evidence.

`CorpusSnapshot` freezes actual document/user IDs, source permissions and PDF hashes,
topic/content families, chunk pages/text, embedding fingerprints and database/model
revision. `BenchmarkCase` extends the structural schema only for fields required by
independent annotation and provenance; metric schema remains version 2.

Each accepted case needs two distinct independently submitted labels. Disagreements
require a third adjudicator and explicit resolved gold. Every reference fact needs
an existing owned relevant chunk, valid page range and exact source quote. Quote
membership proves attribution, not semantic entailment; reviewers must judge support.
The validator rejects missing/duplicate cases, unknown/foreign fixture identities,
source hash mismatch and shared document/topic/content/PDF across splits.

```powershell
.venv/Scripts/python -m evaluation.datasets.v2.scripts.validate_labels --dataset data/eval_private/v2/labels.jsonl --corpus data/eval_private/v2/snapshot/corpus.json
# Structural G1 readiness; independent signoff is still required:
.venv/Scripts/python -m evaluation.datasets.v2.scripts.validate_labels --dataset data/eval_private/v2/labels.jsonl --corpus data/eval_private/v2/snapshot/corpus.json --acceptance
```

Acceptance validation requires at least 100 unique cases, all seven categories and
development/validation/holdout splits with disjoint document/topic/content groups.
Target 120 cases and 70/15/15 grouped splits across 8–12 approved sources/≥5 topics.
Human approvals are not fabricated by a passing validator. A single user-approved
PDF can support an engineering smoke; it cannot pass the planned split/annotation gate.
