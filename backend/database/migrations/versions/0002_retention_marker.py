"""Track payload erasure so bounded cleanup batches make forward progress."""
from alembic import op
import sqlalchemy as sa
revision = '0002_retention_marker'
down_revision = '0001_initial'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('jobs', sa.Column('payload_deleted_at', sa.BigInteger(), nullable=True))

def downgrade():
    op.drop_column('jobs', 'payload_deleted_at')
