# Delivery Backlog & Sprint Execution Playbook

**Planning assumption:** 2 engineers (AI/Backend + Full-stack), 1 rotating reviewer; 5 workdays/week, 2-week sprints, effective capacity ~60–70% after review/testing/maintenance. **Estimates are planning ranges, not commitments.** Re-estimate from baseline after first sprint.

## 1. Workstream execution model

- Branch from updated `develop`: `feature/ai-eval-foundation`, `feature/langchain-tools`, `feature/langgraph-tutor`, `feature/langgraph-quiz`, `feature/langgraph-planner`, `feature/adaptive-retrieval`, `feature/agent-persistence`, `chore/ai-hardening`. Avoid stacking all changes directly in `feature/ui-learning-workspace`.
- UI branch: complete/merge reviewed UI work to `develop` first when its contract cutover criteria permit; otherwise isolate AI work against a frozen integration base and forward-port using reviewed PRs.
- PR policy: target **one vertical slice** and preferably <400–600 changed functional LOC outside generated files; attach checklist, test command/output, screenshots if UI and benchmark if AI behavior changes.
- Merge chain `feature/* → develop → main` with protected main, reviewer + CI, tagged releases; hotfix via `fix/*` and back-merge to develop. Do not push to main.
- Use shared `AgentPort` / DTOs and offline fixture fakes so frontend and backend can work in parallel; regenerate typed API client in same PR as schema changes.

## 2. Suggested sprint plan (12 weeks as reference; gates override dates)

| Sprint | Goal | Task IDs | Exit artifact |
|---|---|---|---|
| **Preflight (3–5d)** | Close UI operational gates, freeze integration SHA | PF-01..PF-04 | UI cutover decision + backup snapshot |
| **S1** | Eval datasets, harness, baseline comparison | BL-01..BL-07 | Phase 1 report + frozen holdout |
| **S2** | Native tool calling POC and contract | LC-01..LC-07 | LangChain flag + paired eval |
| **S3** | Graph router + Tutor with evidence | LG-01..LG-03 | Tutor graph + all golden transitions |
| **S4** | Quiz/Planner graphs + typed FE | LG-04..LG-08 | full workflow beta, no restart promise |
| **S5** | Adaptive router and retriever ablations | AR-01..AR-04 | retrieval benchmark deltas |
| **S6** | Evidence grader + adaptive quiz | AR-05..AR-06 | chosen RAG arm + guardrail report |
| **S7** | Durable checkpoint + memory and ownership | MP-01..MP-03 | authorized resume + migration evidence |
| **S8** | Privacy controls + persistence integration | MP-04..MP-05 | deletion + restart E2E |
| **S9** | Tracing, quotas, adversarial tests | HR-01..HR-03 | load/soak + privacy checks |
| **S10** | CI integration, real-model benchmark, release rehearsal | HR-04..HR-06 | candidate release checklist |

Ten 1-week milestones or ~5 two-week sprints are also possible depending on staffing, but **do not compress baseline and privacy gates**. Planned duration ~10–14 weeks including peer review/bug buffer is more realistic than promise based on framework installation alone.

## 3. Prioritized task backlog — implementation ready

**Priority:** P0 blocker, P1 must-have for beta, P2 research/optional. **Size:** relative effort: S = 0.5–1d, M = 1–3d, L = 3–5d, XL = split before implementation.

