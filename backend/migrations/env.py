"""Explicit migration lifecycle; never load dotenv or print credentials."""

import os
from alembic import context
from study_supporter.config import Settings
from study_supporter.infrastructure.persistence.sqlalchemy.database import Base, Database
from study_supporter.infrastructure.persistence.sqlalchemy import models  # noqa: F401

target_metadata = Base.metadata
database = Database(Settings.from_mapping(os.environ))
try:
    if context.is_offline_mode():
        context.configure(
            url=database.engine.url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )
        with context.begin_transaction():
            context.run_migrations()
    else:
        with database.engine.connect() as connection:
            context.configure(
                connection=connection, target_metadata=target_metadata, compare_type=True
            )
            with context.begin_transaction():
                context.run_migrations()
finally:
    database.close()
