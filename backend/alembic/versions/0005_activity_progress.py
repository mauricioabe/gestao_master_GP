"""Percentual de execucao das atividades.

Revision ID: 0005_activity_progress
Revises: 0004_activities
"""
from alembic import op
import sqlalchemy as sa


revision = "0005_activity_progress"
down_revision = "0004_activities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "activities",
        sa.Column("execution_percentage", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_check_constraint(
        "ck_activities_execution_percentage",
        "activities",
        "execution_percentage BETWEEN 0 AND 100",
    )


def downgrade() -> None:
    op.drop_constraint("ck_activities_execution_percentage", "activities", type_="check")
    op.drop_column("activities", "execution_percentage")
