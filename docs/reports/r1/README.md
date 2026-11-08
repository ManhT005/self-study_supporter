# R1 execution and evidence

WP-01 establishes the approved functional baseline, trace ownership and executable timings. It does not accept a release. Start with `docs/srs/baseline.json`, `docs/decisions/R1_REGISTER.md`, the private approved implementation plan and `release-evidence.json`.

## Reproduce WP-01

Use Python 3.11 or 3.12, from the repository root:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements/dev.txt -r requirements/api.txt
python -m pip install --no-build-isolation --no-deps -e ./backend
python -m scripts.verify_r1_baseline
python -m scripts.profile_r1_baseline --repetitions 5
python -m pytest -q
python -m pytest apps/api/tests -q
python scripts/check_import_boundaries.py
python -m scripts.export_http_contract --check
```

The unchanged API contract is `docs/api/runtime-openapi.json`; its hash at the base SHA is recorded in the freeze manifest. No migration, feature rollout, API DTO/status change, model selection or retrieval tuning occurs in WP-01. Reverting instrumentation or omitting a timing capture scope disables measurements without touching persisted learning state.

## Metrics and their limits

The profiler creates `data/r1/baseline-profile.json` with exact HEAD, dirty-tree marker, timestamp, Python/package versions, fixture hash, phase, raw timing records, p50 and p95 by phase/operation, and explicit pending reviewer. Never attach a dirty-tree report as immutable candidate evidence. The CI artifact regenerates it on the checked-out branch SHA.

| Operation | Boundary measured | Interpretation |
| --- | --- | --- |
| `open_document` | ApplicationFactory document/session construction | Includes source load and service construction |
| `load_all_chunks` | VectorStore read and Chunk reconstruction | Synthetic CI uses an in-memory Chroma-shaped double |
| `bm25_build` | BM25Index construction and tokenization | Observe existing lifecycle; no cache/tokenizer change |
| `embedding` | SharedEmbedding model lock/load/embed, or explicit synthetic provider | Real cold model and warm model must be measured separately |
| `retrieval` | ScopedHybridRetriever authorization-ready document loop and hybrid query | Inclusive of index creation and query embedding |
| `provider_generation` | One legacy ReAct LLM call | Includes adapter fallback/retry time; not per-provider token/cost attribution |
| `tool_round` | One selected legacy tool execution | No tool name, arguments or observation content recorded |
| `ingestion`, `pdf_parse` | Existing ingestion facade and parser | Actual parser/chunking; synthetic embeddings/storage in CI |

Times use a monotonic clock in milliseconds. Percentiles use nearest rank, include errors, and carry sample and error counts. Spans are inclusive and nested: do not sum them. Trace/span IDs are generated internally; no user-supplied correlation label, owner ID, filename, prompt, output, note, raw exception, credential or request body is accepted. Capture scopes restore on exceptions and remain separate across concurrent async requests. A failing diagnostics sink cannot replace application output/errors. Callers must use a bounded sink; the CI harness caps repetitions at 100.

`cold_session` creates a new learning session before its first answer; `warm_session` reuses that session. Neither is a cold-model/process claim. SQL is disposable SQLite; vector storage and model calls are doubles. Synthetic timings prove instrumentation/contract behavior, not BGE-M3, provider, Chroma, production capacity or AI quality.

## Opt-in real measurement

Use an isolated operator-approved environment, approved PDF, pinned existing model/provider settings, a declared call/token budget, and the existing live evaluation safety controls in `evaluation/live/README.md`. Do not run live providers from PR CI or silently reuse learner data. Wrap the real factory calls in the same capture scope; do not place PDF text in an artifact:

```python
from study_supporter.application.telemetry import capture_timings
records = []
with capture_timings(lambda event: records.append(event.to_dict())):
    session = factory.open_document(authenticated_context, owned_ready_document_id)
    result = session.answer(approved_question)
```

The operator supplies these existing, authenticated application objects. Record model ID/version, dataset/index manifest hashes, hardware, cold/warm definition, budget and actual usage, exact clean SHA, environment and reviewer in a separate evidence record. Per-adapter retry/token accounting, durable telemetry export and request/owner correlation belong to WP-19. No approved real-PDF/provider run was executed by this branch.

## Gates and next step

G0 is HOLD until WP-02 write-deny/adversarial evidence, exact candidate hosted CI, real baseline profile and independent Tech Lead/QA review are attached. G1–G4/G6/G7 remain HOLD; optional G5 is DEFER. The private UAT register contains all 26 NOT RUN scenarios; their IDs are mapped in the public registry. `requirements.json` freezes planned ownership only; implementation evidence must be recorded separately by test path, SHA, fixture, result and reviewer. Never change a frozen source requirement to make a test pass.

WP-02 enforcement, test mapping and remaining evidence are in [WP-02 validation](WP-02_VALIDATION.md). Start WP-03 after G0 acceptance and the Security/BE review of DEC-03. The PO-approved DEC-08 governs WP-04. WP-09 source provenance and independent annotation preparation can proceed in parallel.

## Private source control

Full SRS and implementation-plan text remain private pending explicit permission to publish them to this public repository. `docs/srs/baseline.json` records original and transcription checksums; `requirements.json` exposes only stable IDs, categories and package ownership. Run the verifier with `--source /authorized/path/SSS-SRS-001_v1.0.md` to validate the private transcription as well. The verifier also accepts the original approved `.docx` and checks its hash and requirement IDs. G0 cannot be accepted merely because the public ID register passes.