| ID | Priority | Size | Owner | Scope / files | Dependency | Acceptance evidence |
|---|---|---|---|---|---|---|
| PF-01 | P0 | M | Full-stack | review UI `VALIDATION.md`; real-provider smoke | current UI branch | real answers + citations verified |
| PF-02 | P0 | M | Backend | historical SQL/Chroma copy restore and rollback | PF-01 | verified owned document + quiz + notes |
| PF-03 | P0 | S | Full-stack | phone/browser UI + accessibility signoff | PF-01 | screenshots/test device checklist |
| PF-04 | P0 | S | Lead | freeze SHA, architecture drift and branch integration plan | PF-01..03 | approved baseline decision |
| BL-01 | P0 | M | AI | data fixture and labeling guide | PF-04 | ≥100 versioned cases, holdout protected |
| BL-02 | P0 | M | AI | `evaluation/runner_v2.py`, adapter variants | BL-01 | no `[:5]`, deterministic smoke |
| BL-03 | P0 | M | Backend | sanitized run artifact + schema | BL-02 | manifest + typed error records |
| BL-04 | P0 | M | AI | retrieval/citation/tool/quiz metrics | BL-02 | correct denominator/failure tests |
| BL-05 | P0 | M | QA | A/B isolation + prompt injection fixtures | BL-01 | no-leak regression suite |
| BL-06 | P0 | M | AI | paired RAG-only vs legacy evaluation | BL-03/04/05 | report with CI, cost, timing |
| BL-07 | P0 | S | Lead | signoff Phase 1 | BL-06 | baseline frozen and PR reviewed |
| LC-01 | P0 | M | AI | provider tool-call capability spike | BL-07 | Ollama/cloud compatibility matrix |
| LC-02 | P0 | M | Backend | `AgentPort` and DTO contracts | BL-07 | import gate and API tests |
| LC-03 | P0 | L | AI | four typed tools under orchestrator | LC-01/02 | forged user ID rejected; ≤5 steps |
| LC-04 | P0 | M | AI | `create_agent` runner + timeouts/flag | LC-03 | no regex, bounded behavior |
| LC-05 | P1 | S | Backend | factory and API wiring | LC-04 | legacy default, rollback tested |
| LC-06 | P1 | M | AI | compare POC benchmark | LC-05 | ≥99% valid tools candidate gate |
| LC-07 | P1 | S | Lead | ADR + PR acceptance | LC-06 | provider trade-offs recorded |
| LG-01 | P0 | M | AI | LangGraph state, recursion/timeout API spike | LC-07 | state serialization test |
| LG-02 | P0 | M | AI | intent router, safe activities | LG-01 | deterministic routing matrix |
| LG-03 | P0 | L | AI | Tutor graph, citation/abstention policy | LG-02 | no-evidence and loop tests |
| LG-04 | P0 | L | AI | Quiz graph and topic evidence | LG-03 | exact schema, 0 invalid accepted |
| LG-05 | P1 | L | AI | Planner graph and DAG ranking | LG-02 | explainable top next step |
| LG-06 | P1 | M | Backend | API DTO / typed TS regenerate | LG-03..05 | OpenAPI snapshot and consumer tests |
| LG-07 | P1 | M | Frontend | tutor/quiz/plan UI activities | LG-06 | desktop/mobile/a11y E2E |
| LG-08 | P0 | M | QA/AI | workflow evaluation and phase signoff | LG-07 | recorded benchmark + failures |
| AR-01 | P0 | M | AI | retrieve ranking baseline, query taxonomy | BL-07 | Recall/MRR/nDCG report |
| AR-02 | P1 | M | AI | rules router | AR-01 | category tests + safe fallback |
| AR-03 | P1 | L | AI | rerank optional strategy | AR-01 | paired latency/quality ablation |
| AR-04 | P2 | L | AI | graph-backed candidate expansion | AR-01 | concept-to-chunk provenance verified |
| AR-05 | P0 | L | AI | evidence decision + retry/abstention | LG-03/AR-02 | 0 fabricated source IDs |
| AR-06 | P0 | M | Backend/AI | topic-aware quiz retrieval | LG-04/AR-01 | support for every quiz question |
| MP-01 | P0 | M | Backend | authorized thread registry | LG-01 | B cannot resume A thread |
| MP-02 | P0 | L | Backend | Postgres saver adapter + migration | MP-01 | restart + restore tests |
| MP-03 | P1 | L | AI | mastery projection and provenance | LG-05 | deterministic recomputation |
| MP-04 | P0 | M | Backend | note/memory controls, delete/export | MP-02 | privacy lifecycle tests |
| MP-05 | P1 | L | Full-stack | resume/approval APIs and UI | MP-02/04 | restart E2E, no duplicate writes |
| HR-01 | P0 | M | Backend | quotas, timeout, retry, cancellation | LG-08 | bounded load and 429 behavior |
| HR-02 | P0 | M | Backend | tracing + redaction | HR-01 | trace correlation, no secrets |
| HR-03 | P0 | M | QA | restore/rollback, adversarial suite | MP-05 | runbook rehearsal evidenced |
| HR-04 | P0 | M | DevOps | CI offline + staged model jobs | BL-04/HR-03 | green gates with separation |
| HR-05 | P1 | M | QA | load/soak, real-provider benchmark | HR-04 | latency, quality, usage report |
| HR-06 | P0 | S | Lead | release candidate Go/No-Go | HR-05 | signed evidence + known limits |

## 4. Top 10 next actionable tasks (in order)

1. `PF-01`: run a real approved PDF and real provider through Next.js/FastAPI; verify citation support and no fake sources.
2. `PF-02`: restore historical SQL/Chroma copy and prove original documents/notes/quiz resume and rollback.
3. `PF-03`: check physical-device responsive UX and keyboard controls; sign off remaining UI conditions.
4. `PF-04`: pin branch SHA; update stale architecture statement; decide UI-PR merge point.
5. `BL-01`: generate synthetic PDFs, label ≥100 questions and protect the holdout.
6. `BL-02`: refactor evaluation runner; remove hardcoded 5 cases and add `--limit` optional.
7. `BL-03`: define standard run/trace/evidence result schema and error taxonomy.
8. `BL-04`: unit-test retrieval + citation + tools + quiz scoring functions.
9. `BL-05`: adversarial A/B, empty retrieval and prompt-injection corpus.
10. `BL-06`: run paired `rag_only` vs `legacy_react`, publish baseline; **then** start LangChain.

## 5. PR template for every slice

```markdown
## Goal / hypothesis
What measurable behavior should improve and why?

## Code scope
- Changed paths:
- Feature flags and default:
- DB/vector migration (yes/no; backup evidence if yes):

## Contracts and safety
- Authenticated scope preserved:
- Error/timeout/loop behavior:
- Private text/secrets excluded from logs:

## Verification
- Offline tests + command/actual result:
- Integration/E2E + command/actual result:
- AI eval dataset/version/model/CI and deltas:
- Negative tests and rollback:

## Review
- ADR/reference:
- Screenshots/trace/report:
- Known gaps and go/no-go:
```

## 6. Parallelization rules

Backend can implement graph and typed schemas while frontend uses checked-in mock DTOs, **but** both must merge the same generated OpenAPI client change. Retrieval ablations can run in parallel with Tutor tests on a frozen baseline; graph evidence integration waits for the actual adapter. Memory table design may start early as an ADR, but production checkpoint writes wait for graph versioning and rollback tests. Do not run multi-worker persistence experiments against a live legacy Chroma path.

## 7. Finish condition

Every task marked `DONE` needs a PR, commit SHA, fresh checks and an artifact linked in its phase report. Track explicit `BLOCKED`, `IN_REVIEW`, `DONE`, `REVERTED` states; do not mark tasks done based on Markdown creation.
