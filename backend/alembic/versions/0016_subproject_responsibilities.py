"""Vínculos de gerente civil e responsável militar ao subprojeto."""
from alembic import op
import sqlalchemy as sa

revision = '0016_subproject_responsibilities'
down_revision = '0015_user_military_identity'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('subprojects', 'manager', existing_type=sa.String(140), type_=sa.String(150), existing_nullable=False)
    op.add_column('subprojects', sa.Column('manager_user_id', sa.Integer(), nullable=True))
    op.add_column('subprojects', sa.Column('military_responsible_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_subprojects_manager_user', 'subprojects', 'users', ['manager_user_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key('fk_subprojects_military_responsible', 'subprojects', 'users', ['military_responsible_id'], ['id'], ondelete='RESTRICT')


def downgrade() -> None:
    op.drop_constraint('fk_subprojects_military_responsible', 'subprojects', type_='foreignkey')
    op.drop_constraint('fk_subprojects_manager_user', 'subprojects', type_='foreignkey')
    op.drop_column('subprojects', 'military_responsible_id')
    op.drop_column('subprojects', 'manager_user_id')
    op.alter_column('subprojects', 'manager', existing_type=sa.String(150), type_=sa.String(140), existing_nullable=False)
