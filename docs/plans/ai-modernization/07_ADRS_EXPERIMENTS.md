# Architecture Decision Register & Research Experiment Protocol

**Goal:** Preserve rationale for engineering choices and convert implementation into evidence of AI-engineering competency. All decisions below are **proposed** until the team signs off in individual ADRs.

## 1. ADR register (create one file per approved decision)

| ID | Proposed decision | Alternative(s) | Decision driver | Approval gate |
|---|---|---|---|---|
| ADR-AI-001 | Keep legacy ReAct as frozen baseline; add `AgentPort` with feature flags | Immediate rewrite | reproducible quality regression and rollback | baseline experiment |
| ADR-AI-002 | LangChain `create_agent` only with native structured tools | text/regex parsing, custom JSON tool harness | schema validation, safe dispatch | provider capability matrix |
| ADR-AI-003 | One explicit LangGraph router + Tutor/Quiz/Planner subgraphs | unconstrained multi-agent swarm | state control, bounded cost, inspectability | graph golden tests |
| ADR-AI-004 | Preserve SQL/Chroma and BGE-M3 1024D, add adaptive retriever behind port | replace vector DB or reindex | backward compatibility, no data loss | restored-data integration |
| ADR-AI-005 | Use rules-first routing, selective rerank, provenance-aware graph only if helpful | heavy LLM router always-on | Pareto quality/latency | held-out ablation |
| ADR-AI-006 | Auth-scoped checkpoint in PostgreSQL via adapter | in-process memory / unscoped saver | restart and tenant isolation | resume + A/B tests |
| ADR-AI-007 | Explicit consent/approval for learner memory and plan writes | auto-store chat history | privacy and predictable autonomy | UX and deletion tests |
| ADR-AI-008 | Offline PR CI + opt-in heavy LLM eval + release quality gate | live external model for every PR | reliability and reproducibility | CI ownership review |
| ADR-AI-009 | Keep Streamlit rollback until UI/historical restore acceptance | immediate deletion | migration reversibility | owner signoff |
| ADR-AI-010 | Separate quiz question issuance, immutable answer key and idempotent grading | all-in-one generated text | correctness and anti-cheat | grader and retry tests |

**ADR template:**

```markdown
# ADR-AI-XXX — Decision title
Date: YYYY-MM-DD
Status: Proposed | Accepted | Superseded | Rejected
Context: observed problem and reproducible evidence
Constraints: compatibility, security, latency, cost, tenancy
Options: at least 2 with trade-offs
Decision: chosen option, owners and applicable flags
Consequences: migration, implementation complexity, risks
Evidence: benchmark IDs, source SHA, test commands, results
Rollback: how to disable or restore data safely
Review date: when to reconsider
```

ADR files should live in `docs/architecture/adr/` and link to a task ID and actual merged PR. This register can remain as a planning index.

## 2. Research questions

- **RQ1 — Orchestration:** Does native `create_agent` reduce invalid tool requests and tool failure rate versus regex ReAct when model, tools and documents are fixed?
- **RQ2 — Workflow:** Does LangGraph improve task completion and failure recovery (quiz validity, correct plan next step, bounded actions) compared to unstructured agent orchestration?
- **RQ3 — Retrieval:** Does a rules-first adaptive router plus selective reranking improve Vietnamese PDF grounding and Recall@5 over existing Dense+BM25+RRF, within acceptable latency?
- **RQ4 — Grounding:** Does evidence grading reduce unsupported claims and mis-citations without overly abstaining on answerable tasks?
- **RQ5 — Personalization:** Does an approved learner profile + progress-aware Planner improve next-step relevance over document-order or static topic lists without misuse of low-confidence mastery?
- **RQ6 — Reliability:** Can authorized graph sessions survive restart and retries without duplicate writes or cross-account access?

## 3. Independent and controlled variables

| Dimension | Hold fixed across experiment | Intentionally vary |
|---|---|---|
| Corpus | approved PDF/document hashes, chunking/embedding/index version | strategy on same indexed documents |
| Model | provider/model/version, prompt system policy, decoding parameters | separately labeled provider experiment only |
| Workload | same labeled cases, owned document scope, concurrency/profile | workflow or retrieval variant |
| Environment | Python, packages/lock, CPU/GPU, warm/cold cache policy | report an additional hardware profile separately |
| Evaluation | same human gold labels, judge rubric, blind labels | scored outputs of variants |
| Budget | same request timeout/steps/token limits where possible | explicit cost/latency trade-off experiment |

