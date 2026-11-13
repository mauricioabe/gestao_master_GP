import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.deps import current_user
from app.core.database import Base, get_project_db
from app.main import app
from app.models import Project, User
from app.schemas import SubprojectCreate


STAGES = ['INICIACAO', 'CONCEPCAO', 'CONTRATACAO', 'CONCEPCAO_CONTRATACAO',
          'EM_PRODUCAO', 'IMPLANTACAO', 'ENTREGA', 'ENCERRADO']


def payload(**changes):
    return {'project_id': 1, 'code': 'SUB-01', 'name': 'Subprojeto de teste',
            'objective': 'Implantar capacidade', 'main_product': 'Sistema implantado',
            'manager': 'Gerente', 'responsible_unit': 'CCOMGEX',
            'planned_start_date': '2026-01-01', 'planned_end_date': '2028-12-31', **changes}


@pytest.fixture
def client():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Project(id=1, code='SAD3', name='Projeto SAD3', manager='Gestor'))
        db.commit()
    def database():
        with Session(engine, expire_on_commit=False) as db:
            yield db
    app.dependency_overrides[get_project_db] = database
    app.dependency_overrides[current_user] = lambda: User(id=1, role='GESTOR_PROGRAMA')
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


@pytest.mark.parametrize('stage', STAGES)
def test_lifecycle_stage_round_trip_in_create_edit_and_grid(client, stage):
    response = client.post('/api/subprojects', json=payload(lifecycle_stage=stage))
    assert response.status_code == 201, response.text
    item = response.json()
    assert item['lifecycle_stage'] == stage
    assert item['status'] == 'PLANEJAMENTO'  # Lifecycle and operational status are independent.
    assert client.get('/api/subprojects').json()[0]['lifecycle_stage'] == stage
    assert client.get('/api/projects/1/subprojects').json()[0]['lifecycle_stage'] == stage
    changed = STAGES[(STAGES.index(stage) + 1) % len(STAGES)]
    updated = client.put(f'/api/subprojects/{item["id"]}', json=payload(lifecycle_stage=changed))
    assert updated.status_code == 200, updated.text
    assert client.get(f'/api/subprojects/{item["id"]}').json()['lifecycle_stage'] == changed
    assert client.put(f'/api/subprojects/{item["id"]}', json=payload(lifecycle_stage=None)).json()['lifecycle_stage'] is None


def test_existing_clients_can_omit_lifecycle_stage(client):
    response = client.post('/api/subprojects', json=payload())
    assert response.status_code == 201
    assert response.json()['lifecycle_stage'] is None


@pytest.mark.parametrize('invalid', ['OUTRA_FASE', '', 'Concepção'])
def test_unknown_stage_is_rejected(invalid):
    with pytest.raises(ValidationError):
        SubprojectCreate.model_validate(payload(lifecycle_stage=invalid))
