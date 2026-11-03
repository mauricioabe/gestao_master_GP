"""Hierarquia de tarefas e subtarefas na EAP.

Revision ID: 0006_activity_hierarchy
Revises: 0005_activity_progress
"""
from alembic import op
import sqlalchemy as sa


revision = "0006_activity_hierarchy"
down_revision = "0005_activity_progress"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("activities", sa.Column("parent_id", sa.Integer(), nullable=True))
    op.create_index("ix_activities_parent_id", "activities", ["parent_id"])
    op.create_foreign_key(
        "fk_activities_parent_id",
        "activities",
        "activities",
        ["parent_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_activities_parent_id", "activities", type_="foreignkey")
    op.drop_index("ix_activities_parent_id", table_name="activities")
    op.drop_column("activities", "parent_id")
