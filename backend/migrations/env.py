"""Explicit migrations; do not load .env or print connection URLs."""

from alembic import context

from src.db.database import Base, engine
from src.db import models  # noqa: F401: register models for metadata comparison

target_metadata = Base.metadata

if context.is_offline_mode():
    context.configure(
        url=engine.url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
