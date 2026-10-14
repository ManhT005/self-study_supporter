# AI evaluation foundation — local verification

Date: 2026-10-14. Implementation branch: `feature/ai-eval-foundation`.
Frozen pre-change base: `4302d971c31e1944b3280b20d3f1fc9f83135ea4`, merged `develop`.
Python: 3.12.7 on Windows. This is an offline engineering verification report;
it does not accept Phase 1's online quality benchmark or later roadmap phases.
The scoped Agent/API implementation commit is `bd9eab8`; evaluation and this report
are committed separately on the same branch. Pre-commit CLI manifests explicitly
recorded a dirty worktree rather than claiming an already committed execution SHA.

## Fresh local checks

| Check | Actual result |
| --- | --- |
| Pre-change backend/unit/contract baseline | 122 passed |
| Backend/unit/contract + HTTP tests after changes | 153 passed |
| Ruff lint and format | Passed; 174 Python files formatted at verification |
| Import boundary gate | Passed |
| HTTP OpenAPI snapshot | Matches runtime; HTTP response shape preserved |
| Frontend Vitest regression | 12 passed across three files |
| Python packaging | Built sdist and wheel successfully |
| Final telemetry/evaluation regression after name redaction | 14 passed |
| Full synthetic CLI, three repetitions | 90 records; 78 completed, 12 expected scope denials |

Tests cover actual legacy dispatch, max-iteration fallback, evidence accumulation,
fresh/concurrent execution, account rejection before model/tool calls, foreign
response evidence rejection, trace/usage propagation, HTTP adapter substitution,
AI admission release after errors, exact RAG retrieval provenance, dataset validation
and document split isolation, paired ordering/repetitions, explicit sample limits,
privacy probes, sanitized failures, missing judge scores, first-hit/MRR/nDCG and
bootstrap case grouping. Offline fixture tests prohibit socket connections.

Windows sandbox blocked pytest/build temporary directories and Vitest/esbuild child
process creation on initial attempts. Those commands were rerun with the required
permissions; sandbox failures are not reported as application regressions.

## Dataset and acceptance limits

The versioned fixture is 15 public synthetic development cases over three documents
and two accounts. The full regression uses both variants and two repetitions:
60 records, including eight expected `AUTH_SCOPE` denials. Each variant has
30 records: 26 completed and four explicit errors from the scope probes. Missing
legacy tool-validation and refusal signals remain unknown rather than successful.

The smoke uses a lexical retriever, deterministic echo provider and search-only
ReAct prompt. It proves evaluation plumbing, not the production four-tool/hybrid
benchmark. Generated manifests/records live under ignored `data/evaluations/`;
online cases, independent annotations, frozen holdout, usage/cost telemetry,
real-model paired runs and blinded human review are pending. No private PDF,
credential, provider request, database migration or production deployment was
required for this verification. Remote CI and UI operational gates were not run
or signed off by these local checks.
