"""Estrutura inicial exclusiva de gestao_projetos_sisfron."""
from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("manager", sa.String(140), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PLANEJAMENTO"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="MEDIA"),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("progress BETWEEN 0 AND 100", name="ck_projects_progress"),
        sa.UniqueConstraint("code", name="uq_projects_code"),
    )
    op.create_index("ix_projects_code", "projects", ["code"])
    op.create_index("ix_projects_name", "projects", ["name"])
    op.create_index("ix_projects_status", "projects", ["status"])
    op.create_table(
        "project_contracts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("external_contract_id", sa.String(60), nullable=False),
        sa.Column("contract_number", sa.String(50)),
        sa.Column("contract_object", sa.Text()),
        sa.Column("supplier_name", sa.String(255)),
        sa.Column("global_value", sa.Numeric(18, 2)),
        sa.Column("linked_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("project_id", "external_contract_id", name="uq_project_contract"),
    )
    op.create_index("ix_project_contracts_project_id", "project_contracts", ["project_id"])
    op.create_index("ix_project_contracts_external_id", "project_contracts", ["external_contract_id"])


def downgrade() -> None:
    op.drop_table("project_contracts")
    op.drop_table("projects")