Do not simultaneously change prompt, retriever, model and graph then attribute gain to “LangGraph.” Record the exact variant delta. Use random order, fixed dataset split, ≥3 model repetitions for stochastic settings and 95% paired bootstrap intervals; report all errors and denominators.

## 4. Ablation study plan

| Study | A0 | A1 | A2 | A3 | Decision trigger |
|---|---|---|---|---|---|
| Tool calling | legacy regex | native tools | — | — | valid tool success, failure taxonomy, cost |
| Orchestration | native single agent | Tutor graph | Tutor+Quiz | all 3 workflows | completion and loop bounds |
| Retrieval | current hybrid | rewrite hybrid | hybrid+rerank | selective rerank+graph | Recall/nDCG, citation, p95 |
| Grounding | no gate | deterministic support checks | + model grader | + bounded retry | ungrounded rate vs correct abstention |
| Planner | document order | prerequisite DAG | DAG+mastery | + spaced review | human next-step utility and failure safety |

**Decision rule proposal:** Prefer the simplest variant that exceeds baseline on primary metric with acceptable CI and does not violate any security/citation/restart hard gate. If RAG gains are weak, avoid deploying graph expansion. If Planner confidence is low due to sparse attempts, display “insufficient learning history” rather than fabricated personalization.

## 5. Rubric and evaluation artifacts

**Blind answer rubric (1–5 each, with `N/A` allowed):**

- *Correctness*: consistent with annotated reference facts.
- *Groundedness*: support for material claims exists in owned retrieved chunks.
- *Citation validity*: correct document/page/chunk and directly relevant passage.
- *Usefulness*: actionable for requested study task, avoids overconfident guess.
- *Personalization*: uses only approved progress/notes where appropriate, never for factual questions unnecessarily.

**LLM judge restrictions:** use a fixed judge model/prompt/version; ask for structured `{criterion, score, reason_code, cited_ids}`; mask variant names and extraneous system differences. LLM judge cannot be the only oracle; audit 20–30 stratified answers manually and report agreement (e.g. weighted kappa when applicable). Parse failures are counted and surfaced separately, not quietly assigned a valid score.

**Experiment artifact layout (proposed):**

```text
evaluation/
  datasets/v1/README.md
  datasets/v1/questions.jsonl
  datasets/v1/annotations.jsonl  # safe labels only; no private text
  experiments/manifest.schema.json
  experiments/variant_matrix.yaml
  reports/README.md
data/evaluations/<run_id>/      # gitignored raw outputs, no private leak

docs/reports/ai-eval/YYYY-MM-DD-<name>.md
```

**Report template:**

```markdown
# Experiment <ID> — <Title>
- Commit / branch / dataset hash:
- Variants and change:
- Hardware / provider / model / prompt hash:
- Sample sizes / excluded / failures:
- Primary metric absolute values, delta and 95% paired CI:
- Secondary: tool/citation/abstention/quiz/cost/latency:
- Human review and judge agreement:
- Most important 5 failure examples (safe/redacted):
- Security/tenant gate:
- Decision: ship / iterate / reject, rationale and rollback:
```

## 6. Portfolio deliverables

For an AI Engineer portfolio, produce at least:

1. Architecture diagram and ADR log showing *why* native tool calling and LangGraph were chosen rather than only a dependency upgrade.
2. Reproducible baseline vs new variant evaluation with retrieval and answer metrics, confidence intervals, cost/latency and negative results.
3. Schema-validated tool calls, authorization/tenant isolation tests and checkpoint/resume demonstrations.
4. Failure analysis of hallucination/weak evidence and one concrete ablation demonstrating value (or lack of it).
5. Real browser screenshots/video of Tutor, Quiz and Planner using verified citations and persisted progress.
6. Docker/local deployment runbook, CI logs, release gate and safe rollback evidence.

**Do not manufacture quality improvements:** rejected variants, incomplete gates and unresolved provider limitations are valuable technical evidence when documented accurately.
