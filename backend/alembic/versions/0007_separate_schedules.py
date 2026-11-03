"""Separa Milestones do cronograma oficial do projeto.

Revision ID: 0007_separate_schedules
Revises: 0006_activity_hierarchy
"""
from alembic import op
import sqlalchemy as sa


revision = "0007_separate_schedules"
down_revision = "0006_activity_hierarchy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "activities",
        sa.Column("schedule_type", sa.String(length=20), nullable=False, server_default="MILESTONE"),
    )
    op.create_index("ix_activities_schedule_type", "activities", ["schedule_type"])
    op.drop_constraint("uq_activities_subproject_wbs", "activities", type_="unique")
    op.create_unique_constraint(
        "uq_activities_subproject_schedule_wbs",
        "activities",
        ["subproject_id", "schedule_type", "wbs_code"],
    )

    # O progresso oficial passa a ser calculado apenas pelo novo cronograma.
    op.execute("UPDATE subprojects SET execution_percentage = 0")
    op.execute("UPDATE projects SET progress = 0")


def downgrade() -> None:
    # O formato antigo comportava apenas um cronograma por subprojeto.
    op.execute("DELETE FROM activities WHERE schedule_type = 'PROJECT'")
    op.drop_constraint("uq_activities_subproject_schedule_wbs", "activities", type_="unique")
    op.create_unique_constraint(
        "uq_activities_subproject_wbs",
        "activities",
        ["subproject_id", "wbs_code"],
    )
    op.drop_index("ix_activities_schedule_type", table_name="activities")
    op.drop_column("activities", "schedule_type")
