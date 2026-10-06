"""Timezone-aware updated_at for all persistent records."""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
TABLES = [
    "experiments",
    "agent_events",
    "sessions",
    "password_resets",
    "audit_logs",
    "chat_messages",
    "datasets",
    "dataset_profiles",
    "model_artifacts",
    "improvement_steps",
    "prediction_logs",
]


def upgrade():
    for name in TABLES:
        op.add_column(
            name,
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )


def downgrade():
    for name in reversed(TABLES):
        op.drop_column(name, "updated_at")
