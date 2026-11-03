"""Modulo hierarquico de subprojetos com estrutura EAP/WBS.

Revision ID: 0003_subprojects
Revises: 0002_project_crud
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_subprojects"
down_revision = "0002_project_crud"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subprojects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("wbs_code", sa.String(40), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("short_name", sa.String(60), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("main_product", sa.String(255), nullable=False),
        sa.Column("expected_deliverables", sa.Text(), nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("out_of_scope", sa.Text(), nullable=True),
        sa.Column("expected_benefits", sa.Text(), nullable=True),
        sa.Column("manager", sa.String(140), nullable=False),
        sa.Column("responsible_unit", sa.String(120), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PLANEJAMENTO"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="MEDIA"),
        sa.Column("planned_start_date", sa.Date(), nullable=False),
        sa.Column("planned_end_date", sa.Date(), nullable=False),
        sa.Column("real_start_date", sa.Date(), nullable=True),
        sa.Column("real_end_date", sa.Date(), nullable=True),
        sa.Column("execution_percentage", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("budget", sa.Numeric(18, 2), nullable=True),
        sa.Column("key_milestones", sa.Text(), nullable=True),
        sa.Column("schedule_status", sa.String(80), nullable=True),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("execution_percentage BETWEEN 0 AND 100", name="ck_subprojects_execution"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["subprojects.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("project_id", "code", name="uq_subprojects_project_code"),
        sa.UniqueConstraint("project_id", "wbs_code", name="uq_subprojects_project_wbs"),
    )
    op.create_index("ix_subprojects_project_id", "subprojects", ["project_id"])
    op.create_index("ix_subprojects_parent_id", "subprojects", ["parent_id"])
    op.create_index("ix_subprojects_status", "subprojects", ["status"])
    op.create_index("ix_subprojects_active", "subprojects", ["active"])


def downgrade() -> None:
    op.drop_table("subprojects")
