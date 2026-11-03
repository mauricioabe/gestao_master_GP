"""Rastreabilidade da importacao de etapas do CFF.

Revision ID: 0009_cff_activity_source
Revises: 0008_subproject_contracts
"""
from alembic import op
import sqlalchemy as sa


revision = "0009_cff_activity_source"
down_revision = "0008_subproject_contracts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("activities", sa.Column("source_system", sa.String(length=30), nullable=True))
    op.add_column("activities", sa.Column("source_key", sa.String(length=120), nullable=True))
    op.create_index("ix_activities_source_system", "activities", ["source_system"])
    op.create_unique_constraint(
        "uq_activities_import_source",
        "activities",
        ["subproject_id", "schedule_type", "source_system", "source_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_activities_import_source", "activities", type_="unique")
    op.drop_index("ix_activities_source_system", table_name="activities")
    op.drop_column("activities", "source_key")
    op.drop_column("activities", "source_system")
