# Architecture decisions

Status: accepted for implementation. Owner: ManhT005 (repository maintainer).
Revisit via a separate PR with tests and migration evidence.

| ADR | Decision | Rationale and consequence |
| --- | --- | --- |
| 0001 | Modular monolith before v1 | Keep one deployable application; no microservice coordination cost. |
| 0002 | Single `study-supporter` distribution, Python src layout | Installed imports use `study_supporter`; root `src`/`ui` removed after consolidation tests. |
| 0003 | LangGraph belongs to orchestration | Core algorithms and use cases remain framework independent; no LangGraph dependency during consolidation. |
| 0004 | PostgreSQL is authoritative; Chroma stores vectors | Resolve collections using authenticated ownership. Preserve existing vector IDs/dimensions and string quiz user IDs until a reviewed data migration. |
| 0005 | Validate local Docker before UI/API split | Persistent app/PG/model volumes; Ollama optional, no models fetched at build time. |
| 0006 | Reproducible experiments | Freeze RRF semantics and synthetic fixtures; new retrieval changes need datasets, baseline and measured results. |

Existing populated schemas require backup and schema comparison before any manual
Alembic stamp. Never auto-stamp, reset volumes, change vector dimensions or tag v1 during consolidation.

See [repository consolidation](repository-consolidation.md) for the current resource, scope and dependency decisions.
