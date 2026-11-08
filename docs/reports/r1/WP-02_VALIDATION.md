# WP-02 — Legacy Agent write denial

Base: `develop@1f21529` (WP-01 merged through PR #20). This is engineering evidence for the G0/G1 review. The frozen SRS registry still records planned ownership and the formal UAT results remain pending. The user rejection and audit steps of UAT-18 belong to WP-05.

## Enforcement

Legacy ReAct dispatch and its tool prompt share one allowlist. Tools are excluded by default and must opt in as read-only with respect to persisted learning state. `search_docs`, `get_progress` and `generate_quiz` are eligible. Quiz generation in this loop returns transient content. The production and evaluation tool factories omit `save_note`, and dispatch rejects it even if it is registered by mistake. Unknown or denied calls get the same response. Authenticated direct notes continue to use the Core note use case. WP-05 owns the future approval-and-write path.

The change has no schema migration or HTTP v1 contract change. If a newly introduced tool fails review, remove its registration or read-only opt-in. A rollback must preserve the deny-by-default boundary.

## Trace and results

| SRS references | Executable evidence | Engineering result |
| --- | --- | --- |
| NOTE-02, TUT-07, BR-12/13, UAT-10, UAT-18 write denial only | `apps/api/tests/test_learning.py::test_injected_pdf_cannot_save_notes_even_after_retry_but_manual_note_can` | Real PDF parsing and HTTP chat with a scripted provider. A retrieved instruction triggered valid save attempts and an unknown action. The note store was identical before and after chat. Manual notes saved on either side of chat. |
| TUT-07, BR-12/13, NFR-03 | `backend/tests/unit/test_react_baseline.py::test_react_denies_misregistered_write_and_unclassified_tools`, `::test_react_invalid_arguments_never_call_tool`, `::test_react_progress_observation_cannot_authorize_note_write` | A registered write tool with valid arguments, an unclassified tool and malformed argument containers are denied. Hostile progress output cannot authorize writes. |
| NFR-03, UAT-10 | `backend/tests/contract/test_agent_sql_scope.py`, `apps/api/tests/test_learning.py::test_tc_sec_01_02_foreign_chat_note_quiz_never_call_provider_vectors_or_write` | Foreign HTTP resources return 404 before provider or vector access. Retrieved hostile content and forged model arguments cannot change the authenticated scope. Concurrent accounts retain separate evidence. |
| Baseline and compatibility | `scripts.verify_r1_baseline --source <approved Word file>`, `scripts.export_http_contract --check`, `scripts/check_import_boundaries.py`, `evaluation.gates` | Approved Word checksum and all 198 requirement/use-case IDs matched. OpenAPI v1, import boundaries and the unchanged synthetic golden gate passed. |

Local Python 3.12 results: 215 backend tests and 10 HTTP tests passed. Ruff lint/format and package build passed. Hosted CI on the candidate commit supplies the immutable synthetic profile and job evidence.

## G0 handoff

Attach the candidate hosted CI run and synthetic profile. Keep G0 on HOLD until Tech Lead and QA complete independent review, including the authorized baseline source and real PDF/BGE-M3/provider profile. For the live run, use an approved fixture and a dedicated environment with a pinned model and bounded provider budget, then record clean SHA, fixture and environment hashes, cold/warm definitions, and redacted timings as described in [R1 evidence](README.md).

WP-09 may proceed in parallel with the source permission ledger and reviewer assignment. The existing [private evaluation workflow](../../../evaluation/live/README.md) covers preparation and blinded review. Gold labels and holdout approval are G3 evidence.
