# Incremental implementation status — 2026-10-14

Branch: `feature/ai-eval-foundation`, based on merged `develop` at
`4302d971c31e1944b3280b20d3f1fc9f83135ea4` (UI PR #16). The ten roadmap documents
from `APPLY_TO_REPO.md` are now under `docs/plans/ai-modernization/`. Phase 1 has an
executable foundation; its benchmark acceptance gate remains open. Phases 2–6 are
proposals and have not been implemented or enabled.

The Agent/API refactor is recorded separately in commit `bd9eab8`; evaluation,
roadmap documents and validation evidence form the next scoped commit on this branch.

## Delivered in this branch

1. `AnswerQuestionUseCase` consumes `AgentPort` and frozen `AgentResult`, checks
   context/evidence scope, and preserves the adapter trace/usage. It no longer reads
   a mutable tool's `last_evidence` or the vendor-specific ReAct state.
2. `LegacyReActAdapter` builds a recorder, tools and orchestrator per invocation;
   concurrent turns cannot overwrite citations. Distinct evidence from all searches
   is returned, with ordered retrieval metadata and safe tool names. This fixes the
   old last-search-only citation behavior. Parser, prompt builder, four production
   tools, their order and the five-iteration loop remain unchanged.
3. Evaluation has strict versioned labels, 15 reproducible synthetic development
   cases, source/prompt/config manifests, adapter callbacks, paired randomized
   repetitions, typed errors, sanitized records, structural metrics with explicit
   denominators, and case-level paired bootstrap intervals. CI runs it offline.
   Historical online evaluation retains its JSON format with explicit limits/model
   selection, single-retrieval provenance and corrected judge failure denominators.
4. API session readiness and AI admission are extracted from route closures into
   `LearningServices`. `ApplicationFactory(agent_factory=...)` selects orchestration
   at composition; adapter substitution requires no HTTP DTO/route/frontend changes.
   No browser or model argument becomes authenticated identity.
5. The architecture overview's obsolete statement about absent Next.js/FastAPI is
   corrected. Frontend, database schema, embeddings, vector IDs and persistence
   implementations are unchanged.

## Evidence and limits

See the [local validation report](../../reports/ai-eval/2026-10-14-foundation.md).
These checks establish offline behavior and packaging, not real-provider quality,
production load performance, a deployment or remote CI success. V2's CLI is synthetic;
live callback integration/provisioning remains separate opt-in work. The smoke uses
a search-only prompt and lexical retriever, not BGE-M3/hybrid production ranking.
Unknown legacy tool validation, refusal and usage remain explicitly unmeasured.

## Open gates before the next framework phase

- Independently annotate ≥100 approved questions across all seven strata, with
  document/topic-separated splits, frozen holdout and reviewer consensus. Current
  fixtures cover five strata; quiz/personalized and prompt-injection grading remain open.
- Provision isolated online account/history/tool-effect fixtures; freeze actual
  provider/model sampling, full production prompt, BGE-M3/index snapshot, SQL/Alembic
  revision and hardware. Run paired stochastic repetitions and blinded human review.
- Complete or explicitly exclude real-provider UI acceptance, restored historical
  SQL/Chroma, rollback, physical-phone and maintainer signoff from the UI runbook.
- Review the paired baseline report and pass Phase 1 before LangChain/LangGraph.

No new orchestration flags are exposed until corresponding adapters and release
gates exist. Frontend and persistence refactors require a concrete separate need.
