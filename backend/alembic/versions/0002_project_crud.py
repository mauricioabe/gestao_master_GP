"""Amplia o cadastro para o CRUD completo de projetos SAD.

Revision ID: 0002_project_crud
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_project_crud"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("phase", sa.String(30), nullable=False, server_default="NAO_INICIADO"))
    op.add_column("projects", sa.Column("budget", sa.Numeric(18, 2), nullable=True))
    op.add_column("projects", sa.Column("cma", sa.String(20), nullable=True))
    op.add_column("projects", sa.Column("geographic_scope", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("objectives", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_index("ix_projects_phase", "projects", ["phase"])
    op.create_index("ix_projects_cma", "projects", ["cma"])
    op.create_index("ix_projects_active", "projects", ["active"])
    op.execute("""UPDATE projects SET phase = CASE status
        WHEN 'EM_EXECUCAO' THEN 'EXECUCAO'
        WHEN 'CONCLUIDO' THEN 'ENCERRADO'
        WHEN 'SUSPENSO' THEN 'SUSPENSO'
        WHEN 'ATRASADO' THEN 'EXECUCAO'
        ELSE 'NAO_INICIADO' END""")

    op.create_table(
        "project_oms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("added_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("project_id", "name", name="uq_project_om_name"),
    )
    op.create_index("ix_project_oms_project_id", "project_oms", ["project_id"])

    op.create_table(
        "project_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("added_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_project_documents_project_id", "project_documents", ["project_id"])


def downgrade() -> None:
    op.drop_table("project_documents")
    op.drop_table("project_oms")
    op.drop_index("ix_projects_active", table_name="projects")
    op.drop_index("ix_projects_cma", table_name="projects")
    op.drop_index("ix_projects_phase", table_name="projects")
    op.drop_column("projects", "active")
    op.drop_column("projects", "objectives")
    op.drop_column("projects", "geographic_scope")
    op.drop_column("projects", "cma")
    op.drop_column("projects", "budget")
    op.drop_column("projects", "phase")
