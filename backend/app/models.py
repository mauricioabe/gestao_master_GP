from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Table, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150))
    person_type: Mapped[str] = mapped_column(String(10), default='CIVIL', server_default='CIVIL')
    rank: Mapped[str | None] = mapped_column(String(20))
    war_name: Mapped[str | None] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(40), default="EQUIPE_PROJETO", index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    @property
    def display_name(self) -> str:
        if self.person_type == 'MILITAR' and self.rank and self.war_name:
            return f'{self.rank} {self.war_name}'
        return self.name


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
    manager: Mapped[str] = mapped_column(String(150))
    manager_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    military_responsible_id: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    responsible_unit: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30), default="PLANEJAMENTO", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIA")
    lifecycle_stage: Mapped[str | None] = mapped_column(String(30))
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
    manager_user: Mapped[User | None] = relationship(foreign_keys=[manager_user_id])
    military_responsible: Mapped[User | None] = relationship(foreign_keys=[military_responsible_id])
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


# SQLite uses INTEGER for autoincrement in tests; production IDs are BIGINT.
LOGBOOK_ID = BigInteger().with_variant(Integer(), 'sqlite')


def logbook_utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

logbook_projects = Table(
    'logbook_projects', Base.metadata,
    Column('logbook_id', LOGBOOK_ID, ForeignKey('logbooks.id', ondelete='CASCADE'), primary_key=True),
    Column('project_id', ForeignKey('projects.id', ondelete='CASCADE'), primary_key=True),
)
logbook_subprojects = Table(
    'logbook_subprojects', Base.metadata,
    Column('logbook_id', LOGBOOK_ID, ForeignKey('logbooks.id', ondelete='CASCADE'), primary_key=True),
    Column('subproject_id', ForeignKey('subprojects.id', ondelete='CASCADE'), primary_key=True),
)
logbook_relators = Table(
    'logbook_relators', Base.metadata,
    Column('logbook_id', LOGBOOK_ID, ForeignKey('logbooks.id', ondelete='CASCADE'), primary_key=True),
    Column('team_member_id', ForeignKey('team_members.id', ondelete='RESTRICT'), primary_key=True),
)


class TeamMember(Base):
    __tablename__ = 'team_members'
    id: Mapped[int] = mapped_column(primary_key=True)
    rank: Mapped[str] = mapped_column(String(60), default='')
    full_name: Mapped[str] = mapped_column(String(150))
    war_name: Mapped[str] = mapped_column(String(100), default='')
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), unique=True)
    user: Mapped[User | None] = relationship()


class Logbook(Base):
    __tablename__ = 'logbooks'
    id: Mapped[int] = mapped_column(LOGBOOK_ID, primary_key=True)
    subject_principal: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text, default='')
    scope: Mapped[str] = mapped_column(String(20), default='global')
    status: Mapped[str] = mapped_column(String(30), default='aberto', index=True)
    registration_date: Mapped[date] = mapped_column(Date)
    closure_date: Mapped[date | None] = mapped_column(Date)
    responsible_id: Mapped[int] = mapped_column(ForeignKey('team_members.id', ondelete='RESTRICT'))
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    tags: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=logbook_utc_now, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=logbook_utc_now, server_default=func.now(), onupdate=logbook_utc_now)
    responsible: Mapped[TeamMember] = relationship()
    relators: Mapped[list[TeamMember]] = relationship(secondary=logbook_relators, order_by='TeamMember.id')
    projects: Mapped[list[Project]] = relationship(secondary=logbook_projects)
    subprojects: Mapped[list[Subproject]] = relationship(secondary=logbook_subprojects)
    items: Mapped[list['LogbookItem']] = relationship(back_populates='logbook', cascade='all, delete-orphan', order_by='(LogbookItem.event_date, LogbookItem.id)')


class LogbookItem(Base):
    __tablename__ = 'logbook_items'
    id: Mapped[int] = mapped_column(LOGBOOK_ID, primary_key=True)
    logbook_id: Mapped[int] = mapped_column(LOGBOOK_ID, ForeignKey('logbooks.id', ondelete='CASCADE'), index=True)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    event_date: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    type: Mapped[str] = mapped_column(String(20))
    references_text: Mapped[str] = mapped_column(String(255), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=logbook_utc_now, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=logbook_utc_now, server_default=func.now(), onupdate=logbook_utc_now)
    author: Mapped[User] = relationship()
    logbook: Mapped[Logbook] = relationship(back_populates='items')
    attachments: Mapped[list['LogbookItemAttachment']] = relationship(cascade='all, delete-orphan')


class LogbookItemAttachment(Base):
    __tablename__ = 'logbook_item_attachments'
    id: Mapped[int] = mapped_column(LOGBOOK_ID, primary_key=True)
    item_id: Mapped[int] = mapped_column(LOGBOOK_ID, ForeignKey('logbook_items.id', ondelete='CASCADE'), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(80), unique=True)
    mime_type: Mapped[str] = mapped_column(String(150))
    file_size: Mapped[int] = mapped_column(BigInteger)
    description: Mapped[str] = mapped_column(String(500), default='')


class LogbookLink(Base):
    __tablename__ = 'logbook_links'
    __table_args__ = (UniqueConstraint('source_logbook_id', 'target_logbook_id', 'link_type', name='uq_logbook_link'),)
    id: Mapped[int] = mapped_column(LOGBOOK_ID, primary_key=True)
    source_logbook_id: Mapped[int] = mapped_column(LOGBOOK_ID, ForeignKey('logbooks.id', ondelete='CASCADE'), index=True)
    target_logbook_id: Mapped[int] = mapped_column(LOGBOOK_ID, ForeignKey('logbooks.id', ondelete='CASCADE'), index=True)
    link_type: Mapped[str] = mapped_column(String(30))
    observations: Mapped[str] = mapped_column(Text, default='')


class ProjectMember(Base):
    __tablename__ = 'project_members'
    project_id: Mapped[int] = mapped_column(ForeignKey('projects.id', ondelete='CASCADE'), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), primary_key=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=logbook_utc_now, server_default=func.now())
    user: Mapped[User] = relationship()


class SubprojectMember(Base):
    __tablename__ = 'subproject_members'
    subproject_id: Mapped[int] = mapped_column(ForeignKey('subprojects.id', ondelete='CASCADE'), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), primary_key=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=logbook_utc_now, server_default=func.now())
    user: Mapped[User] = relationship()
