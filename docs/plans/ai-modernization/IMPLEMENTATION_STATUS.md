# Incremental implementation status — 2026-10-14

## Current post-merge execution

Current branch: `feature/ai-online-eval-baseline`, based on merged `develop`
`79224d718ce154fbb1a2222fc9c5955e64ae4480`. The
[execution plan](09_POST_MERGE_AI_EXECUTION_PLAN.md) governs this work. The
[merge-SHA rebaseline](../../reports/ai-eval/POST_MERGE_BASELINE.md) verifies CI on
that merge and a fresh offline run; independent G0 approval is still pending.

| Milestone | Implementation / remaining acceptance |
| --- | --- |
| M0 / G0 | Merge verified, clean branch, local regression/golden passed; reviewer signoff pending |
| M1 / G1 | V2 independent-label schema/validator and source/topic/split checks implemented; only one approved PDF, no independently annotated ≥100-case dataset |
| M2 / G2 | Real SQL/BGE-M3/hybrid/full ReAct harness and fresh per-sample clones implemented; two-case Gemini smoke passed with three calls, full three-case accepted dry run pending |
| M3 / G3 | Private answer export, blinded review packets and separate assignment map implemented; quality baseline/review/signoff pending |
| M4 / M5 | LangChain POC and adopt/iterate/reject decision remain gated by G3 |

Gemini calls are opt-in with a pinned model, durable request budget, no retries,
no fallback and failure blocking. The current default is `gemini-3.1-flash-lite`
with minimal thinking. The separate synthetic golden continues to use offline
fixtures. See [live usage and limits](../../../evaluation/live/README.md) and
[actual smoke/test evidence](../../reports/ai-eval/2026-10-14-live-evaluation.md).
This does not close human labels, citation support, personalized chat-memory,
UI acceptance or operational release gates. Stable application/frontend/persistence
modules were not refactored in this post-merge slice.

## Historical foundation and review slices

Branch: `feature/ai-eval-foundation`, based on merged `develop` at
`4302d971c31e1944b3280b20d3f1fc9f83135ea4` (UI PR #16). The ten roadmap documents
from `APPLY_TO_REPO.md` are now under `docs/plans/ai-modernization/`. Phase 1 has an
executable foundation; its benchmark acceptance gate remains open. Phases 2–6 are
proposals and have not been implemented or enabled.

The Agent/API refactor is recorded separately in commit `bd9eab8`; evaluation,
roadmap documents and validation evidence were committed in `679665b`.

Review follow-up uses `fix/eval-metrics-and-coverage` from `679665b`, following
the review's option A without merging or changing `develop`. Metric/tool/retrieval
semantics are corrected in `00a951c`; SQL/API scope coverage and the versioned
golden CI gate are recorded in `ba36691`. See the
[review resolution and fresh local evidence](../../reports/ai-eval/2026-10-14-review-resolution.md).
QA-01 through QA-06 have local implementation/test evidence. The fix and foundation
have since merged through PRs #17/#18; CI on the resulting merge was successful.
Independent Tech/Test Lead phase signoff remains pending. The report below records
the earlier slice, rather than evidence for the current online harness.

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
production load performance or deployment. The foundation V2 CLI is synthetic;
the current post-merge live CLI is described above. The synthetic smoke uses
a search-only prompt and lexical retriever, not BGE-M3/hybrid production ranking.
Unknown legacy tool validation, refusal and usage remain explicitly unmeasured.
Metric schema version 2 distinguishes standard recall from hit rate, initial ranking
from multi-search coverage, and expected denials from unexpected failures. Candidate
evidence is separate from nullable supporting-citation telemetry. The historical
foundation report retains version 1 semantics and is not rewritten as new evidence.

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
