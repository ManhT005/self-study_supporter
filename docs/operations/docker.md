# Local Docker operations

Use Python 3.11 in the image, Docker Desktop Linux containers/WSL2 on Windows.
Allocate at least 8 GB RAM and 15 GB free disk for CPU dependencies and BGE weights.
App is capped at 6 GB RAM / 2 CPUs; PostgreSQL and Ollama ports are not published.
Streamlit binds only to `127.0.0.1:8501`. Weights are downloaded on first ingestion,
never during build. Download time depends on bandwidth; BGE-M3 is a large model.

PowerShell:

```powershell
Copy-Item .env.docker.example .env.docker
# Edit POSTGRES_PASSWORD; keep provider keys blank for the local baseline.
docker compose --env-file .env.docker config --quiet
docker compose --env-file .env.docker up -d --build --wait
docker compose --env-file .env.docker ps
Invoke-WebRequest http://localhost:8501/_stcore/health
```

POSIX uses `cp .env.docker.example .env.docker` and
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
No GPU required. Do not open the listener to public networks.

## Backup and isolated restore

For local persistent Chroma only (external Chroma needs its own snapshot). Backups
contain private data; use access controlled/encrypted storage and do not commit them.
The helper stops app writes, dumps SQL and snapshots `/app/data` at the same boundary,
then restarts the app if it was running. A failed backup has no completed manifest.

```powershell
python scripts/docker_backup.py backup data/backups/p0-001 --project-name self-study-supporter
python scripts/docker_backup.py restore data/backups/p0-001 --project-name p0-restore-check
```

Restore refuses the source project and any existing target containers/volumes.
Run functional smoke against restored SQL/Chroma before starting the restored UI.
Set a separate APP_PORT to avoid the original app. Model caches are reproducible,
not part of the snapshot. Restoring old data is never an automatic schema stamp.

## Dependency locks

`requirements.in` pins direct runtime dependencies; `requirements.txt` locks the
Linux/Python 3.11 CPU deployment. `requirements-dev.txt` locks offline test tooling.
Regenerate with uv 0.13.0, review the diff, then clean-build before committing.
The existing `.env`, uploaded data and secrets are excluded by `.dockerignore`.
