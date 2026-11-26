"""Create transactional event outbox."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME

revision = "0002_event_outbox"
down_revision = "0001_evidence_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("aggregate_id", sa.CHAR(36), nullable=False),
        sa.Column("aggregate_version", sa.Integer(), nullable=False),
        sa.Column("routing_key", sa.String(150), nullable=False),
        sa.Column("envelope", sa.JSON(), nullable=False),
        sa.Column("mandatory", sa.Boolean(), nullable=False),
        sa.Column("created_at", DATETIME(fsp=6), nullable=False),
        sa.Column("next_attempt_at", DATETIME(fsp=6), nullable=False),
        sa.Column("published_at", DATETIME(fsp=6)),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(255)),
        sa.UniqueConstraint("aggregate_id", "aggregate_version", name="uq_outbox_aggregate_version"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    op.create_index("idx_outbox_pending", "outbox_events", ["published_at", "next_attempt_at"])


def downgrade():
    op.drop_table("outbox_events")
