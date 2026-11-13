import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.deps import current_user
from app.core.database import Base, get_project_db
from app.main import app
from app.models import Project, ProjectMember, TeamMember, User


@pytest.fixture
def system():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([
            User(id=1, login='civil', name='Nome Civil', password_hash='unused', role='GESTOR_PROGRAMA'),
            User(id=2, login='military', name='Nome Militar', password_hash='unused', role='COORDENADOR_PROJETOS', person_type='MILITAR', rank='Cap', war_name='Silva'),
            User(id=3, login='inactive', name='Usuário Inativo', password_hash='unused', role='GERENTE_PROJETOS', active=False),
            TeamMember(id=1, full_name='Integrante anterior', rank='Gerente de Projetos', war_name='Anterior'),
        ])
        db.commit()
        db.add(Project(id=1, code='P1', name='Projeto 1', manager='Gestor'))
        db.commit()
        db.add(ProjectMember(project_id=1, user_id=2))
        db.commit()
    def database():
        with Session(engine, expire_on_commit=False) as db:
            yield db
    app.dependency_overrides[get_project_db] = database
    app.dependency_overrides[current_user] = lambda: User(id=1, role='GESTOR_PROGRAMA')
    try:
        with TestClient(app) as client:
            yield client, engine
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_member_uses_registered_user_identity_and_reflects_updates(system):
    client, engine = system
    response = client.post('/api/team-members', json={'user_id': 2, 'full_name': 'Spoof', 'rank': 'Other'})
    assert response.status_code == 201, response.text
    member = response.json()
    assert member['user_id'] == 2
    assert member['full_name'] == 'Nome Militar'
    assert member['rank'] == 'Cap'
    assert member['display_name'] == 'Cap Silva · Coordenador de Projetos'
    with Session(engine) as db:
        user = db.get(User, 2)
        user.rank, user.war_name, user.name = 'Maj', 'Souza', 'Nome Atualizado'
        db.commit()
    updated = next(m for m in client.get('/api/team-members').json() if m['id'] == member['id'])
    assert updated['display_name'] == 'Maj Souza · Coordenador de Projetos'
    assert updated['full_name'] == 'Nome Atualizado'


@pytest.mark.parametrize('body', [{}, {'full_name': 'Nome manual'}, {'user_id': 999}, {'user_id': 3}])
def test_new_members_require_existing_active_users(system, body):
    client, _ = system
    assert client.post('/api/team-members', json=body).status_code == 422


def test_link_existing_member_without_replacing_historical_id(system):
    client, _ = system
    response = client.put('/api/team-members/1', json={'user_id': 1})
    assert response.status_code == 200
    assert response.json()['id'] == 1
    assert response.json()['display_name'] == 'Nome Civil'
    assert response.json()['rank'] == ''
    assert client.post('/api/team-members', json={'user_id': 1}).status_code == 409
    assert client.put('/api/team-members/1', json={'user_id': 2}).status_code == 409
    assert client.put('/api/team-members/1', json={'user_id': None}).status_code == 422


def test_inactive_linked_user_remains_in_history_but_not_new_assignments(system):
    client, engine = system
    member = client.post('/api/team-members', json={'user_id': 2}).json()
    body = {'subject_principal': 'Assunto de teste', 'responsible_id': member['id'], 'registration_date': '2026-11-01'}
    book = client.post('/api/logbooks', json=body).json()
    with Session(engine) as db:
        db.get(User, 2).active = False
        db.commit()
    assert client.post('/api/logbooks', json=body).status_code == 422
    assert client.put(f'/api/logbooks/{book["id"]}', json=body).status_code == 200
    changed = client.put(f'/api/team-members/{member["id"]}', json={'user_id': 2, 'active': True}).json()
    assert changed['active'] is False
    assert changed['member_active'] is True
    assert changed['full_name'] == 'Nome Militar'
    with Session(engine) as db:
        assert db.scalar(select(TeamMember.user_id).where(TeamMember.id == member['id'])) == 2


def test_legacy_member_keeps_history_until_explicitly_linked(system):
    client, _ = system
    legacy = client.get('/api/team-members').json()[0]
    assert legacy['display_name'] == 'Gerente de Projetos Anterior'
    assert legacy['user_id'] is None
    assert client.put('/api/team-members/1', json={'active': False}).status_code == 200
