import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.deps import current_user
from app.core.database import Base, get_project_db
from app.main import app
from app.models import Project, User


@pytest.fixture
def system():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Project(id=1, code='SAD3', name='Projeto SAD3', manager='Gestor'))
        db.add_all([
            User(id=1, login='civil', name='Gerente Civil', password_hash='unused', role='GERENTE_PROJETOS'),
            User(id=2, login='military', name='Nome Completo Militar', password_hash='unused', role='COORDENADOR_PROJETOS', person_type='MILITAR', rank='Cap', war_name='Silva'),
            User(id=3, login='inactive', name='Civil Inativo', password_hash='unused', role='GERENTE_PROJETOS', active=False),
            User(id=4, login='inactive.military', name='Militar Inativo', password_hash='unused', role='SUPERVISOR_PROJETO', active=False, person_type='MILITAR', rank='Maj', war_name='Souza'),
        ])
        db.commit()
    def database():
        with Session(engine, expire_on_commit=False) as db:
            yield db
    app.dependency_overrides[get_project_db] = database
    app.dependency_overrides[current_user] = lambda: User(id=1, role='ANALISTA_PROJETOS')
    try:
        with TestClient(app) as client:
            yield client, engine
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def payload(**changes):
    return {'project_id': 1, 'code': 'SUB-01', 'name': 'Subprojeto de teste',
            'objective': 'Implantar capacidade', 'main_product': 'Sistema implantado',
            'manager': 'Nome digitado', 'responsible_unit': 'CCOMGEX',
            'planned_start_date': '2026-01-01', 'planned_end_date': '2028-12-31', **changes}


def test_assignment_directory_available_without_exposing_user_administration(system):
    client, _ = system
    response = client.get('/api/users/assignment-options')
    assert response.status_code == 200
    users = response.json()
    assert {u['id'] for u in users} == {1, 2}
    assert users[1]['assignment_label'] == 'Cap Silva · Coordenador de Projetos'
    assert users[0]['assignment_label'] == 'Gerente Civil'
    assert all('login' not in u and 'password_hash' not in u for u in users)
    assert client.get('/api/users').status_code == 403


def test_civil_manager_and_military_responsible_round_trip(system):
    client, _ = system
    response = client.post('/api/subprojects', json=payload(manager_user_id=1, military_responsible_id=2))
    assert response.status_code == 201, response.text
    item = response.json()
    assert item['manager'] == 'Gerente Civil'
    assert item['manager_user']['id'] == 1
    assert item['military_responsible']['assignment_label'] == 'Cap Silva · Coordenador de Projetos'
    path = f'/api/subprojects/{item["id"]}'
    assert client.get(path).json()['military_responsible_id'] == 2
    assert client.get('/api/subprojects').json()[0]['military_responsible']['rank'] == 'Cap'
    # Older clients omitting the new fields must not silently lose assigned users.
    preserved = client.put(path, json=payload()).json()
    assert preserved['military_responsible_id'] == 2
    assert preserved['manager_user_id'] == 1
    cleared = client.put(path, json=payload(manager_user_id=1, military_responsible_id=None)).json()
    assert cleared['military_responsible_id'] is None
    assert cleared['military_responsible'] is None


@pytest.mark.parametrize('assignments', [
    {'manager_user_id': 2}, {'manager_user_id': 3}, {'manager_user_id': 999},
    {'military_responsible_id': 1}, {'military_responsible_id': 4}, {'military_responsible_id': 999},
])
def test_rejects_wrong_modality_inactive_and_missing_users(system, assignments):
    client, _ = system
    assert client.post('/api/subprojects', json=payload(**assignments)).status_code == 422


def test_existing_assignments_and_free_text_history_survive(system):
    client, engine = system
    item = client.post('/api/subprojects', json=payload(manager_user_id=1, military_responsible_id=2)).json()
    with Session(engine) as db:
        db.get(User, 1).active = False
        db.get(User, 2).active = False
        db.commit()
    changed = client.put(f'/api/subprojects/{item["id"]}', json=payload(manager_user_id=1, military_responsible_id=2))
    assert changed.status_code == 200
    assert changed.json()['military_responsible']['active'] is False
    legacy = client.post('/api/subprojects', json=payload(code='SUB-02', manager='Gerente anterior')).json()
    assert legacy['manager'] == 'Gerente anterior'
    assert legacy['manager_user_id'] is None
    assert legacy['military_responsible'] is None
