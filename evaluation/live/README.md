# Opt-in real-pipeline evaluation

This tooling reuses `ApplicationFactory`, owned SQL access, BGE-M3/1024D,
`ScopedHybridRetriever`/Dense+BM25+RRF, `RagOnlyAdapter` and the unchanged full
four-tool `LegacyReActAdapter`. It introduces no application endpoint, orchestration
flag, provider-selection change, schema migration to retained data or frontend change.
Imports and mandatory tests never call a provider or download a model.

Prepare an approved PDF in a **new** private snapshot directory. Preparation applies
the existing migration to a disposable SQLite database, runs the production ingestion
pipeline once and clones the frozen vectors for a second account's scope probe.
It makes zero Gemini calls. Set local model cache/revision explicitly; record the
same BGE-M3 artifact and lockfiles. The second account/index is an ownership fixture,
not a second independent quality source. `corpus.json` contains private text/hashes.

```powershell
python -m evaluation.live.prepare --pdf "data/cnn-nhan dang bien so.pdf" --snapshot data/eval_private/v2/snapshot --permission-reference user-approved-2026-10-14 --embedding-revision <BGE-M3-cache-revision>
```

Use a provisioned runtime with `chromadb`, `sentence-transformers` and the pinned
runtime dependencies; the ordinary development venv does not necessarily include
them. An existing runtime Docker image with the repository mounted read-only and
`PYTHONPATH=/app/backend/src` can run current code. Mount only the dedicated eval
directory writable and the existing Hugging Face cache read-only/offline. Do not
mount the application database/Chroma volumes writable or run `down -v`.

Each callback verifies the immutable payload/corpus hash, clones SQL/Chroma to a
distinct temporary directory and starts a separate subprocess. SQL ownership is
checked before vectors/model access; process exit releases Chroma before cleanup.
Notes/progress/tool writes affect only the clone; the source is verified again
afterwards. Explicit progress fixtures are seeded per invocation; nonempty chat
history is rejected because the current production AgentPort does not consume it.
Do not claim chat-memory evaluation support or QA-09 closure from this limitation.

Gemini is pinned explicitly (default `gemini-3.1-flash-lite`), with no `auto` selection,
fallback or transport retry. Every model attempt reserves a durable budget slot
before transport. The default smoke allows at most three cases, one repetition,
six total model attempts, 768 output tokens/call, a 24,000-character input cap,
90-second answer deadline and 180-second subprocess deadline. Quota/auth/provider
failures disable further requests. Missing response usage/version remains unknown;
cost is never invented. The original ReAct maximum five iterations remains unchanged,
including nested quiz calls subject to the same global request budget.
Flash-Lite 3.1 uses explicit `thinking_level=minimal`; the retained 2.5 setting uses
`thinking_budget=0`. Both omit thoughts. The exact setting is recorded in the live
sidecar. A model listing is not proof of generation availability: the initial 2.5
smoke returned HTTP 404, so a separate run explicitly pins 3.1 instead of fallback.

```powershell
# Supply GEMINI_API_KEY securely in the environment; never print or commit it.
python -m evaluation.live.cli --mode online --purpose smoke --dataset data/eval_private/v2/smoke.jsonl --snapshot data/eval_private/v2/snapshot --work-root data/eval_private/v2/work --output-dir data/eval_private/v2/runs --model gemini-3.1-flash-lite --budget 6
```

The paired runner/metric schema 2 are reused. Initial ranking and union success
remain separate; actual model-chosen tool top-k values are recorded rather than
silently clamped or changing the legacy prompt. Parent orchestration time and
worker initialization/warmup are separate from measured answer latency. Model
responses' observed versions are recorded and drift fails the engineering check;
runner seed controls pair order/bootstrap, not provider sampling. A model alias
without a returned version is explicitly not an immutable provider artifact digest.

All output stays in the private snapshot sandbox. `results.json` is sanitized;
`answers.private.json`, blinded `review/packets.private.json` and the separate
assignment map contain approved actual text and must never be uploaded as shared
CI artifacts. Restrict access, keep reviewers blind to the map, record at least two
independent reviewers/adjudication and apply the team's retention policy. No hidden
scratchpad or raw SDK exception is serialized. The live engineering check is
separate from `evaluation/gates.py`'s synthetic golden and cannot sign G1/G2/G3.

`--purpose benchmark` requires the independent-annotation validator's structural
G1 prerequisites and an external `--approval-record` declaring G1/G2 approvals.
Holdout execution stays locked pending final review/unlock policy. The public
repository contains no fabricated ≥100-case dataset or human approvals. One
approved source/three unreviewed engineering cases can demonstrate a live dry run,
not Phase 1 quality acceptance; LangChain/LangGraph remain gated.

Gemini configuration references: [model](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite),
[thinking](https://ai.google.dev/gemini-api/docs/gemini-3),
[pricing](https://ai.google.dev/gemini-api/docs/pricing),
[Python SDK](https://github.com/googleapis/python-genai).
