# Phase 6 — Production Hardening, Observability & Release

**Estimate:** 1–2 weeks plus acceptance/soak buffer · **Prerequisites:** core graph, retrieval benchmark and durable memory gates.
**Objective:** demonstrably safe, observable and recoverable release. A green unit suite alone is not production readiness.

## 1. Production deployment target and non-goals

**Existing:** Next.js/FastAPI preview with CI and isolated Docker Compose, legacy Streamlit rollback, Postgres/Chroma persistence and BGE-M3 lazy loading. **Do not replace all infrastructure with Kubernetes or microservices** for a student/small-team project. Start with a documented single-deployment service topology and explicit capacity limits.

**Not automatically included:** full-scale multi-tenant SaaS, billing, mobile native apps, OCR ingestion, model fine-tuning, dedicated GPU serving, distributed job queue, multi-worker write scaling. Each requires separate evidence/ADR and budget.

**Supported initial topology (proposed):** web → API (1 worker initially) → SQL/Chroma → model provider/Ollama; optional isolated worker only after persistent queues and idempotent ingestion exist. Keep `compose.workspace.yaml` isolated from legacy volumes through early beta; stage a restore copy of real historical data for cutover tests.

## 2. Observability contract

Trace a single request end-to-end via `trace_id` and `request_id`; redact user content by default. OpenTelemetry or LangSmith may be selected after privacy/hosting decision; a vendor-specific tracing SDK must live in instrumentation adapters, not domain code.

| Signal | Capture | Never capture by default |
|---|---|---|
| API | route, status, latency, auth_scope_hash, request size, trace ID | session cookie, password, raw prompt |
| Agent | variant, graph/node ID, run duration, step count, tool name/status, retry reason | raw chain-of-thought, full notes |
| Retrieval | strategy, candidate count, authorized document count, rank time, evidence count, grades | full document text in shared logs |
| LLM | provider/model ID, request duration, token usage when supplied, error type, budget | API keys, private prompt/system secrets |
| Data | checkpoint age, state version, failed resume, SQL pool saturation | user IDs in shared analytics if avoidable |
| Quality | dataset version, eval score and failure category, regression delta | private gold labels / raw PDF |

**SLO candidates, to verify with load tests:** availability ≥99% in defined demo window; p95 tutor ≤15s using a declared test model/hardware and normal input; p95 read-only retrieval ≤2s for warm index; 429 for overload with Retry-After; memory growth stable over 1h soak; error responses with `trace_id` and no private details. These are planning targets, not verified SLOs.

## 3. Safety and resilience work packages

### HR-01 — Budget and admission control

- Overall request deadline, per-model/tool timeout, graph recursion limit, tool-call cap, retrieved-context token cap, note length and PDF upload size.
- Bounded concurrency separate for CPU embeddings, retriever, external LLM and live streaming; reuse existing `BoundedSemaphore` as MVP and ensure no global-user coupling.
- Rate-limit at principal + endpoint + IP with predictable 429, no accidental DOS from nested query retries.
- Decide deterministic retry class (`429`,`5xx`, transient network) and non-retry class (auth, validation, wrong model capability). Exponential backoff with jitter within total deadline; do not retry unsafe writes without receipt.
- Request cancellation on disconnected client; ensure already-started side effects are transactional/idempotent and health routes remain responsive.

### HR-02 — Auth, tenant isolation, prompt injection

- No user-provided `user_id` controls ownership. Verify every retrieved chunk, note, plan, run and checkpoint against authenticated scope.
- PDF and user notes are untrusted data. Isolate from developer instructions and do not let retrieved text initiate save/delete calls.
- Restrict tool registry; no arbitrary tool function names, SQL interpolation, local file access, remote URL fetch or arbitrary code execution.
- No `Thought` or scratchpad returned to Next.js; use redacted activity events only.
- Keep CSRF/Origin/cookie flags, request-size limits, invalid MIME handling and protected endpoints consistent with existing FastAPI adapter.
- Dependency scanning, secret scanning, lockfile/SBOM checks and security patch cadence; no `.env` in Docker images or Git history.

### HR-03 — Data backup, migration, recovery

- Backup SQL, Chroma and key configs as a consistent snapshot. Document restore steps and verify *historical* documents/quiz/notes/citations in staging.
- Before migration: Alembic autogenerate review, drift check and migration rehearsal on copies. No destructive schema change to legacy `QuizAttempt.user_id` or BGE-M3/1024D vectors.
- Restart/rollback drills: API restart, model timeout, database outage, invalid checkpoint, Chroma unavailable, interruption during quiz submission, missing model cache.
- Streamlit rollback remains until original-data replay, real-provider comparison and maintainer signoff complete. Feature-flag rollback is first line; full traffic rollback requires compatibility proof.

