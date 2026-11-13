"""Diário de bordo e integrantes de equipe, sem integração de IA."""
from alembic import op
import sqlalchemy as sa

revision = '0013_logbooks'
down_revision = '0012_users_auth'
branch_labels = None
depends_on = None


def upgrade():
    bigint = sa.BigInteger().with_variant(sa.Integer(), 'sqlite')
    op.create_table('team_members',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('rank', sa.String(60), nullable=False),
        sa.Column('full_name', sa.String(150), nullable=False),
        sa.Column('war_name', sa.String(100), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False))
    op.create_table('logbooks',
        sa.Column('id', bigint, primary_key=True),
        sa.Column('subject_principal', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('scope', sa.String(20), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('registration_date', sa.Date(), nullable=False),
        sa.Column('closure_date', sa.Date()),
        sa.Column('responsible_id', sa.Integer(), sa.ForeignKey('team_members.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('tags', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False))
    op.create_index('ix_logbooks_subject_principal', 'logbooks', ['subject_principal'])
    op.create_index('ix_logbooks_status', 'logbooks', ['status'])
    for table, target, key in [('logbook_projects', 'projects', 'project_id'), ('logbook_subprojects', 'subprojects', 'subproject_id')]:
        op.create_table(table,
            sa.Column('logbook_id', bigint, sa.ForeignKey('logbooks.id', ondelete='CASCADE'), primary_key=True),
            sa.Column(key, sa.Integer(), sa.ForeignKey(f'{target}.id', ondelete='CASCADE'), primary_key=True))
    op.create_table('logbook_items',
        sa.Column('id', bigint, primary_key=True),
        sa.Column('logbook_id', bigint, sa.ForeignKey('logbooks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('event_date', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('type', sa.String(20), nullable=False),
        sa.Column('references_text', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False))
    op.create_index('ix_logbook_items_logbook_id', 'logbook_items', ['logbook_id'])
    op.create_index('ix_logbook_items_event_date', 'logbook_items', ['event_date'])
    op.create_table('logbook_item_attachments',
        sa.Column('id', bigint, primary_key=True),
        sa.Column('item_id', bigint, sa.ForeignKey('logbook_items.id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('stored_name', sa.String(80), nullable=False, unique=True),
        sa.Column('mime_type', sa.String(150), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('description', sa.String(500), nullable=False))
    op.create_index('ix_logbook_item_attachments_item_id', 'logbook_item_attachments', ['item_id'])
    op.create_table('logbook_links',
        sa.Column('id', bigint, primary_key=True),
        sa.Column('source_logbook_id', bigint, sa.ForeignKey('logbooks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_logbook_id', bigint, sa.ForeignKey('logbooks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('link_type', sa.String(30), nullable=False),
        sa.Column('observations', sa.Text(), nullable=False),
        sa.UniqueConstraint('source_logbook_id', 'target_logbook_id', 'link_type', name='uq_logbook_link'))
    for key in ['source_logbook_id', 'target_logbook_id']:
        op.create_index(f'ix_logbook_links_{key}', 'logbook_links', [key])


def downgrade():
    for table in ['logbook_links', 'logbook_item_attachments', 'logbook_items', 'logbook_subprojects', 'logbook_projects', 'logbooks', 'team_members']:
        op.drop_table(table)
