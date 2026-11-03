"""Valores previsto e realizado das atividades.

Revision ID: 0010_activity_financial_values
Revises: 0009_cff_activity_source
"""
from alembic import op
import sqlalchemy as sa


revision = "0010_activity_financial_values"
down_revision = "0009_cff_activity_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "activities",
        sa.Column("planned_value", sa.Numeric(precision=15, scale=2), nullable=False, server_default="0"),
    )
    op.add_column(
        "activities",
        sa.Column("actual_value", sa.Numeric(precision=15, scale=2), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("activities", "actual_value")
    op.drop_column("activities", "planned_value")
