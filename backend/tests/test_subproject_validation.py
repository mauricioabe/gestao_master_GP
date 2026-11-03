import pytest
from pydantic import ValidationError

from app.schemas import SubprojectCreate


def payload(**changes):
    data = {
        "project_id": 1,
        "code": "SITAGE",
        "name": "Sistema Tatico de Gerenciamento",
        "objective": "Implantar a capacidade operacional",
        "main_product": "Sistema implantado",
        "manager": "Gerente do subprojeto",
        "responsible_unit": "CCOMGEX",
        "planned_start_date": "2026-01-01",
        "planned_end_date": "2028-12-31",
    }
    data.update(changes)
    return data


def test_subprojeto_valido():
    item = SubprojectCreate.model_validate(payload())
    assert item.code == "SITAGE"


def test_cronograma_planejado_invalido():
    with pytest.raises(ValidationError, match="data final planejada"):
        SubprojectCreate.model_validate(payload(planned_end_date="2025-12-31"))


def test_suspensao_exige_justificativa():
    with pytest.raises(ValidationError, match="justificativa"):
        SubprojectCreate.model_validate(payload(status="SUSPENSO"))


def test_conclusao_exige_data_real():
    with pytest.raises(ValidationError, match="termino real"):
        SubprojectCreate.model_validate(payload(status="CONCLUIDO"))
