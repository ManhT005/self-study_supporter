# Application architecture

One `study-supporter` distribution contains all product use cases. Streamlit under
`apps/streamlit_legacy` renders application results; `bootstrap.ApplicationFactory`
owns explicit database lifecycle, lazy shared embeddings and per-account learning
sessions. No user-bound retriever or agent is cached across accounts.

The document-first migration adds `apps/api` as a FastAPI HTTP adapter and
`apps/web` as a Next.js presentation adapter. Both reuse the same distribution;
FastAPI imports never enter the pure core. Next.js proxies same-origin `/api` and
receives dedicated HTTP DTOs rather than ORM models. The runtime OpenAPI snapshot
generates TypeScript types. See [implementation ADRs](../design/ui-v1/IMPLEMENTATION.md)
and [operations](../operations/learning-workspace.md). Streamlit remains until the
original-data restore/rollback and real-provider gates pass.

| Layer | Responsibility |
| --- | --- |
| domain | Documents, quiz/graph validation, authenticated errors, conversation policy |
| ai | Deterministic chunking, RRF, graph ordering and quiz/JSON parsing |
| application | DTOs, ports, ingestion/retrieval/answer/learning services |
| infrastructure | SQLAlchemy, Chroma, PyMuPDF, embeddings and LLM SDK/HTTP adapters |
| orchestration/legacy_react | Original text parser and five-step tool workflow |
| bootstrap | Resource wiring and provider priority |
| apps/streamlit_legacy | Authentication/session adapter and presentation |
| apps/api | HTTP DTOs, cookie sessions, Origin validation, ownership, bounded dispatch |
| apps/web | Responsive learning workspace, forms, queries, evidence and quiz presentation |

Dependencies point from entrypoints/bootstrap to application, domain and injected
adapters. Application may call pure AI algorithms; pure layers cannot import UI,
infrastructure, orchestration, network clients or provider SDKs. Exact deterministic
vendor exceptions are checked by the AST gate and negative tests.

PostgreSQL owns accounts/documents/quiz attempts; Chroma retains `documents_<id>`
and `user_memory`. Immutable AppContext binds identity from authentication; tools
accept content/query parameters only. Existing Alembic revision/string quiz IDs,
BGE-M3/1024D, hashes, tokenizer, RRF ordering and prompts are preserved.

Ingestion is synchronous with trace-linked progress, per-process user/hash locking
and READY only after verified chunk IDs. Multi-process hash uniqueness is a future
schema/concurrency task. Quiz generation still samples the first five chunks;
retrieval quality and Vietnamese tokenization changes require separate benchmarks.

Root `src/` and `ui/` have been removed. `evaluation/` contains opt-in experiments;
tests are unified under `backend/tests`, with HTTP tests in `apps/api/tests`.
Next.js/FastAPI are additive adapters; LangChain/LangGraph remain gated proposals.
See [boundaries](module-boundaries.md), [ADR](adr/repository-consolidation.md),
[historical baseline](current-state.md) and [current acceptance](../reports/repository-consolidation-acceptance.md).

Answer execution uses the framework-independent `AgentPort` and frozen `AgentResult`.
`AnswerQuestionUseCase` validates the bound context and response evidence scope;
`LegacyReActAdapter` creates a recorder, tools and orchestrator for each invocation.
It preserves the original parser/prompt/five-step loop, accumulates distinct evidence
across searches, and exposes only tool names and hashed retrieval metadata. Usage,
abstention and tool validation remain unknown when legacy execution cannot measure them.
`ApplicationFactory(agent_factory=...)` is the composition seam for future adapters.
`apps/api/app/learning_services.py` owns session readiness and AI admission; routes
authenticate, validate HTTP DTOs and map responses. HTTP shapes remain unchanged.

The [AI roadmap](../plans/ai-modernization/README.md) and
[execution status](../plans/ai-modernization/IMPLEMENTATION_STATUS.md) distinguish the
offline evaluation foundation from the pending online benchmark and later frameworks.
