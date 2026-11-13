"""Equipes de integrantes por projeto e subprojeto."""
from alembic import op
import sqlalchemy as sa

revision = '0018_project_subproject_members'
down_revision = '0017_team_member_users'
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table, parent, key in [('project_members', 'projects', 'project_id'),
                               ('subproject_members', 'subprojects', 'subproject_id')]:
        op.create_table(table,
            sa.Column(key, sa.Integer(), sa.ForeignKey(f'{parent}.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='RESTRICT'), primary_key=True),
            sa.Column('added_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))


def downgrade() -> None:
    op.drop_table('subproject_members')
    op.drop_table('project_members')
