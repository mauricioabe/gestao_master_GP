"""Contratos do Radar Financeiro vinculados a subprojetos.

Revision ID: 0008_subproject_contracts
Revises: 0007_separate_schedules
"""
from alembic import op
import sqlalchemy as sa


revision = "0008_subproject_contracts"
down_revision = "0007_separate_schedules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subproject_contracts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subproject_id", sa.Integer(), sa.ForeignKey("subprojects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_contract_id", sa.String(length=60), nullable=False),
        sa.Column("contract_number", sa.String(length=50), nullable=True),
        sa.Column("contract_object", sa.Text(), nullable=True),
        sa.Column("supplier_name", sa.String(length=255), nullable=True),
        sa.Column("global_value", sa.Numeric(18, 2), nullable=True),
        sa.Column("linked_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("subproject_id", "external_contract_id", name="uq_subproject_contracts_contract"),
    )
    op.create_index("ix_subproject_contracts_subproject_id", "subproject_contracts", ["subproject_id"])
    op.create_index("ix_subproject_contracts_external_contract_id", "subproject_contracts", ["external_contract_id"])


def downgrade() -> None:
    op.drop_table("subproject_contracts")
