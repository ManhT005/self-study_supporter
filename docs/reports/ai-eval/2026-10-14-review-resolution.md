# Foundation review resolution — 2026-10-14

Reviewed base: `679665b7d14c0d005d8a63724c649ca5957ddd4f`.
Fix branch: `fix/eval-metrics-and-coverage`, created from that foundation (review option A).
The [provided Test/Tech review](AI_EVAL_FOUNDATION_TEST_TECH_REVIEW_2026-10-14.md)
is preserved as historical input; its quoted GitHub CI run was not rerun or independently
verified here. This report records fresh local implementation/testing, not independent
Tech/Test Lead signoff, a maintainer merge decision or Phase 1 benchmark acceptance.

## Traceability and actual verification

| Issue | Test IDs / coverage | Implementation commit | Local result |
| --- | --- | --- | --- |
| QA-01 | TC-EVAL-01a–e: partial/full/missing gold, duplicates, MRR, empty gold | `00a951c`; semantic golden in `ba36691` | Standard recall differs from hit rate; schema 2 recorded; passed |
| QA-02 | TC-SEC-01/02: HTTP A/B cookies, foreign chat/note/quiz, uniform 404, no provider/vectors/writes; TC-SEC-03: SQL ownership rejects ranking; TC-SEC-04: concurrent A/B; TC-SEC-05: injected text + forged model identity args | `ba36691` | Passed with real SQLite repositories/application/legacy dispatch and deterministic vectors/providers |
| QA-03 | TC-TOOL-01–06: required vs allowed, no-tool/null, unknown tool, RAG-only N/A, unobserved validation, partial required coverage | `00a951c`; golden in `ba36691` | Passed; no vacuous empty-tool success |
| QA-04 | TC-RETR-01–05: empty initial then successful retry, duplicate union, later irrelevant search, no search and instrumentation fallback | `00a951c`; golden in `ba36691` | Passed; initial ranking and aggregate retrieval are separate |
| QA-05 | TC-GATE-01/02 and negative mutation/CLI tests: wrong semantics, missing/duplicate cases, wrong hashes, forced unknown validity, absent expected denial, unexpected errors, bad provenance and paired stats | `ba36691` | Golden pass verified; deliberate regressions fail; malformed CLI input exits 2, violated policy exits 1 |
| QA-06 | Expected vs unexpected record outcome classification and missing-denial regression | `00a951c`, `ba36691` | Passed; 90 = 78 completed + 12 expected denials + 0 unexpected failures |
| QA-07 | Online account/history/side-effect/cache isolation | Separate future baseline work | Open; live callbacks remain caller-managed |
| QA-08 | Candidate `retrieved_evidence` vs unmeasured `supporting_citations=null`, legacy candidate alias retained | `00a951c` | Telemetry/docs distinction implemented; claim-level support adjudication remains open |
| QA-09 | Approved independent ≥100 labels, seven strata, frozen holdout, real hybrid/BGE-M3/provider and blinded review | Separate Phase 1 acceptance | Open; synthetic smoke remains 15 unique development cases |

## Fresh local checks

Python 3.12.7 on Windows. Commands ran against the fix working tree, followed by a
clean committed CLI/gate run pinned to `ba366910d9c9658fe56676ebb6e708d2295660d4`.

| Command/check | Actual result |
| --- | --- |
| `python -m pytest -c pytest.ini backend/tests/unit backend/tests/contract apps/api/tests -q` | 178 passed |
| Frontend `npm test` | 12 passed across three files |
| Ruff lint / format | Passed; 177 Python files formatted |
| Import boundary gate | Passed |
| Runtime HTTP OpenAPI check | Matches committed snapshot |
| Full synthetic CLI + golden gate | Passed; metric schema 2; 90 records |
| Diff of production core, API app and frontend | Empty; no production source changes |

The clean run manifest records `git_dirty=false`, top-k 3, seed 42, three repetitions,
synthetic-echo-v1, a lexical index and both prompt hashes. Run ID:
`65910e5818104e6ab39c30374a12983a`.
The local sanitized report is under ignored
`data/evaluations/65910e5818104e6ab39c30374a12983a/results.json`.
Dataset SHA-256: `d139fc49ebf04c5ea415d275f4b194c7131c171476b332f7cfd3e7d46258672a`.
Corpus SHA-256: `9d2a1b2798b4a41dc2c67044c73428ef0349f4ed681977f325c8991735feab7a`.
Golden revision 1 pins these plus the unchanged baseline prompt hashes.

## Compatibility and remaining gates

Version 1's `recall_at_k` was hit rate; those reports must not be compared as standard
recall. Version 2 retains a separate hit rate and explicit initial ranking aliases,
adds multi-search/union metrics, and declares tool capabilities. Compatibility
`n_valid`/`n_failed` retain raw status counts; use exclusive outcome groups for failure
reporting. Candidate citations are not claim support, and legacy validation, refusal,
usage and cost remain unknown. No model, production retriever, prompts, tool set,
iteration limit, provider selection, HTTP DTO, frontend, SQL schema, Chroma IDs or
embedding settings changed. Revert the fix commits to roll back; no migration/reindex.

CI now invokes the frozen golden gate and uploads the sanitized offline artifact even
on failure. The fresh six-job remote CI run (including PostgreSQL/Docker/browser E2E)
and independent Tech/Test Lead/maintainer decisions have not been performed by this
local task. Scripted SQL/API identity-injection tests prove their scoped boundary;
they do not establish general real-model prompt-injection robustness or physical
Chroma isolation. Engineering fixes are locally verified; the online benchmark and
framework migration remain gated by QA-07/08/09 and the existing UI operational gates.
