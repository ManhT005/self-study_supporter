# Docker Local Foundation & Parallel Development Plan

This branch packages the **existing Streamlit implementation** before the FastAPI + Next.js redesign. It is not yet a public-production release.

Phase 0 continuation: use [current Docker operations](operations/docker.md),
[migration instructions](operations/migrations.md), and [executed evidence](reports/p0-acceptance.md).
The app now receives separate PostgreSQL fields (reserved password characters work),
and a one-shot Alembic service runs before app startup. Existing schemas require reviewed adoption.

## Start (Windows PowerShell)

```powershell
git fetch origin
git switch feature/docker-local-foundation
Copy-Item .env.docker.example .env.docker
# Edit .env.docker; replace POSTGRES_PASSWORD with a strong password.
docker compose --env-file .env.docker config --quiet
docker compose --env-file .env.docker up -d --build
docker compose --env-file .env.docker ps
docker compose --env-file .env.docker logs --tail=100 -f app
```

Open http://localhost:8501. The image may download a large local BGE-M3 embedding model on first use. Default execution is CPU-based.

### Container layout

- `app`: Streamlit / existing AI Core, port 8501 on host loopback only.
- `db`: PostgreSQL 16, isolated from the host network.
- `app_data`: durable local embedded Chroma vector store and app files.
- `hf_cache`: durable Hugging Face model cache.
- `ollama` (optional): CPU Ollama container with `ollama_data` volume.

This does not migrate data from existing Supabase/Postgres services.

### Ollama hosted on Windows

Default `OLLAMA_BASE_URL=http://host.docker.internal:11434`. On Windows, confirm the Ollama HTTP listener can accept connections from Docker Desktop and is not exposed to untrusted networks. Install model via `ollama pull qwen2.5:1.5b`. Check connectivity:

```powershell
docker compose --env-file .env.docker exec app python -c "import os,requests; r=requests.get(os.environ['OLLAMA_BASE_URL']+'/api/tags',timeout=10); print(r.status_code); r.raise_for_status()"
```

### Ollama fully inside Compose

Edit `.env.docker`: `OLLAMA_BASE_URL=http://ollama:11434`. Then:

```powershell
docker compose --env-file .env.docker --profile local-ai up -d --build
docker compose --env-file .env.docker --profile local-ai exec ollama ollama pull qwen2.5:1.5b
docker compose --env-file .env.docker --profile local-ai restart app
```

Avoid launching the local-ai profile without setting `OLLAMA_BASE_URL`.

### Operational commands

```powershell
docker compose --env-file .env.docker ps
docker compose --env-file .env.docker logs -f app
docker compose --env-file .env.docker down
docker compose --env-file .env.docker up -d --build
```

**Do not use `docker compose down -v` if you need the data.** Named volumes are persistent, but you need backups of **both** PostgreSQL and Chroma data for consistent recovery.

## Limits & release gates

- Docker build and full E2E smoke tests must still be run on a Docker-enabled machine. The code has not been verified in a running container here.
- SQLAlchemy `create_all()` only creates missing tables; adopt Alembic migrations before release.
- Existing Streamlit session/auth isolation and quiz parsing need hardening.
- Pin Python dependencies and container image versions after a reproducible build.
- Secrets must be kept in `.env.docker`, never embedded in images or committed.
- The existing application is synchronous during document ingestion; moving to workers requires first extracting the ingestion use case from Streamlit.
- Do not expose this stack to the public Internet without auth, security, backup and reverse-proxy hardening.

## Parallel project streams

| Stream | Branch idea | Safe to develop alongside Docker? | Deliverable |
| --- | --- | --- | --- |
| Infrastructure | `feature/docker-local-foundation` | Yes | Compose, persistence, boot smoke |
| AI Core extraction | `refactor/ai-core-isolation` | Yes | Pure Python use cases and interfaces |
| Frontend redesign | `feature/ui-learning-workspace` | Yes | Next.js design system and mock data |
| LangGraph orchestration | `feature/langgraph-orchestration` | Yes, after interfaces freeze | Tutor/Quiz/Planner graphs |
| RAG experiments | `research/adaptive-rag-benchmark` | Yes | Golden dataset and ablation scores |
| Application API | `feature/study-api-contract` | Yes, with contract ownership | FastAPI auth/docs/chat/quiz endpoints |

Merge sequencing: infrastructure and core contracts first; then API/Agent integration; then frontend E2E. Avoid parallel modifications of `main.py` and `ui/components/sidebar.py` in independent branches.

## Minimal acceptance checks

1. `docker compose --env-file .env.docker config --quiet` passes.
2. `docker compose ... up -d --build` succeeds with no hardcoded secrets.
3. `db` reports healthy and `app` responds on `/_stcore/health`.
4. User can register, sign in and upload a sample PDF with a valid supported embedding model.
5. Quiz result and uploaded document remain available after `docker compose down` / `up -d`.
6. Ollama connectivity works using the configured endpoint (if selected).
7. User B cannot access user A data, including after A logs out in the same browser session.
8. Data backup/restore and application/DB upgrade are verified before public release.
