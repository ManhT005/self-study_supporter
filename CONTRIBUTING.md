# Contributing

Branch from the latest `origin/develop`, use conventional commits and review each
vertical slice separately. Local refactor checkpoints are a dependency stack;
submit/rebase them in plan order after preceding slices merge into develop.
No direct main push or release tag is part of consolidation. Do not commit secrets,
student PDFs, database dumps or model weights.

PowerShell offline gates from repository root:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements/dev.txt
.venv/Scripts/python -m pip install --no-build-isolation --no-deps -e ./backend
.venv/Scripts/python -m pytest -q
.venv/Scripts/ruff check .
.venv/Scripts/ruff format --check .
.venv/Scripts/python scripts/check_import_boundaries.py
.venv/Scripts/python -m build --no-isolation ./backend
```

POSIX substitutes `.venv/bin/`. Supported Python is 3.11–3.12. Default tests use
fakes and never download weights or call cloud providers. Ruff covers canonical
code, apps, migrations, scripts, evaluation and all tests. Public contracts/ports
use explicit types; the architecture gate limits vendor imports to reviewed,
deterministic modules and prohibits SDK/network imports in pure layers.

PostgreSQL integration requires a disposable migrated DB: set `DATABASE_URL` and
`STUDY_TEST_DATABASE_URL`, run Alembic upgrade/check, then
`python -m pytest backend/tests/integration -q`. Missing configuration fails this
suite. Tests add/delete fixture records, so never use retained user data.

Use [Docker smoke/backup commands](docs/operations/docker.md) for runtime changes.
Real-model smoke and [evaluation](evaluation/README.md) are opt-in. Record local
results separately from remote CI and human browser acceptance. Review and the
quality workflow's offline/postgres/docker checks should protect develop/main;
the repository files do not configure GitHub branch protection automatically.
