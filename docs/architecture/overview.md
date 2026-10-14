# Application architecture

One `study-supporter` distribution contains all product use cases. Streamlit under
`apps/streamlit_legacy` renders application results; `bootstrap.ApplicationFactory`
owns explicit database lifecycle, lazy shared embeddings and per-account learning
sessions. No user-bound retriever or agent is cached across accounts.

| Layer | Responsibility |
| --- | --- |
| domain | Documents, quiz/graph validation, authenticated errors, conversation policy |
| ai | Deterministic chunking, RRF, graph ordering and quiz/JSON parsing |
| application | DTOs, ports, ingestion/retrieval/answer/learning services |
| infrastructure | SQLAlchemy, Chroma, PyMuPDF, embeddings and LLM SDK/HTTP adapters |
| orchestration/legacy_react | Original text parser and five-step tool workflow |
| bootstrap | Resource wiring and provider priority |
| apps/streamlit_legacy | Authentication/session adapter and presentation |

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
tests are unified under `backend/tests`. Next.js/FastAPI/LangGraph are not introduced.
See [boundaries](module-boundaries.md), [ADR](adr/repository-consolidation.md),
[historical baseline](current-state.md) and [current acceptance](../reports/repository-consolidation-acceptance.md).
