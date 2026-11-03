import pytest
from pydantic import ValidationError

from app.schemas import ProjectCreate


def payload(**changes):
    data = {
        "code": "SAD-T",
        "name": "Projeto de teste",
        "manager": "Gestor do projeto",
        "phase": "PLANEJAMENTO",
        "start_date": "2026-01-01",
        "contracts": [],
        "oms": [],
        "documents": [],
    }
    data.update(changes)
    return data


def test_orcamento_obrigatorio_em_execucao():
    with pytest.raises(ValidationError, match="orcamento e obrigatorio"):
        ProjectCreate.model_validate(payload(phase="EXECUCAO", budget=None))


def test_data_final_nao_pode_anteceder_inicio():
    with pytest.raises(ValidationError, match="data final"):
        ProjectCreate.model_validate(payload(start_date="2026-05-01", end_date="2026-04-30"))


def test_documento_exige_link_http():
    with pytest.raises(ValidationError, match="http"):
        ProjectCreate.model_validate(payload(documents=[{"name": "Termo", "url": "arquivo.pdf"}]))


def test_cadastro_completo_valido():
    project = ProjectCreate.model_validate(payload(
        phase="EXECUCAO",
        budget=1000,
        end_date="2027-01-01",
        oms=[{"name": "17o Batalhao de Fronteira"}],
        documents=[{"name": "Termo", "url": "https://example.org/termo"}],
    ))
    assert project.budget == 1000
    assert len(project.oms) == 1