### HR-04 — Offline CI and staged model evaluation

- **Fast PR gate:** Ruff, import boundaries, Pydantic contract tests, agent graph unit+golden transitions, API tests, Next.js lint/types/unit, OpenAPI snapshot, E2E smoke with deterministic model/retriever.
- **Integration gate:** PostgreSQL/Chroma isolated service tests, checkpoint resume, migration upgrade/check, idempotency, A/B isolation, Docker build/smoke, ownership.
- **Nightly/manual research gate:** versioned 120-case benchmark, provider/model matrix, quality/citation, p95 and budget trend, evaluators/repeated runs and model memory.
- **Release gate:** staging restore with real historical data, one real provider or declared local model, mobile physical-device sanity, security review, failure/rollback drill, human approval.
- Normal PRs must not depend on paid cloud credits or full BGE model downloads if deterministic tests are possible; record the separately executed model benchmark SHA.

## 4. Operational commands (adapt to current checked-out branch)

Current repository offers these scripts per docs. Re-run after changes and save log/commit evidence:

```powershell
.venv/Scripts/python -m pytest backend/tests/unit backend/tests/contract apps/api/tests -q
.venv/Scripts/ruff check .
.venv/Scripts/ruff format --check .
.venv/Scripts/python scripts/check_import_boundaries.py
.venv/Scripts/python -m scripts.export_http_contract --check
npm --prefix apps/web run lint
npm --prefix apps/web run typecheck
npm --prefix apps/web test
npm --prefix apps/web run build
# E2E needs its test HTTP API and browser fixtures; use the existing Playwright config:
npm --prefix apps/web run test:e2e
```

For Docker preview, use `compose.workspace.yaml` and `config/workspace.env.example`, never run `docker compose down -v` against existing data. See `docs/operations/learning-workspace.md` for exact startup and environment requirements.

**Proposed extra commands (not yet implemented):**

```powershell
python -m evaluation.runner_v2 --dataset evaluation/datasets/v1 --variant legacy_react --offline
python -m evaluation.runner_v2 --dataset evaluation/datasets/v1 --variant langgraph --online --model <approved_model>
python -m scripts.smoke_agent_contract --variant langgraph
python -m scripts.verify_checkpoint_restore --fixture synthetic
```

Do not copy the proposed commands into CI until corresponding scripts exist and the model/fixture profile is documented.

## 5. Release checklist

### Must pass (Go/No-Go)

- [ ] Every phase's exit gate has a dated report with branch, SHA, test output, sample size and reviewer.
- [ ] All secrets/logs/cookie configuration reviewed; cross-user attack suite passed.
- [ ] Tool schema / citation / quiz correctness and controlled errors passed on frozen gold set.
- [ ] Performance/cost within agreed bounds on declared hardware/model and concurrency.
- [ ] No unexpected SQL/Chroma schema or vector change; restored historical data still works.
- [ ] Checkpoint can be resumed after restart and authenticated thread ownership rechecked.
- [ ] CI green on target branch, clean containers run, full browser E2E and real-provider smoke passed.
- [ ] Backup + restore + traffic rollback rehearsed, validated by a second reviewer.
- [ ] Clear release notes: capabilities, known limitations, model dependency and user data policy.

### Rollout sequence

1. Dry-run staging with restored/copied data and blocked external write effects.
2. Enable LangChain POC/graph for dedicated internal test accounts, not for all users.
3. Canary 5% → 25% → 100% *only if enough active users and telemetry exist*; otherwise explicit human-verified cohort progression, no pretend percentages.
4. At each step, compare `error_rate`, `citation_validity`, `quiz_invalid`, latency and CPU/RAM. Abort on scope violation or unsupported claims with fabricated sources.
5. Rollback `AI_ORCHESTRATOR=legacy` / `RAG_STRATEGY=hybrid_legacy`, or switch traffic to legacy preview per tested runbook; retain artifacts for root cause.

## 6. Required runbooks and evidence

Create/update:

```text
docs/operations/ai-agent-runbook.md       # flags, provider fallback, quotas, alerts
docs/operations/ai-backup-restore.md      # SQL/Chroma/checkpoints, consistent snapshot
docs/operations/ai-incident-response.md   # P0 incident handling / rollback
docs/reports/ai-eval/<run>-quality.md      # model, dataset, stats and confidence interval
docs/reports/release-candidate-v1.md      # acceptance signatures and limitations
```

**Exit:** release-tag candidate approved by maintainer; no hidden manual steps and no safety regression. **Do not tag/deploy solely because tests in a document say “pass”.**
