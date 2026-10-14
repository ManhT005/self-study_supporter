# Phase 5 — Memory, Checkpointing and Persistence

**Estimate:** 1–2 weeks (may extend if DB/concurrency design changes) · **Prerequisites:** state contracts, thread policy, identity tests, backup.
**Goal:** authorized continuity over sessions/restarts, not unbounded collection of learner information.

## 1. Memory taxonomy and ownership

| State | Lifecycle | Proposed store | Owner and access |
|---|---|---|---|
| Request scratch / work | One graph invocation | In-memory transient | server request only; not user-visible thought |
| Thread checkpoint | Multi-step graph run, interrupt/resume | LangGraph PostgreSQL saver **via scoped repository/adapter** | `(user_id, thread_id)` + version |
| Conversation summary | Across turns of an owned thread | PostgreSQL or compact checkpoint reference | authenticated thread owner |
| Notes explicitly saved | Long-term | preserve existing Chroma user-memory collection + SQL metadata only if needed | authenticated account; edit/delete |
| Progress / attempts | Long-term canonical grade facts | Existing PostgreSQL repository | authenticated account; idempotent grading |
| Mastery estimation | Derived profile, versioned | additive SQL table/view or computed projection | authenticated account; recalculable |
| Learning plan | Explicitly accepted proposal | new additive SQL records | owner + optimistic version, no automatic write |

**Do not conflate** agent scratchpad with learner memory. No “automatic remember everything”; persist only necessary facts with explicit product policy. Do not write raw hidden model reasoning or whole uploaded PDF text to checkpoints.

## 2. Existing constraints to address

- `apps/api/app/main.py` uses expiring **process-memory** auth sessions. `apps/api/app/learning.py` and `apps/api/app/quizzes.py` keep unfinished quiz state in-memory. Production documentation permits one API worker and states that restart logs users out.
- Existing quiz attempts and some learning artifacts survive in SQL; historic `QuizAttempt.user_id` is a **string**. Preserve schema compatibility and migrate only with careful Alembic checks.
- `Chroma` collections use legacy `documents_<id>` and `user_memory`; vector dimension 1024. **No destructive reset or implicit re-embed.**
- Backend ingestion uses process-local locking; multi-worker uniqueness still needs a separate transaction/lock design.

**Important:** Graph checkpoint persistence does *not* fix HTTP authentication, in-flight ingestion, or unfinished quiz storage by itself. Treat these as distinct persistence lanes.

## 3. Phase implementation sequence

### MP-01 — Namespace and thread authorization policy

- Generate opaque server-owned `thread_id`; map it to owner in an authorized SQL table or equivalent ownership registry. Do not rely on predictable concatenation of `user_id` into caller-controlled thread IDs.
- `thread_id` used for checkpoint lookup is validated against authenticated account on **read, update, resume, delete, export**. If graph config includes `thread_id`, server populates from the validated mapping, never accepts it as sufficient proof of access.
- Scope active document IDs; on resume re-check they still exist, are owned and indexed READY.
- Version checkpoints (`graph_version`, `state_schema_version`, `provider_version`) and reject or migrate unsupported historical states gracefully.

### MP-02 — PostgreSQL checkpoint adapter

- Evaluate maintained `langgraph-checkpoint-postgres` or current supported package and select one after compatibility spike. Keep adapter-specific imports in `infrastructure/checkpointing/` or `orchestration/langgraph_core/persistence.py` and wire via `bootstrap.py`.
- Use **separate test schema/database** for fixtures; production migrations must be additive, reversible by backup, reviewed for locks/indexes and no breaking changes to the legacy tables.
- Each graph invocation/interrupt has an idempotency key, trace ID, bounded lifetime and deadline. Re-entrant tool calls must not repeat notes, quiz submissions or accepted plans.
- Durable interrupt/resume requires a checkpointer and revalidation after resume. Use human-in-the-loop approval for plan writes or autonomous note saves; if approval unavailable, return a draft and stop safely.
- Verify connection cleanup, rollback on crash and transaction boundary between checkpoint and external side-effect. Prefer outbox/receipt records when exactly-once effects cannot be guaranteed by DB transaction alone.

### MP-03 — Learner profile and mastery estimation

Proposed explainable `mastery_score` in `[0,1]` from validated quiz attempt history and concept mapping; separate `confidence` based on volume/recency. MVP formula to test, **not validated psychometrics**:

```text
For concept c:
  observed = weighted_mean(valid graded responses tagged with c)
  mastery(c) = shrinkage(observed, neutral_prior=0.5, strength=3)
  confidence(c) = min(1, attempts(c) / 8)
  review_due(c) = conservative rule based on last_attempt + repeated errors
```

