# AI Modernization Roadmap — Self Study Supporter

**Version:** 1.0-draft · **Date:** 2026-10-14 · **Target branch reviewed:** `feature/ui-learning-workspace`
**Repository:** https://github.com/ManhT005/self-study_supporter · **Status:** Roadmap proposed; incremental evaluation foundation implemented, phase acceptance pending.

These plans were applied after the UI branch merged into `develop` at
`4302d971c31e1944b3280b20d3f1fc9f83135ea4` (PR #16). See
[current implementation and open gates](IMPLEMENTATION_STATUS.md); the original
branch observations below remain historical inputs, not fresh acceptance evidence.

> These files are implementation plans, not evidence that their work is complete. The repository was inspected via GitHub on 2026-10-14. Before starting each sprint, recheck the branch head, CI, open PRs and runtime dependency APIs. Do not copy proposed performance targets into release reports as achieved results.

## Reading order

For disabled LangChain engineering work, the
[implementation-ready plan](10_LANGCHAIN_POC_IMPLEMENTATION_READY.md) revises the
older G3 dependency: LC-PR01..04 may proceed in parallel with labels/baseline.
[Current engineering evidence](../../reports/ai-eval/2026-10-15-langchain-poc.md)
does not close G3 or permit comparative claims/production rollout.

After the foundation merge, start with the
[post-merge execution plan](09_POST_MERGE_AI_EXECUTION_PLAN.md) and
[fresh merge-SHA evidence](../../reports/ai-eval/POST_MERGE_BASELINE.md), followed by
[bounded live-smoke evidence](../../reports/ai-eval/2026-10-14-live-evaluation.md).

| File | Scope | Primary deliverable |
|---|---|---|
| [`MASTER_PLAN.md`](MASTER_PLAN.md) | North star, architecture, dependencies, stages 1–6, release sequencing | One accountable roadmap |
| [`00_BASELINE_EVALUATION.md`](00_BASELINE_EVALUATION.md) | Freeze UI/core baseline, eval datasets, harness, measurement, gates | Reproducible comparison |
| [`01_LANGCHAIN_POC.md`](01_LANGCHAIN_POC.md) | `create_agent`, **4 real tools**, provider adapters and safe POC | Native tool calling with feature flag |
| [`02_LANGGRAPH_CORE.md`](02_LANGGRAPH_CORE.md) | Tutor / Quiz / Planner stateful workflows, routing, API contracts | Deterministic orchestration |
| [`03_ADAPTIVE_RAG.md`](03_ADAPTIVE_RAG.md) | Router, hybrid search, rerank, concept graph, evidence grader | Benchmark-backed retrieval |
| [`04_MEMORY_PERSISTENCE.md`](04_MEMORY_PERSISTENCE.md) | Checkpoints, memory policies, progress/mastery, resume, tenancy | Safe persistence |
| [`05_HARDENING_RELEASE.md`](05_HARDENING_RELEASE.md) | Tracing, limits, security, CI, Docker, rollback and release | Release readiness |
| [`06_BACKLOG_SPRINTS.md`](06_BACKLOG_SPRINTS.md) | Sprint plan, work items, effort, dependencies, PR slices | Executable team backlog |
| [`07_ADRS_EXPERIMENTS.md`](07_ADRS_EXPERIMENTS.md) | Architecture decisions, research hypotheses and experiment templates | Explainable design trade-offs |

## First actions (do these before implementing a new framework)

1. Review `docs/design/ui-v1/VALIDATION.md` and close **remaining real-provider, historical backup/restore, rollback and mobile acceptance gates**. Keep Streamlit as fallback until complete.
2. Freeze a **known-good Git SHA**, current database / Chroma collection contracts, and baseline E2E evidence. Do not merge AI changes into the UI PR at the same time.
3. Implement Phase 1 benchmark and evaluate legacy ReAct/RAG-only **before** introducing LangChain or LangGraph.
4. Put any new orchestration behind `AI_ORCHESTRATOR=legacy|langchain|langgraph`; keep default `legacy` until phase-specific release criteria pass.
5. Make scoped PRs to `develop`. Use `main` only for reviewed releases, following the project's branch policy.

## Terminology

- **Observed:** confirmed in repository files or existing validation records; **not** newly executed by this plan.
- **Proposed:** a decision/target requiring team sign-off and test evidence.
- **Gate:** a documented set of verifiable evidence blocking advancement or release.
- **Offline unit:** fake model, fake retriever and synthetic accounts; must not call a network or mutate real data.
- **Online benchmark:** explicitly opt-in, with model/document version, token, cost, latency and evaluator recorded.

## Existing references

- [Repository architecture](../../architecture/overview.md)
- [Existing P0 plan](../PHASE_0_ENGINEERING_FOUNDATION.md)
- [UI validation evidence](../../design/ui-v1/VALIDATION.md)
- [Learning workspace operations](../../operations/learning-workspace.md)
- [Existing eval runner](../../../evaluation/README.md) (from repo root: `evaluation/README.md`)
- [LangChain agents](https://docs.langchain.com/oss/python/langchain/agents)
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)

**Scope discipline:** No code, database migration, credential change, production traffic switch, or GitHub push has been performed by generating these documents.
