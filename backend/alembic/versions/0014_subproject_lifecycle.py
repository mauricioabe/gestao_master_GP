"""Ciclo de vida dos subprojetos."""
from alembic import op
import sqlalchemy as sa

revision = '0014_subproject_lifecycle'
down_revision = '0013_logbooks'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing subprojects remain unclassified until explicitly edited.
    op.add_column('subprojects', sa.Column('lifecycle_stage', sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column('subprojects', 'lifecycle_stage')
