# Phase 0 baseline evidence

Recorded 2026-10-13. Owner: repository maintainer (ManhT005); implementation: Codex.

- Remote checked with `git fetch origin feature/docker-local-foundation main`.
- Foundation HEAD: `0cf9524e52455e3b75d2b8cd781ddd4300b1e085`.
- Main baseline: `cb67b95d890fc90eff98df1960d68384e48c99b7`.
- Host: Windows, PowerShell, Python 3.12.7 (existing Anaconda environment).
- Docker Engine: 29.1.3, Docker Desktop Linux engine. Desktop UI version not recorded.
- Worktree was clean on `manht`; switched to the existing remote foundation branch.
- No cloud credentials used for tests. Existing `.env` and local data excluded from evidence.

## Executed baseline

| Command | Actual result |
| --- | --- |
| `python -m pytest -q` | Collection failed: `eval_test.py` and `scripts/test_setup.py` import unavailable `google.genai`; these are online scripts, not offline tests. |
| `python -m pytest tests -q` | 17 passed, 2 protobuf deprecation warnings, 1.67 seconds. |
| `docker info --format '{{.ServerVersion}}'` | 29.1.3; requires Docker pipe access outside the workspace sandbox. |

## Current call graph and hazards

`main.py -> ui/router.py -> auth/sidebar/chat/quiz/graph`.
Sidebar composes PDF parsing, embedding, Chroma, BM25, providers, ReAct and SQL repositories.
Auth/document/progress modules call `create_all()` on import. Documents use per-document
Chroma collections; notes use a shared collection filtered by user ID. SQL users/documents
use integer user IDs; quiz attempts preserve historical string user IDs.

Static hazards requiring regression tests: incomplete logout reset; document updates
without ownership checks; quiz parser defaults to A; percentile on empty distances;
temporary PDF not cleaned after failure; interpolated PostgreSQL password in Compose.
Existing graph cycle tests and provider fallback tests pass. ReAct tests are absent.

## Synthetic fixtures and expected behavior

Generate PDFs in temporary directories with PyMuPDF: one text page, two text pages,
one blank page and corrupt bytes. Use deterministic fake two-dimensional embeddings.
Quiz fixtures: four ordered options, exactly one explicit answer marker; missing,
duplicate or ambiguous markers must fail closed. Users A/B use throwaway accounts
in isolated test databases. Never copy real uploaded PDFs, keys or account records.

Docker build, functional persistence, restore, Ollama and browser E2E are pending
at baseline. Later results belong in `docs/reports/p0-acceptance.md`.
