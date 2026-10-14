from sqlalchemy import inspect, text

from study_supporter.infrastructure.persistence.sqlalchemy.database import Base, default_database
from study_supporter.infrastructure.persistence.sqlalchemy import models  # noqa: F401


def verify_schema(database=None) -> None:
    """Read-only readiness. Application imports never create or alter tables."""
    engine = (database or default_database()).engine
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if not set(Base.metadata.tables) <= tables or "alembic_version" not in tables:
        raise RuntimeError("Database requires reviewed Alembic migrations")
    with engine.connect() as connection:
        if connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all() != [
            "p0_0001"
        ]:
            raise RuntimeError("Database revision does not match application baseline")
    for name, table in Base.metadata.tables.items():
        columns = {column["name"] for column in inspector.get_columns(name)}
        if not set(table.columns.keys()) <= columns:
            raise RuntimeError("Database schema does not match the baseline")
