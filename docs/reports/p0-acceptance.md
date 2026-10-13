# Phase 0 acceptance evidence — 2026-10-13

Status: implementation delivered locally; final acceptance still requires remote CI,
branch protection/review and human browser smoke. No v1 tag or production deployment.

## Environment and baseline

Windows/PowerShell; host Python 3.12.7 in a fresh `.venv`; Docker Engine 29.1.3,
Linux CPU image based on Python 3.11-slim-bookworm. Remote foundation baseline
`0cf9524e52455e3b75d2b8cd781ddd4300b1e085` was fetched and checked before work.
Original checkout was clean on `manht`; implementation continues on
`feature/docker-local-foundation`. Existing `.env` and retained local data were not migrated.

## Executed checks

| Check | Actual result |
| --- | --- |
| `python -m pytest -q` in `.venv` | 91 passed, 12 dependency deprecation warnings, 16.62 seconds. Root collection now excludes opt-in online scripts. |
| Same suite in Linux/Python 3.11.17 CPU image | 91 passed, 8 warnings, 16.38 seconds. Warnings include legacy/PyMuPDF deprecations and test-cache permissions in the non-root container; test data/volume writes work. |
| Ruff check / format check | Pass on all configured P0 new/touched files. Untouched legacy lint is outside this baseline. |
| `python scripts/check_import_boundaries.py` | Pass; negative tests detect framework, SDK, legacy and reversed layer imports. |
| Editable install, sdist and wheel build | Pass. Docker imports installed core from `/usr/local/lib/python3.11/site-packages`; isolated host import also passes. |
| Fresh PostgreSQL upgrade / `alembic check` | Pass; no schema drift against ORM models. |
| `pytest backend/tests/integration -q` | 2 passed, 6 datetime deprecation warnings, 1.16 seconds, against disposable PostgreSQL 16 at loopback 55432. |
| Existing unversioned schema | Refused without modifying existing fixture rows; no automatic stamp. |
| Repeated upgrade with sample rows | Pass; rows preserved. Populated downgrade refused; empty downgrade/upgrade roundtrip passes. |
| Compose config and clean CPU build | Pass, including final PostHog-compatible dependency rebuild; PostgreSQL and app healthy; migration exits 0 before app startup. |
| Liveness and runtime identity | `/_stcore/health` returns 200; app UID is 10001. Health alone is not functional readiness. |
| Synthetic Docker service smoke | Pass: register/login, real PDF parsing, chunk provenance, fake 1024D vectors, Chroma query, mocked quiz, persisted progress and user/notes isolation. |
| App/DB restart | Pass; synthetic SQL, Chroma, quiz and notes still retrievable. |
| Compose `down` / `up` without deleting volumes | Pass on final image; real-model documents/vectors/progress and synthetic fixtures retained. |
| Synchronized backup and isolated restore | Pass; `data/backups/p0-foundation-20261013` restored into fresh `p0-restore-check`; smoke verifies SQL/Chroma/notes/progress. Backup is ignored private data. |
| Final backup including real-model records | Pass; `data/backups/p0-final-20261013` restored into fresh `p0-final-restore`; both synthetic smoke and real-model SQL/Chroma/progress checks pass. |
| Streamlit AppTest | Pass: UI registration → logout → B login in the same session; unknown account-scoped keys and A's quiz/vector state cleared. This is not a real browser. |
| Host Ollama `/api/tags` | Pass; qwen3:1.7b, qwen3:4b and qwen2.5:1.5b available. |
| Host Ollama chat / real quiz | Pass using qwen3:1.7b; one valid four-option quiz parsed successfully. No cloud calls. |
| Image/git secret exclusions | `.env` and `.env.docker` absent from image; no commits for those paths in fetched history. No claim of a comprehensive historical secret audit. |
| Workflow / OpenAPI YAML / mock DTO | YAML parsed; mock response constructs the core Evidence DTO. HTTP contract is a P1 proposal, not a deployed API. |

One repeated host test run encountered Windows `WinError 10106` initializing
`_overlapped` in an Alembic subprocess (85 pass, 1 fail). Re-running the unchanged
suite passed all 87 tests at that point, then all 91 after adding architecture guard cases.
Do not hide persistent platform errors by skipping migration tests.

## Changes and compatibility

Pure RRF preserves duplicate contributions and dense-first stable tie order; legacy
imports forward to the installed package. Retrieval contracts validate top_k and
ownership before retrieval; the core has no runtime framework dependencies.

Logout/login clears all state except validated theme. Document updates and quiz
document associations check user ownership. Quiz rejects missing/ambiguous markers,
extra options and invalid structured answer indexes. Empty/scan/corrupt uploads fail
closed; tempfile cleanup runs on failure. Provider authentication does not silently
fall back; fallback messages avoid raw provider bodies. Citation chips use actual
retrieved evidence, and raw thought logs are removed from the UI.

New uploads store their original filename as source metadata; existing stored
vectors/IDs/collections are not rewritten or reindexed. BGE-M3/1024D remains the
baseline. Quiz user IDs retain the historical string schema; a conversion/backfill
is deliberately deferred to a reviewed migration. No existing Supabase schema was adopted.

Smoke exposed Chroma 0.5.23 incompatibility with newer PostHog capture signatures.
Runtime pins PostHog 3.7.0 and disables anonymized telemetry. Direct dependencies and
Linux/Python 3.11 CPU transitive dependencies are locked; dev lock supports Python 3.11–3.12.

## Final runtime checks

The final dependency image built successfully and Chroma initialization reports
PostHog 3.7.0 / anonymized telemetry false without capture errors. BGE-M3 downloaded
into `hf_cache`, loaded and produced 1024D embeddings. `python -m scripts.model_smoke`
passed real PDF parsing/semantic chunking, BGE indexing, hybrid retrieval, Ollama ReAct
with retrieved evidence, real validated quiz and SQL progress in a synthetic account.
This is service execution, not browser E2E or a retrieval quality benchmark.

Observed model metadata:

- BGE-M3 revision: `5617a9f61b028005a4858fdac845db406aefb181`.
- Host Ollama qwen3:1.7b digest: `8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7`.
- Embedding image uses CPU Torch 2.5.1+cpu; no weights baked into image layers.

Optional container Ollama profile has not been provisioned; host Ollama is verified.
Disposable integration/restore containers were stopped after verification without
deleting retained restore volumes. The main dev app/DB remain running at localhost:8501.

## Remaining acceptance work

- Execute the committed workflow on GitHub and review all three jobs; local commits
  do not establish remote CI green.
- Configure/verify main branch protection and reviewer requirements.
- A human must run register/login → upload → chat → quiz → logout/login in a real
  browser, including A/B isolation. AppTest and service smoke cover subsets.
- Any existing populated DB adoption needs its own synchronized backup, schema diff,
  restore evidence and maintainer approval. This work uses fresh disposable databases.

## Implementation commits

| Commit | Part |
| --- | --- |
| `f826685` | Baseline and architecture decisions |
| `1aca19f` | Docker/config/dependency locks/backup |
| `26460e2` | Python package, RRF and architecture gate |
| `2709ba4` | Correctness, ownership and session regression guards |
| `6af2613` | Explicit Alembic lifecycle and PostgreSQL tests |
| `42438f3` | Runtime embedding validation and telemetry compatibility |
| `d008e4c` | CI, smoke scripts, developer docs and frontend handoff |
| `b720141` | Reject fifth/extra quiz options |
| `6fd77be` | Reject standard-library network/DB imports in pure core |
