# Post-merge rebaseline — 2026-10-14

Baseline `develop`: `79224d718ce154fbb1a2222fc9c5955e64ae4480`.
Implementation branch: `feature/ai-online-eval-baseline` from that exact merge SHA.
GitHub REST API confirmed PR #18 merged at `2026-10-14T11:22:59Z` and
[Actions run 38556175138](https://github.com/ManhT005/self-study_supporter/actions/runs/38556175138)
completed successfully on the same merge SHA. All six jobs were successful:
offline, API, PostgreSQL, web, workspace Docker and legacy Docker.

Fresh local evidence, Python 3.12.7 on Windows:

| Check on merge SHA | Actual result |
| --- | --- |
| Backend unit/contract + API suite | 178 passed |
| Synthetic CLI and golden revision 1 | Passed; metric schema 2 |
| Synthetic accounting | 90 records; 78 completed, 12 expected denials, 0 unexpected failures |
| Import boundary gate | Passed |
| Initial checkout | Clean; manifest `git_dirty=false` |

Synthetic run ID: `ad76407937c7453c90888ae237cc503e`.
Private local artifact: `data/evaluations/ad76407937c7453c90888ae237cc503e/results.json`.
This verifies engineering behavior, not a real-model benchmark or Phase 1 acceptance.
No schema migration, user-data change, production provider call or traffic cutover
was part of this rebaseline. Independent QA/maintainer G0 signoff remains pending.

The [post-merge execution plan](../../plans/ai-modernization/09_POST_MERGE_AI_EXECUTION_PLAN.md)
governs the next changes. User-authorized smoke source is a single private PDF under
ignored `data/`; it is insufficient for independent ≥100-case/seven-stratum G1
acceptance and document/topic-disjoint holdout. Requested provider is Gemini with
a small free-tier request budget. Source text and answers remain private.

UI production cutover remains a separate gate: real-provider UI acceptance,
historical SQL/Chroma restore, traffic rollback, physical-phone checks and maintainer
review in [UI validation](../../design/ui-v1/VALIDATION.md). These do not prevent
isolated offline research but are not closed by this report or an AI smoke run.
