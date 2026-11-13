"""Múltiplos relatores por diário, preservando responsáveis anteriores."""
from alembic import op
import sqlalchemy as sa

revision = '0019_logbook_relators'
down_revision = '0018_project_subproject_members'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bigint = sa.BigInteger().with_variant(sa.Integer(), 'sqlite')
    op.create_table('logbook_relators',
        sa.Column('logbook_id', bigint, sa.ForeignKey('logbooks.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('team_member_id', sa.Integer(), sa.ForeignKey('team_members.id', ondelete='RESTRICT'), primary_key=True))
    op.execute(sa.text('INSERT INTO logbook_relators (logbook_id, team_member_id) SELECT id, responsible_id FROM logbooks'))


def downgrade() -> None:
    op.drop_table('logbook_relators')
