from datetime import date, datetime, timezone
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CleanModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')


class TeamMemberInput(CleanModel):
    user_id: int | None = Field(default=None, gt=0)
    rank: str = Field(default='', max_length=60)
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    war_name: str = Field(default='', max_length=100)
    active: bool = True


class LogbookInput(CleanModel):
    subject_principal: str = Field(min_length=1, max_length=255)
    description: str = Field(default='', max_length=100000)
    status: Literal['aberto', 'aguardando_validacao', 'fechado', 'cancelado'] = 'aberto'
    registration_date: date = Field(default_factory=lambda: datetime.now(ZoneInfo('America/Sao_Paulo')).date())
    closure_date: date | None = None
    responsible_id: int | None = Field(default=None, gt=0)
    relator_ids: list[Annotated[int, Field(gt=0)]] | None = Field(default=None, max_length=1000)
    tags: str = Field(default='', max_length=4000)
    project_ids: list[int] = Field(default_factory=list, max_length=1000)
    subproject_ids: list[int] = Field(default_factory=list, max_length=1000)

    @model_validator(mode='after')
    def dates(self):
        if self.relator_ids is not None and not self.relator_ids:
            raise ValueError('Selecione pelo menos um relator')
        if self.relator_ids is None and self.responsible_id is None:
            raise ValueError('Selecione pelo menos um relator')
        if self.status == 'fechado' and not self.closure_date:
            raise ValueError('Informe a data de fim para fechar o assunto')
        if self.closure_date and self.closure_date < self.registration_date:
            raise ValueError('A data de fim não pode anteceder a data de registro')
        return self


class LogbookItemInput(CleanModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=100000)
    event_date: datetime
    type: Literal['nota', 'decisao', 'pendencia', 'risco', 'evidencia'] = 'nota'
    references_text: str = Field(default='', max_length=255)

    @field_validator('event_date')
    @classmethod
    def normalize_event_date(cls, value):
        # datetime-local is interpreted in the institutional timezone; stored as UTC.
        if value.tzinfo is None:
            value = value.replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
        return value.astimezone(timezone.utc).replace(tzinfo=None)


class LogbookLinkInput(CleanModel):
    target_logbook_id: int = Field(gt=0)
    link_type: Literal['relacionado', 'depende_de', 'bloqueia', 'originado_de', 'subassunto_de']
    observations: str = Field(default='', max_length=10000)
