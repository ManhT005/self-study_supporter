"""Fresh database baseline. Existing databases need reviewed adoption."""

from alembic import op
import sqlalchemy as sa

revision = "p0_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    if not op.get_context().as_sql:
        tables = set(sa.inspect(op.get_bind()).get_table_names())
        if tables & {"users", "documents", "quiz_attempts"}:
            raise RuntimeError(
                "Existing schema detected: backup and inspect before manual adoption; automatic stamp is forbidden"
            )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("file_hash", sa.String(), nullable=True),
        sa.Column("chroma_collection_name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=True),
        sa.Column("concept_graph_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])
    op.create_index("ix_documents_file_hash", "documents", ["file_hash"])
    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # Preserve historical string user IDs; conversion requires a separate backfill.
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("topic", sa.String(), nullable=False),
        sa.Column("question", sa.String(), nullable=False),
        sa.Column("is_correct", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_quiz_attempts_user_id", "quiz_attempts", ["user_id"])


def downgrade():
    if op.get_context().as_sql:
        raise RuntimeError("Offline destructive downgrade is not supported")
    for table in ["users", "documents", "quiz_attempts"]:
        if op.get_bind().execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar():
            raise RuntimeError(
                "Populated baseline cannot be downgraded; restore a verified backup instead"
            )
    for table in ["quiz_attempts", "documents", "users"]:
        op.drop_table(table)