Every update stores computation version, provenance (`attempt_id`s), timestamp and concept taxonomy version. Do not hallucinate mastery for topics with no labeled attempts. Provide recomputation job and comparison to simple accuracy baseline. Spaced repetition/knowledge tracing models (BKT, DKT) are optional experiments after sufficient empirical data.

### MP-04 — Privacy and user controls

- Note **consent/intent**: explicit Save Note button or confirmed agent action; no automatic profiling from arbitrary conversation. A user can inspect, edit and delete saved notes and learning plans.
- Retention proposal: transient trace payload ≤7 days, checkpoints ≤30 days after last activity unless active plan needs longer; aggregated non-PII metrics longer. Final retention must be approved by product/data policy, not baked into schema prematurely.
- Sanitize notes, apply size limit and prompt-injection handling; text from documents/notes is *data*, not system instructions.
- Define data export/deletion across PostgreSQL checkpoints, notes/Chroma and cached derived summaries; deletion needs a tested cascade/runbook and tombstones where physical delete is asynchronous.
- Multi-tenant isolation at SQL/Chroma/retrieval/cache levels, with fixtures A/B and logged owner-scope failures (no sensitive content in audit events).

### MP-05 — API and frontend continuity

- Add endpoints conceptually: `GET /api/v1/threads`, `GET /threads/{id}`, `POST /threads/{id}/resume`, `DELETE /threads/{id}`, plus typed progress/mastery and plan approval DTOs. Follow existing API `/api/v1` style and same-origin cookie auth, Origin validation and generated TS contract.
- Browser resumes via authorized thread list, not local storage of agent state. UI must differentiate `processing`, `needs_approval`, `completed`, `expired`, `failed` and `recovery_required`.
- Auth session store: decide between durable rotating sessions in Redis/PostgreSQL or explicit re-auth after restart. **If durable auth not delivered, show that limitation**; do not claim end-to-end resume without login.
- Unfinished quizzes: store immutable quiz ID, protected answer keys and generation version server-side with TTL (SQL for durable resumable quiz). Never trust a browser-submitted correct answer index.

## 4. Schema migration sketch (proposal; subject to ADR)

```text
agent_threads (id uuid, user_id FK/typed-compatible, status, graph_version,
               active_document_ids, created_at, updated_at, expires_at)
agent_run_receipts (request_key unique per owner, thread_id, effect_type, effect_id,
                    outcome, created_at)
learning_plans (id, user_id, version, proposed_json, approved_at nullable, status)
concept_mastery (user_id, concept_id, taxonomy_version, score, confidence,
                 computed_at, evidence_version)
```

Take care with real `User.id` integer and legacy `QuizAttempt.user_id` string: use explicit normalizing adapters/foreign keys appropriate to the existing schema instead of pretending all IDs already share one type. Have a migration SQL review and backup/restore trial.

## 5. Restart and adversarial test suite

| ID | Scenario | Expected |
|---|---|---|
| MP-T01 | Start graph, checkpoint, restart API, re-login if required, resume | thread state continues correctly |
| MP-T02 | Account B guesses A's thread ID | 404/403 with no metadata or state |
| MP-T03 | A deletes document while thread paused | resume blocked; no foreign or stale citation |
| MP-T04 | Retry `save_note` or quiz submission after timeout | one business effect, same receipt |
| MP-T05 | Interrupt before/after write edge | no duplicate side-effect |
| MP-T06 | Old checkpoint graph version | explicit migration/reject with safe error |
| MP-T07 | Delete account/profile | SQL, Chroma and cache scoped records deleted per policy |
| MP-T08 | Parallel threads same user | no state cross-contamination |
| MP-T09 | Progress recomputation | deterministic given versioned historical attempts |
| MP-T10 | PostgreSQL outage/restore | checkpoint error surfaced, graceful recovery |
| MP-T11 | Malicious note instruction | no tool or instruction escalation |
| MP-T12 | User lacks approval UI | plan remains draft; no silent write |

## 6. Exit gate

Prove resume on restart against isolated persisted PostgreSQL, validated ownership, separate restored SQL/Chroma, no duplicate effects, idempotent retries, schema migration check and user note deletion. Document whether auth/ingestion/unfinished quiz cross-restart limitations remain. Rollback via disabled feature flag and verified database backup—not by dropping checkpoint tables or deleting legacy volumes.

**Next:** [`05_HARDENING_RELEASE.md`](05_HARDENING_RELEASE.md).
