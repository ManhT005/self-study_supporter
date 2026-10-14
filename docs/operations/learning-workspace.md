# Learning workspace operations

Next.js/FastAPI is an additive document-first preview. Legacy Streamlit and its
Compose configuration remain available for regression and rollback. Preview
volumes are separate from all existing app volumes.

## Local development

Use Node 24.12.0 (`.nvmrc`) and the repository's Python environment.

```powershell
.venv/Scripts/python -m pip install -r requirements/dev.txt -r requirements/api.txt
.venv/Scripts/python -m pip install --no-build-isolation --no-deps -e ./backend
npm --prefix apps/web ci
```

For actual embedding/Chroma/provider execution, install `requirements/runtime.txt`.
Use a separate migrated database and Chroma path, never a directory being written
by Streamlit. In the API terminal:

```powershell
$env:DATABASE_URL = 'sqlite:///data/workspace-dev.db'
$env:CHROMA_PATH = 'data/workspace-chroma'
$env:WEB_ORIGIN = 'http://localhost:3000'
$env:API_SECURE_COOKIE = 'false' # local HTTP only
.venv/Scripts/python -m alembic -c backend/alembic.ini upgrade head
.venv/Scripts/python -m uvicorn apps.api.app.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-proxy-headers
```

In another terminal, run `npm --prefix apps/web run dev`. Web proxies same-origin
`/api` to server-only `API_ORIGIN` (default `http://127.0.0.1:8000`). Keep provider
keys out of `NEXT_PUBLIC_*`. HTTPS requires `API_SECURE_COOKIE=true` and the exact
public `WEB_ORIGIN`. API `/docs` exposes OpenAPI on the internal port.

## Isolated Docker preview

```powershell
Copy-Item config/workspace.env.example .env.workspace
# Edit .env.workspace: private WORKSPACE_DB_PASSWORD and provider settings.
docker compose -f compose.workspace.yaml --env-file .env.workspace up -d --build --wait
```

Only web is published. Migration finishes before API startup. Health checks inspect
SQL schema without downloading an embedding model. Models load at first use. The
preview owns `workspace_postgres`, `workspace_data`, `workspace_hf_cache`; it never
mounts `app_data`, `postgres_data`, `hf_cache`. Original `compose.yaml` still runs
Streamlit. Stop without deleting volumes using:

```powershell
docker compose -f compose.workspace.yaml --env-file .env.workspace down
```

## Validation

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
Set-Location apps/web
npx playwright install chromium
npm run test:e2e
```

Regenerate HTTP contracts with `python -m scripts.export_http_contract` then
`npm --prefix apps/web run api:types`. Check them into the same API change.

Browser tests launch production web and a test-only HTTP factory on ports 3000/8000.
They exercise real PDF parsing, SQL persistence, use cases and HTTP cookies, with
deterministic AI/vector doubles. Screenshots go to `docs/design/ui-v1/screenshots`.
Container smoke checks validate real SQL/Chroma separately. Neither establishes
real-provider answer quality.

## Limits and cutover gates

Run one API worker. Auth and unfinished quizzes use bounded expiring process memory;
restart logs users out. Quiz summaries persist in SQL. Ingestion is synchronous,
one active job; keep the upload page open until completion. API startup marks
interrupted processing records failed; uploading the same PDF retries safely using
the existing hash policy. Original PDF bytes are not persisted: the reader shows
indexed text with real page bounds. Writes require exact Origin. Foreign resources
return 404. API errors contain `code/message/request_id` without secrets/tracebacks.

Before production cutover: validate real providers/models and old data on restored
copies, rehearse PostgreSQL/Chroma backup/restore and traffic rollback, review
screenshots and check touch/keyboard behavior on a physical phone. Never enable two
writers on the same Chroma path. Keep Streamlit and production volumes until all
playbook gates pass. See [validation record](../design/ui-v1/VALIDATION.md).
