"""Persistent admission fence for incident reports and loan closure."""

from alembic import op
import sqlalchemy as sa

revision = "0004_incident_closures"
down_revision = "0003_loan_inbox"


def upgrade():
    op.create_table(
        "cierres_incidencias",
        sa.Column("prestamo_id", sa.CHAR(36), primary_key=True),
        sa.Column("sellado", sa.Boolean, nullable=False, server_default=sa.text("0")),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )


def downgrade():
    op.drop_table("cierres_incidencias")
