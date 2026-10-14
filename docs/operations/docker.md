# Local Docker operations

Use Python 3.11 in the image, Docker Desktop Linux containers/WSL2 on Windows.
Allocate at least 8 GB RAM and 15 GB free disk for CPU dependencies and BGE weights.
App is capped at 6 GB RAM / 2 CPUs; PostgreSQL and Ollama ports are not published.
Streamlit binds only to `127.0.0.1:8501`. Weights are downloaded on first ingestion,
never during build. Download time depends on bandwidth; BGE-M3 is a large model.

PowerShell:

```powershell
Copy-Item config/docker.env.example .env.docker
# Edit POSTGRES_PASSWORD; keep provider keys blank for the local baseline.
docker compose --env-file .env.docker config --quiet
docker compose --env-file .env.docker up -d --build --wait
docker compose --env-file .env.docker ps
Invoke-WebRequest http://localhost:8501/_stcore/health
```

POSIX uses `cp config/docker.env.example .env.docker` and
`curl --fail http://localhost:8501/_stcore/health`; Compose commands are identical.
Health 200 proves Streamlit liveness, not DB/model readiness. Run functional smoke
separately; offline fake vectors cannot establish BGE model quality or LLM availability.
The DB connection uses SQLAlchemy `URL.create()` so reserved password characters work.

Volumes: `postgres_data` contains SQL, `app_data` contains local Chroma/files,
`hf_cache` contains Hugging Face weights, `ollama_data` contains optional Ollama models.
Use `restart` or `down` then `up`; never use `down -v` for a retained environment.
Do not reuse old Chroma data with a different embedding dimension/model.

## Ollama

Host mode: `OLLAMA_BASE_URL=http://host.docker.internal:11434`. Ensure Docker can
reach the host listener. Container mode: set `http://ollama:11434`, then
`docker compose --env-file .env.docker --profile local-ai up -d`.
Provision explicitly with `docker compose --env-file .env.docker exec ollama ollama pull qwen3:1.7b`.
Set `OLLAMA_MODEL=qwen3:1.7b` in `.env.docker` when using that model and recreate
the app. The preserved UI default is `qwen2.5:1.5b`; it must be installed if you
keep the default. Real-model smoke explicitly selects `qwen3:1.7b`.
No GPU required. Do not open the listener to public networks.

## Backup and isolated restore

For local persistent Chroma only (external Chroma needs its own snapshot). Backups
contain private data; use access controlled/encrypted storage and do not commit them.
The helper stops app writes, dumps SQL and snapshots `/app/data` at the same boundary,
then restarts the app if it was running. A failed backup has no completed manifest.

```powershell
python scripts/docker_backup.py backup data/backups/local-snapshot --project-name self-study-supporter
python scripts/docker_backup.py restore data/backups/local-snapshot --project-name restore-check
```

Restore refuses the source project and any existing target containers/volumes.
Run functional smoke against restored SQL/Chroma before starting the restored UI.
Set a separate APP_PORT to avoid the original app. Model caches are reproducible,
not part of the snapshot. Restoring old data is never an automatic schema stamp.

## Dependency locks

`backend/pyproject.toml` declares direct dependencies; `requirements/runtime.txt` locks the
Linux x86_64/Python 3.11 CPU deployment. `requirements/dev.txt` locks offline test tooling.
See [lock regeneration](../../requirements/README.md); review the diff and rebuild Docker.
The existing `.env`, uploaded data and secrets are excluded by `.dockerignore`.

## Executable smoke commands

Only use synthetic smoke seeding on a disposable dev stack. It adds fixture accounts,
documents and quiz records; the marker refuses accidental repeated seeding.

```powershell
docker compose --env-file .env.docker exec -T app python -m scripts.docker_smoke seed
docker compose --env-file .env.docker exec -T app python -m scripts.docker_smoke verify
docker compose --env-file .env.docker exec -T app python -m scripts.streamlit_smoke
# Optional: downloads BGE-M3 and calls host/container Ollama qwen3:1.7b.
docker compose --env-file .env.docker exec -T app python -m scripts.model_smoke
```

The first suite uses fake 1024D embeddings and a mocked LLM. AppTest executes
Streamlit registration/logout/login. Model smoke uses BGE-M3 and real Ollama in
dedicated fixture accounts. None substitutes for a human browser E2E check or a
retrieval quality benchmark. Results are in [acceptance evidence](../reports/p0-acceptance.md).
