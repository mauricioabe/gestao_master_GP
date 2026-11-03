"""Situacao da entrega nas atividades.

Revision ID: 0011_activity_delivery_status
Revises: 0010_activity_financial_values
"""
from alembic import op
import sqlalchemy as sa


revision = "0011_activity_delivery_status"
down_revision = "0010_activity_financial_values"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "activities",
        sa.Column("delivery_status", sa.String(length=20), nullable=False, server_default="EM_PLANEJAMENTO"),
    )
    op.create_index("ix_activities_delivery_status", "activities", ["delivery_status"])
    op.execute("UPDATE activities SET delivery_status = CASE WHEN execution_percentage = 100 THEN 'ENCERRADA' WHEN execution_percentage > 0 THEN 'EM_EXECUCAO' ELSE 'EM_PLANEJAMENTO' END")


def downgrade() -> None:
    op.drop_index("ix_activities_delivery_status", table_name="activities")
    op.drop_column("activities", "delivery_status")
