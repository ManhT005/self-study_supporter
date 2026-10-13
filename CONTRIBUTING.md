# Contributing

Keep PRs small and reversible. Branch from the current foundation branch until it
is merged, then from main. Use conventional commits (`fix`, `refactor`, `infra`,
`ci`, `docs`); each correctness change needs a reproducing test. No direct main pushes
or v1 tags in Phase 0. Never include `.env`, real uploaded PDFs, model weights or keys.

Maintainer should configure branch protection for main: require review and the
`quality` workflow's offline/postgres/docker jobs. This document does not configure
GitHub protection settings; remote enforcement must be verified separately.

PowerShell setup:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m pip install --no-build-isolation --no-deps -e ./backend
.venv/Scripts/python -m pytest -q
.venv/Scripts/ruff check .
.venv/Scripts/ruff format --check .
.venv/Scripts/python scripts/check_import_boundaries.py
.venv/Scripts/python -m build --no-isolation ./backend
```

POSIX: replace `.venv/Scripts/python` with `.venv/bin/python` and
`.venv/Scripts/ruff` with `.venv/bin/ruff`. Python 3.11–3.12 is supported.
Run from repository root. Dev lock provides offline test dependencies; it does not
install Torch/Chroma or download weights. Docker supplies the complete CPU runtime.
Root pytest explicitly selects offline suites; online evaluation scripts are opt-in.

Ruff applies to P0 new/touched code; untouched legacy modules will be brought into
the gate as they are extracted in P1. Current typing policy: annotate new contracts,
ports and public core functions, validate DTOs at runtime; static type checking is
deferred until legacy adapters have typed boundaries.

PostgreSQL integration: create a disposable database, set both DATABASE_URL and
P0_TEST_DATABASE_URL, run Alembic upgrade/check, then
`python -m pytest backend/tests/integration -q`. Missing DB configuration fails this
suite explicitly. Never point it at retained user data.

Full embedding/Ollama/browser smoke is a separate acceptance check with recorded
model/environment metadata. Fast CI must not call cloud LLMs or require GPU access.
See [Docker](docs/operations/docker.md), [migrations](docs/operations/migrations.md)
and [acceptance evidence](docs/reports/p0-acceptance.md).
