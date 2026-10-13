# Repository consolidation acceptance

Implemented on 2026-10-14 from `origin/develop` at
`5c9a16d2eb133ec4f20cdc6093b2cda970755603`. Base foundation CI was independently
verified successful; it is not counted as CI evidence for these local changes.

All product implementations now live in `backend/src/study_supporter`. The root
`src/`, `ui/` and split test tree are removed. Streamlit calls account-bound
application services, and ReAct tools take identity from AppContext rather than
LLM arguments or a user-ID prefix in the question. Root commands are redirects.

Dependencies are declared once in `backend/pyproject.toml`; generated locks live
in `requirements/`. Docker/native templates live in `config/`. Existing local
`.env`/`.env.docker` credentials remain unchanged and ignored. Every locked runtime
version is unchanged; the dev lock adds the existing BM25 dependency for offline checks.

Local commits/checkpoints are a dependency stack based on develop:

| Slice | Commit | Branch checkpoint |
| --- | --- | --- |
| Contracts | 2965b38 | refactor/core-contracts |
| Configuration/bootstrap | a5213b8 | refactor/config-bootstrap |
| Persistence/ownership | d75c05a | refactor/persistence-repositories |
| Document ingestion | 98bdd37 | refactor/document-ingestion |
| Retrieval adapters | f5c45cf | refactor/retrieval-adapters |
| Learning services | 45b971c | refactor/learning-services |
| ReAct/Streamlit boundary | f478856 | refactor/agent-ui-boundary |
| Requirements/env cleanup | 0d79829 | refactor/legacy-cleanup |
| Namespace removal, QA and docs | final cleanup commit | refactor/legacy-cleanup |

Submit/rebase the slices in plan order after review. No push, remote PR, merge or
release tag is part of this local execution.

| Verification | Evidence |
| --- | --- |
| Original baseline | 91 offline tests on Windows |
| Final offline suite | 121 tests; all old tests retained and collected in backend/tests |
| Windows | Python 3.12.7: 121 passed, 11.04 seconds |
| Linux | Python 3.11 in Linux Docker: 121 passed, 23.57 seconds |
| Architecture/lint/format | Import gate, caller/presentation boundaries, Ruff check/format passed |
| Package | Wheel/sdist built; wheel imported outside repository with src/ui unavailable |
| PostgreSQL 16 fresh schema | Alembic upgrade/check, no drift, 3 integration tests passed |
| Docker and Streamlit | Final image healthy; AppTest registration/logout/B login, fake services seed/verify and absence of src/ui namespaces passed |
| Historical SQL/Chroma data | Baseline SQL/Chroma snapshot restored into consolidation-restore-20261014; canonical auth/chat/citations/quiz/progress/notes and A/B isolation verification passed |
| Real model smoke | BGE-M3/1024D and Ollama qwen3:1.7b: canonical ingestion/retrieval/ReAct/evidence/quiz/persisted progress passed |
| Real browser automation | Final Chromium flow pending |
| Remote CI and human acceptance | Pending publication/review by maintainer |

Fresh synthetic SQL/Chroma seed was verified again after Compose down/up without
removing volumes. The backup baseline is retained locally under
`data/backups/consolidation-baseline-20261014`; restored/smoke project volumes are
also retained, and disposable containers are stopped after checks.

Preserved data contracts: Alembic `p0_0001`, SQL tables/columns, string
`QuizAttempt.user_id`, Chroma `documents_<id>` and `user_memory`, BGE-M3/1024D,
chunk hashes/provenance, BM25 tokenizer, RRF tie ordering, graph extraction prompt,
provider priority and ReAct five-step ceiling. No reindex, schema change or volume
reset is required. Historical engineering notes are retained in docs/archive.

Known limits remain explicit: quiz context still samples the first five chunks;
ingestion hash locking protects one process, not multiple workers; PDF scans need
OCR; generated quiz sets/history are session-scoped while attempts and graphs
persist in SQL; model smoke uses synthetic accounts and is not a quality benchmark. Human
browser review, Tech Lead/Test Lead sign-off and final remote CI are still required
before claiming the plan's overall merge acceptance.
