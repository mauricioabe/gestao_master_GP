from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LoginRequest(BaseModel):
    login: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str
    permissions: list[str]


class UserCreate(BaseModel):
    login: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    role: str


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=150)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: str | None = None
    active: bool | None = None


class UserOut(BaseModel):
    id: int
    login: str
    name: str
    role: str
    active: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ContractSnapshot(BaseModel):
    external_contract_id: str = Field(max_length=60)
    contract_number: str | None = None
    contract_object: str | None = None
    supplier_name: str | None = None
    global_value: Decimal | None = None


class ProjectOmInput(BaseModel):
    name: str = Field(min_length=2, max_length=200)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip()


class ProjectDocumentInput(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    url: str = Field(min_length=8, max_length=500)

    @field_validator("url")
    @classmethod
    def valid_url(cls, value: str) -> str:
        value = value.strip()
        if not value.lower().startswith(("http://", "https://", "/uploads/documents/")):
            raise ValueError("Informe um link http(s) ou um documento enviado pelo sistema")
        return value


class ProjectBase(BaseModel):
    code: str = Field(min_length=2, max_length=30)
    name: str = Field(min_length=3, max_length=180)
    description: str | None = None
    manager: str = Field(min_length=3, max_length=140)
    status: str = "PLANEJAMENTO"
    phase: str = "NAO_INICIADO"
    priority: str = "MEDIA"
    start_date: date | None = None
    end_date: date | None = None
    progress: int = Field(default=0, ge=0, le=100)
    budget: Decimal | None = Field(default=None, ge=0)
    cma: str | None = Field(default=None, max_length=20)
    geographic_scope: str | None = None
    objectives: str | None = None

    @model_validator(mode="after")
    def validate_project(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("A data final nao pode ser anterior a data inicial")
        return self


class ProjectCreate(ProjectBase):
    contracts: list[ContractSnapshot] = Field(default_factory=list)
    oms: list[ProjectOmInput] = Field(default_factory=list)
    documents: list[ProjectDocumentInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_execution_budget(self):
        if self.phase == "EXECUCAO" and not self.budget:
            raise ValueError("O orcamento e obrigatorio para projetos em execucao")
        return self


class ProjectUpdate(ProjectCreate):
    pass


class ProjectContractOut(ContractSnapshot):
    id: int
    linked_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProjectOmOut(ProjectOmInput):
    id: int
    added_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProjectDocumentOut(ProjectDocumentInput):
    id: int
    added_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProjectOut(ProjectBase):
    id: int
    active: bool
    duration_years: int | None
    created_at: datetime
    updated_at: datetime
    contracts: list[ProjectContractOut]
    oms: list[ProjectOmOut]
    documents: list[ProjectDocumentOut]
    model_config = ConfigDict(from_attributes=True)

class SubprojectBase(BaseModel):
    project_id: int
    parent_id: int | None = None
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=3, max_length=200)
    short_name: str | None = Field(default=None, max_length=60)
    description: str | None = None
    objective: str = Field(min_length=3)
    main_product: str = Field(min_length=2, max_length=255)
    expected_deliverables: str | None = None
    scope: str | None = None
    out_of_scope: str | None = None
    expected_benefits: str | None = None
    manager: str = Field(min_length=3, max_length=140)
    responsible_unit: str = Field(min_length=2, max_length=120)
    status: str = "PLANEJAMENTO"
    priority: str = "MEDIA"
    planned_start_date: date
    planned_end_date: date
    real_start_date: date | None = None
    real_end_date: date | None = None
    execution_percentage: int = Field(default=0, ge=0, le=100)
    budget: Decimal | None = Field(default=None, ge=0)
    key_milestones: str | None = None
    schedule_status: str | None = Field(default=None, max_length=80)
    justification: str | None = None

    @model_validator(mode="after")
    def validate_subproject(self):
        if self.planned_end_date < self.planned_start_date:
            raise ValueError("A data final planejada nao pode ser anterior a data inicial")
        if self.real_start_date and self.real_end_date and self.real_end_date < self.real_start_date:
            raise ValueError("A data final real nao pode ser anterior a data inicial real")
        if self.status in {"SUSPENSO", "SOBRESTADO", "CANCELADO"} and not self.justification:
            raise ValueError("A justificativa e obrigatoria para a situacao selecionada")
        if self.status == "CONCLUIDO" and not self.real_end_date:
            raise ValueError("A data de termino real e obrigatoria para subprojeto concluido")
        return self


class SubprojectCreate(SubprojectBase):
    pass


class SubprojectUpdate(SubprojectBase):
    pass


class SubprojectOut(SubprojectBase):
    id: int
    wbs_code: str
    sort_order: int
    active: bool
    project_name: str
    project_code: str
    parent_name: str | None = None
    children_count: int = 0
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SubprojectContractsInput(BaseModel):
    external_contract_ids: list[str] = Field(default_factory=list, max_length=200)

    @field_validator("external_contract_ids")
    @classmethod
    def clean_ids(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if any(len(item) > 60 for item in cleaned):
            raise ValueError("Codigo de contrato invalido")
        return list(dict.fromkeys(cleaned))


class ActivityBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    start_date: date
    finish_date: date
    resource_names: str | None = None
    execution_percentage: int = Field(default=0, ge=0, le=100)
    planned_value: Decimal = Field(default=Decimal("0"), ge=0)
    actual_value: Decimal = Field(default=Decimal("0"), ge=0)
    delivery_status: str = Field(default="EM_PLANEJAMENTO", pattern="^(ENCERRADA|EM_EXECUCAO|CANCELADA|EM_PLANEJAMENTO)$")
    predecessor_id: int | None = None

    @model_validator(mode="after")
    def validate_activity(self):
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("O nome da atividade e obrigatorio")
        if self.finish_date < self.start_date:
            raise ValueError("A data de termino nao pode ser anterior a data de inicio")
        return self


class ActivityCreate(ActivityBase):
    pass


class ActivityUpdate(ActivityBase):
    pass


class ActivityReorder(BaseModel):
    target_id: int = Field(gt=0)
    position: Literal["before", "after", "inside"]


class ActivityOut(ActivityBase):
    id: int
    subproject_id: int
    schedule_type: str
    source_system: str | None = None
    source_key: str | None = None
    wbs_code: str
    sort_order: int
    duration_days: int
    predecessor_wbs: str | None = None
    parent_id: int | None = None
    depth: int = 0
    is_summary: bool = False
    active: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CffStageOut(BaseModel):
    id: int
    cff_id: int
    contract_id: str
    contract_number: str | None = None
    cff_version: int
    stage_number: str | None = None
    name: str
    stage_value: Decimal | None = None
    readiness_letter_date: date | None = None
    import_start_date: date
    import_finish_date: date
    bank_order: str | None = None
    paid_value: Decimal = Decimal("0")
    payment_status: str
    payment_message: str
    payment_verified_at: datetime | None = None
    execution_percentage: int
    importable: bool
    imported: bool
    imported_activity_id: int | None = None


class CffPreviewOut(BaseModel):
    linked_contracts: int
    cff_files: int
    stages: list[CffStageOut]


class CffImportInput(BaseModel):
    stage_ids: list[int] = Field(min_length=1, max_length=500)
    parent_activity_id: int = Field(gt=0)

    @field_validator("stage_ids")
    @classmethod
    def unique_stage_ids(cls, value: list[int]) -> list[int]:
        return list(dict.fromkeys(value))


class CffImportOut(BaseModel):
    imported: int
    updated: int
    skipped: int
    activities: list[ActivityOut]
