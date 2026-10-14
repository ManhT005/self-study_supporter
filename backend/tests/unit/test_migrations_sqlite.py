import subprocess
import sys

from sqlalchemy import create_engine, inspect, text


def migrate(monkeypatch, path, *args, success=True):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{path.as_posix()}")
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", *args],
        capture_output=True,
        text=True,
    )
    assert (result.returncode == 0) == success, result.stderr
    return result


def test_fresh_schema_no_drift_and_idempotent_upgrade(monkeypatch, tmp_path):
    db = tmp_path / "fresh.db"
    migrate(monkeypatch, db, "upgrade", "head")
    migrate(monkeypatch, db, "check")
    engine = create_engine(f"sqlite:///{db.as_posix()}")
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO users (username, password_hash) VALUES ('fixture', 'fixture')")
        )
    migrate(monkeypatch, db, "upgrade", "head")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM users")).scalar() == 1
    result = migrate(monkeypatch, db, "downgrade", "base", success=False)
    assert "Populated baseline cannot be downgraded" in result.stderr
    engine.dispose()


def test_existing_unversioned_schema_refused(monkeypatch, tmp_path):
    db = tmp_path / "existing.db"
    engine = create_engine(f"sqlite:///{db.as_posix()}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO users VALUES (9)"))
    result = migrate(monkeypatch, db, "upgrade", "head", success=False)
    assert "Existing schema detected" in result.stderr
    assert "documents" not in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT id FROM users")).scalar() == 9
    engine.dispose()


def test_empty_downgrade_roundtrip(monkeypatch, tmp_path):
    db = tmp_path / "empty.db"
    migrate(monkeypatch, db, "upgrade", "head")
    migrate(monkeypatch, db, "downgrade", "base")
    migrate(monkeypatch, db, "upgrade", "head")
    migrate(monkeypatch, db, "check")


def test_imports_do_not_connect_or_create_tables(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://unused:unused@127.0.0.1:1/unused")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import study_supporter.infrastructure.persistence.sqlalchemy.auth_repository, study_supporter.infrastructure.persistence.sqlalchemy.document_repository, study_supporter.infrastructure.persistence.sqlalchemy.progress_repository",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
