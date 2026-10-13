# Database lifecycle

`src/db/models.py` is the schema source of truth. Alembic revision `p0_0001`
matches the legacy User/Document/QuizAttempt schema. Integer users/documents and
historical string quiz user IDs are intentionally preserved: no unreviewed type
conversion or FK/backfill for legacy quiz identities. New attempts validate the
authenticated user and document ownership in the service.

Fresh database only, from repository root:

```powershell
# Set DATABASE_URL explicitly for the intended database (do not print it).
python -m alembic -c backend/alembic.ini upgrade head
python -m alembic -c backend/alembic.ini check
```

For fresh SQLite without cloud configuration:

```powershell
New-Item -ItemType Directory -Force data | Out-Null
$env:DATABASE_URL = 'sqlite:///data/app.db'
python -m alembic -c backend/alembic.ini upgrade head
```

Compose runs a one-shot `migrate` service after DB health and before app startup.
Imports do not create tables. Streamlit verifies schema explicitly and refuses to
serve an unversioned or mismatched schema. `upgrade head` is idempotent on a DB
already migrated by Alembic. Restart does not rewrite data.

## Existing database adoption

Migration refuses any existing legacy tables without a baseline revision. Stop
writes, backup PostgreSQL/Chroma together, restore into an isolated target, compare
columns, types, nullable flags, indexes and FKs against a fresh migrated reference.
`alembic check` reports differences but is not proof of data semantics or ownership.
Inspect orphan quiz/document rows and historical string IDs. Prepare an explicit
data migration for differences; do not alter tables by importing model modules.

Only after a maintainer approves the specific schema comparison and restore
evidence may an operator manually stamp that verified DB with `p0_0001`.
No application/startup script automatically stamps existing data. Old Supabase
schemas are not universally supported by this baseline.

## Rollback

For an empty disposable DB, `downgrade base` removes the baseline tables.
For a populated DB the downgrade refuses to drop tables. Roll back application
code to the compatible revision or restore a verified synchronized SQL/Chroma
snapshot into an isolated project; never drop retained volumes to resolve errors.
