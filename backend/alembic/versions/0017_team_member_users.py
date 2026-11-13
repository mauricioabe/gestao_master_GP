"""Integrantes vinculados aos usuários já cadastrados."""
from alembic import op
import sqlalchemy as sa

revision = '0017_team_member_users'
down_revision = '0016_subproject_responsibilities'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('team_members', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_unique_constraint('uq_team_members_user', 'team_members', ['user_id'])
    op.create_foreign_key('fk_team_members_user', 'team_members', 'users', ['user_id'], ['id'], ondelete='RESTRICT')


def downgrade() -> None:
    op.drop_constraint('fk_team_members_user', 'team_members', type_='foreignkey')
    op.drop_constraint('uq_team_members_user', 'team_members', type_='unique')
    op.drop_column('team_members', 'user_id')
