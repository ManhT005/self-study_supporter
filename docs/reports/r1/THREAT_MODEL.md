# R0 threat model and fault inventory

Status: INITIAL ENGINEERING REVIEW; independent Security/QA review pending. This inventory records the WP-01 baseline at `develop@155fd76` and the targeted WP-02 mitigation.

| Boundary / asset | Threat or failure | Present evidence / known gap | Required mitigation and acceptance |
| --- | --- | --- | --- |
| Learner to API/SQL/vector | Forged resource ID or prompt attempts to select another owner | Owner checks and scoped retrieval contract tests exist; new R1 resources remain unimplemented | AUTH-04, BR-01/02; UAT-03/10 in WP-03/11 |
| PDF/tool observations to agent | Embedded instructions induce a persistent note write | WP-02 removes `SaveNoteTool` from composition and rejects tools that have not opted in as read-only at dispatch | [Adversarial and manual note checks](WP-02_VALIDATION.md); independent review pending |
| API process to session store | Restart/revoke inconsistency or multi-replica rate bypass | In-memory auth and limiter at baseline | WP-03 shared sessions/admission, restart and replica tests; DEC-03 direction recorded, Security/BE review pending |
| Upload to parser/embedding/index | Expensive file, worker death, partial index or missing source | Synchronous ingestion and process locks; no private original/job/index lifecycle | WP-06/07 leases, versioned promotion, source manifests; UAT-04/06/07 |
| Model to quiz/browser/attempts | Invalid quiz, late-chapter omission, answer leakage or duplicate grading | `chunks[:5]`, RAM quiz state, legacy attempt persistence | WP-04/05/12, UAT-12…15; no claim of durable quiz acceptance |
| Retrieval/model to learner | Unsupported answers with plausible citations | Existing structural regression is not independent source-support review | WP-09/11: reviewed gold, holdout, abstention; G3 HOLD |
| Application to diagnostics | Prompt, PDF, user ID, note or error detail leaks | WP-01 emits only fixed operation, random trace/span IDs, elapsed ms and status | Redaction, failure and concurrent-scope tests; inspect profile artifact before sharing |
| Core to n8n/provider | Unverified email, stale consent, replay or ambiguous dispatch | No production reminder flow at baseline | WP-17/18 service auth/outbox/admission/receipt; G6 HOLD |
| Release to historical data | Destructive migration, stale indexes, missing backup | No new schema/index change in WP-01 | WP-20 isolated historical restore/rollback; G7 HOLD |

Avoid raw exception strings in timing data. Telemetry uses an explicit context-local sink and is inactive outside a capture scope; it never changes HTTP DTOs or forwards data externally. Existing legacy logging is outside this instrument's guarantee and needs WP-19 review.
