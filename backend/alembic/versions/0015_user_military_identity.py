"""Modalidade civil/militar e identificação dos usuários."""
from alembic import op
import sqlalchemy as sa

revision = '0015_user_military_identity'
down_revision = '0014_subproject_lifecycle'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('person_type', sa.String(10), nullable=False, server_default='CIVIL'))
    op.add_column('users', sa.Column('rank', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('war_name', sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'war_name')
    op.drop_column('users', 'rank')
    op.drop_column('users', 'person_type')
