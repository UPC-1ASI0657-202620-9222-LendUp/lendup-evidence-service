"""Store the generation of each loan closure attempt."""
from alembic import op
import sqlalchemy as sa

revision = "0005_incident_seal_generation"
down_revision = "0004_incident_closures"


def upgrade():
    op.add_column("cierres_incidencias", sa.Column("sello_id", sa.CHAR(36)))


def downgrade():
    op.drop_column("cierres_incidencias", "sello_id")
