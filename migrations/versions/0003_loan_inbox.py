"""Create loan projection and transactional inbox."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME

revision = "0003_loan_inbox"
down_revision = "0002_event_outbox"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "inbox_events",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("aggregate_id", sa.CHAR(36), nullable=False),
        sa.Column("aggregate_version", sa.Integer(), nullable=False),
        sa.Column("routing_key", sa.String(150), nullable=False),
        sa.Column("processed_at", DATETIME(fsp=6), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    op.create_table(
        "loan_projection",
        sa.Column("prestamo_id", sa.CHAR(36), primary_key=True),
        sa.Column("reserva_id", sa.CHAR(36), nullable=False),
        sa.Column("publicacion_id", sa.CHAR(36), nullable=False),
        sa.Column("prestamista_usuario_id", sa.CHAR(36), nullable=False),
        sa.Column("prestatario_usuario_id", sa.CHAR(36), nullable=False),
        sa.Column("aggregate_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_event_type", sa.String(64)),
        sa.Column("estado", sa.String(24)),
        sa.Column("state_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("creation_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("garantia_requerida", sa.Boolean()),
        sa.Column("garantia_monetaria_acordada", sa.Numeric(12, 2)),
        sa.Column("moneda", sa.CHAR(3)),
        sa.Column("devolucion_vigente_en", sa.String(40)),
        sa.Column("date_version", sa.Integer(), nullable=False, server_default="0"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )


def downgrade():
    op.drop_table("loan_projection")
    op.drop_table("inbox_events")
