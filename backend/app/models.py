from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(40), default="EQUIPE_PROJETO", index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    manager: Mapped[str] = mapped_column(String(140))
    status: Mapped[str] = mapped_column(String(30), default="PLANEJAMENTO", index=True)
    phase: Mapped[str] = mapped_column(String(30), default="NAO_INICIADO", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIA")
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    progress: Mapped[int] = mapped_column(default=0)
    budget: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    cma: Mapped[str | None] = mapped_column(String(20), index=True)
    geographic_scope: Mapped[str | None] = mapped_column(Text)
    objectives: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    contracts: Mapped[list["ProjectContract"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    oms: Mapped[list["ProjectOm"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    documents: Mapped[list["ProjectDocument"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    subprojects: Mapped[list["Subproject"]] = relationship(back_populates="project", foreign_keys="Subproject.project_id", cascade="all, delete-orphan")

    @property
    def duration_years(self) -> int | None:
        if not self.start_date or not self.end_date:
            return None
        return max(0, int((self.end_date - self.start_date).days / 365.25))


class ProjectContract(Base):
    __tablename__ = "project_contracts"
    __table_args__ = (UniqueConstraint("project_id", "external_contract_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    external_contract_id: Mapped[str] = mapped_column(String(60), index=True)
    contract_number: Mapped[str | None] = mapped_column(String(50))
    contract_object: Mapped[str | None] = mapped_column(Text)
    supplier_name: Mapped[str | None] = mapped_column(String(255))
    global_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    linked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    project: Mapped[Project] = relationship(back_populates="contracts")


class ProjectOm(Base):
    __tablename__ = "project_oms"
    __table_args__ = (UniqueConstraint("project_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    project: Mapped[Project] = relationship(back_populates="oms")


class ProjectDocument(Base):
    __tablename__ = "project_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(500))
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    project: Mapped[Project] = relationship(back_populates="documents")

class Subproject(Base):
    __tablename__ = "subprojects"
    __table_args__ = (
        UniqueConstraint("project_id", "code", name="uq_subprojects_project_code"),
        UniqueConstraint("project_id", "wbs_code", name="uq_subprojects_project_wbs"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("subprojects.id", ondelete="RESTRICT"), index=True)
    wbs_code: Mapped[str] = mapped_column(String(40))
    sort_order: Mapped[int] = mapped_column(default=1)
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    short_name: Mapped[str | None] = mapped_column(String(60))
    description: Mapped[str | None] = mapped_column(Text)
    objective: Mapped[str] = mapped_column(Text)
    main_product: Mapped[str] = mapped_column(String(255))
    expected_deliverables: Mapped[str | None] = mapped_column(Text)
    scope: Mapped[str | None] = mapped_column(Text)
    out_of_scope: Mapped[str | None] = mapped_column(Text)
    expected_benefits: Mapped[str | None] = mapped_column(Text)
    manager: Mapped[str] = mapped_column(String(140))
    responsible_unit: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30), default="PLANEJAMENTO", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIA")
    planned_start_date: Mapped[date] = mapped_column(Date)
    planned_end_date: Mapped[date] = mapped_column(Date)
    real_start_date: Mapped[date | None] = mapped_column(Date)
    real_end_date: Mapped[date | None] = mapped_column(Date)
    execution_percentage: Mapped[int] = mapped_column(default=0)
    budget: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    key_milestones: Mapped[str | None] = mapped_column(Text)
    schedule_status: Mapped[str | None] = mapped_column(String(80))
    justification: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    project: Mapped[Project] = relationship(back_populates="subprojects", foreign_keys=[project_id])
    parent: Mapped["Subproject | None"] = relationship(remote_side="Subproject.id", back_populates="children")
    children: Mapped[list["Subproject"]] = relationship(back_populates="parent")
    activities: Mapped[list["Activity"]] = relationship(back_populates="subproject", cascade="all, delete-orphan")
    contracts: Mapped[list["SubprojectContract"]] = relationship(back_populates="subproject", cascade="all, delete-orphan")


class SubprojectContract(Base):
    __tablename__ = "subproject_contracts"
    __table_args__ = (UniqueConstraint("subproject_id", "external_contract_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    subproject_id: Mapped[int] = mapped_column(ForeignKey("subprojects.id", ondelete="CASCADE"), index=True)
    external_contract_id: Mapped[str] = mapped_column(String(60), index=True)
    contract_number: Mapped[str | None] = mapped_column(String(50))
    contract_object: Mapped[str | None] = mapped_column(Text)
    supplier_name: Mapped[str | None] = mapped_column(String(255))
    global_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    linked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    subproject: Mapped[Subproject] = relationship(back_populates="contracts")


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        UniqueConstraint(
            "subproject_id",
            "schedule_type",
            "wbs_code",
            name="uq_activities_subproject_schedule_wbs",
        ),
        UniqueConstraint(
            "subproject_id",
            "schedule_type",
            "source_system",
            "source_key",
            name="uq_activities_import_source",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subproject_id: Mapped[int] = mapped_column(ForeignKey("subprojects.id", ondelete="CASCADE"), index=True)
    schedule_type: Mapped[str] = mapped_column(String(20), default="MILESTONE", server_default="MILESTONE", index=True)
    wbs_code: Mapped[str] = mapped_column(String(60))
    sort_order: Mapped[int] = mapped_column(default=1)
    name: Mapped[str] = mapped_column(String(255))
    start_date: Mapped[date] = mapped_column(Date)
    finish_date: Mapped[date] = mapped_column(Date)
    resource_names: Mapped[str | None] = mapped_column(Text)
    execution_percentage: Mapped[int] = mapped_column(default=0)
    planned_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"), server_default="0")
    actual_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"), server_default="0")
    delivery_status: Mapped[str] = mapped_column(String(20), default="EM_PLANEJAMENTO", server_default="EM_PLANEJAMENTO", index=True)
    predecessor_id: Mapped[int | None] = mapped_column(ForeignKey("activities.id", ondelete="RESTRICT"), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("activities.id", ondelete="RESTRICT"), index=True)
    source_system: Mapped[str | None] = mapped_column(String(30), index=True)
    source_key: Mapped[str | None] = mapped_column(String(120))
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    subproject: Mapped[Subproject] = relationship(back_populates="activities")
    predecessor: Mapped["Activity | None"] = relationship(remote_side="Activity.id", foreign_keys=[predecessor_id])
    parent: Mapped["Activity | None"] = relationship(remote_side="Activity.id", foreign_keys=[parent_id], back_populates="children")
    children: Mapped[list["Activity"]] = relationship(foreign_keys="Activity.parent_id", back_populates="parent")
