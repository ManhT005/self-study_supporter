# UI migration validation — 2026-10-14

Branch: `feature/ui-learning-workspace`. This record distinguishes executable
UI/API work from production cutover gates. No existing DB, Chroma layout, embedding
dimension, production volume or user data was reset or migrated during this work.

## Executed checks

| Check | Result |
| --- | --- |
| Original Python baseline | 122 passed |
| Core + HTTP API regression | 128 passed |
| Ruff lint / formatting / import boundaries | Passed |
| Runtime OpenAPI snapshot consistency | Passed |
| Generated TypeScript contract diff | Clean |
| Frontend lint / strict typecheck | Passed |
| Vitest component, auth and contract cases | 12 passed |
| Next.js production build | Passed on Windows and in Linux Docker |
| npm clean install | Passed on Windows and Linux |
| Playwright real HTTP learning flow | Desktop and mobile passed |
| Axe WCAG 2 A/AA, 2.1 AA, 2.2 AA | No violations on dashboard, citation dialog and quiz feedback |
| Responsive body overflow | Dashboard checked at 360, 390, 768, 1024, 1280, 1440 px |
| Compose web/API/DB/migration | Built and healthy on isolated volumes |
| HTTP storage smoke | Real PostgreSQL + Chroma, synthetic embedding/LLM; passed |
| API/DB restart persistence | Documents, evidence and one idempotent quiz attempt retained |
| Alembic metadata consistency | No new upgrade operations detected |

Windows pytest temp-file access and Node subprocesses required execution outside
the filesystem sandbox. Initial sandbox failures were rerun successfully; no tests
were skipped to make results green. Existing dependency deprecation notices remain.

## Evidence and coverage

The browser flow exercises register/login/reload, upload, ready state, source-based
chat, citation sheet/Escape, mobile pane switching without losing draft, four-option
quiz, feedback, persisted progress, logout and protected-route redirect. HTTP tests
also cover invalid PDFs, hash dedupe, embedding/quota failures without secret leakage,
expired/rotated sessions, Origin rejection, identity spoofing, foreign resources,
strict answer validation, repeat submission conflict, processing recovery and cycles.
Account-change tests prove the previous account cache is removed on identity change.

Review [desktop tutor](screenshots/desktop-tutor.png),
[mobile tutor](screenshots/mobile-tutor.png),
[desktop dashboard](screenshots/desktop-dashboard.png),
[mobile dashboard](screenshots/mobile-dashboard.png),
[desktop quiz](screenshots/desktop-quiz.png) and
[mobile quiz](screenshots/mobile-quiz.png) against the original `assets/` sketches.

Design differences are deliberate and based on current backend capabilities:
document workspaces replace persisted courses; the reader shows indexed text because
PDF originals are not stored; dashboard cards reflect actual documents/attempts
rather than invented schedules, mastery or recommendations. There is no raw reasoning
log, fabricated citation, fake progress percentage or inert unsupported feature tab.

## Remaining production gates

- Real-provider/model acceptance and answer-quality evaluation using approved PDFs.
- Backup/restore of copies of existing production PostgreSQL/Chroma data and proof
  those historical records can be read by the new stack.
- Traffic rollback rehearsal against that restored data, plus physical-phone checks.
- Maintainer review of screenshots and operational limits before production cutover.

Consequently Phase 8 delivers additive Docker/CI infrastructure; it does not change
production traffic or remove Streamlit. One API worker, process-memory sessions and
unfinished quizzes, synchronous bounded ingestion and text-only reading are published
MVP limits. The original Compose/Streamlit stack remains the rollback baseline.

The test-only provider factory exists only in explicit test scripts and Compose
overrides. The production API has no mock switch. The isolated local smoke stack
was stopped after verification, with its synthetic volumes preserved.
