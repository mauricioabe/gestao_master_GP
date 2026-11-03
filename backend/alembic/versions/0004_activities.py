"""Atividades do cronograma dos subprojetos.

Revision ID: 0004_activities
Revises: 0003_subprojects
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_activities"
down_revision = "0003_subprojects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subproject_id", sa.Integer(), nullable=False),
        sa.Column("wbs_code", sa.String(60), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("finish_date", sa.Date(), nullable=False),
        sa.Column("resource_names", sa.Text(), nullable=True),
        sa.Column("predecessor_id", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["subproject_id"], ["subprojects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["predecessor_id"], ["activities.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("subproject_id", "wbs_code", name="uq_activities_subproject_wbs"),
    )
    op.create_index("ix_activities_subproject_id", "activities", ["subproject_id"])
    op.create_index("ix_activities_predecessor_id", "activities", ["predecessor_id"])
    op.create_index("ix_activities_active", "activities", ["active"])


def downgrade() -> None:
    op.drop_table("activities")
