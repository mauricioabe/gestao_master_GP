import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_project_db
from app.core.permissions import MANAGE_USERS, permissions_for_role
from app.core.security import create_token, hash_password
from app.main import app
from app.models import User


@pytest.fixture
def client():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(User(id=1, login='admin', name='Administrador', password_hash=hash_password('admin-pass-123'), role='GESTOR_PROGRAMA'))
        db.commit()
    def database():
        with Session(engine, expire_on_commit=False) as db:
            yield db
    app.dependency_overrides[get_project_db] = database
    try:
        with TestClient(app) as test_client:
            test_client.headers['Authorization'] = 'Bearer ' + create_token('admin', 'GESTOR_PROGRAMA')
            yield test_client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def payload(**changes):
    return {'login': 'test.user', 'name': 'Nome Completo', 'password': 'senha-teste-123', 'role': 'EQUIPE_PROJETO', **changes}


@pytest.mark.parametrize('rank', ['Ten', 'Cap', 'Maj', 'TC', 'Cel', 'Cel R1', 'Gen Bda'])
def test_military_user_display_and_authentication(client, rank):
    response = client.post('/api/users', json=payload(person_type='MILITAR', rank=rank, war_name='Silva'))
    assert response.status_code == 201, response.text
    user = response.json()
    assert user['name'] == 'Nome Completo'
    assert user['display_name'] == rank + ' Silva'
    assert user['person_type'] == 'MILITAR'
    token = client.post('/api/auth/login', json={'login': 'test.user', 'password': 'senha-teste-123'}).json()
    assert token['name'] == rank + ' Silva'
    me = client.get('/api/auth/me', headers={'Authorization': 'Bearer ' + token['access_token']}).json()
    assert me['name'] == 'Nome Completo'
    assert me['display_name'] == rank + ' Silva'
    updated = client.patch(f'/api/users/{user["id"]}', json={'war_name': 'Souza'})
    assert updated.status_code == 200
    assert updated.json()['display_name'] == rank + ' Souza'
    assert client.get('/api/users').json()[1]['display_name'] == rank + ' Souza'


def test_civil_fields_are_unchanged_and_defaulted(client):
    response = client.post('/api/users', json=payload())
    assert response.status_code == 201
    user = response.json()
    assert user['person_type'] == 'CIVIL'
    assert user['display_name'] == user['name'] == 'Nome Completo'
    assert user['rank'] is None and user['war_name'] is None


@pytest.mark.parametrize('identity', [
    {}, {'rank': 'Cap'}, {'war_name': 'Silva'}, {'rank': 'Cap', 'war_name': '   '},
    {'rank': 'Sgt', 'war_name': 'Silva'},
])
def test_incomplete_or_invalid_military_identity_rejected(client, identity):
    assert client.post('/api/users', json=payload(person_type='MILITAR', **identity)).status_code == 422


def test_civil_military_conversions_and_partial_updates(client):
    user = client.post('/api/users', json=payload()).json()
    path = f'/api/users/{user["id"]}'
    assert client.patch(path, json={'person_type': 'MILITAR'}).status_code == 422
    changed = client.patch(path, json={'person_type': 'MILITAR', 'rank': 'Cel R1', 'war_name': ' Abe '})
    assert changed.status_code == 200
    assert changed.json()['display_name'] == 'Cel R1 Abe'
    assert client.patch(path, json={'rank': None}).status_code == 422
    assert client.patch(path, json={'name': 'Outro Nome Completo'}).json()['display_name'] == 'Cel R1 Abe'
    civilian = client.patch(path, json={'person_type': 'CIVIL'}).json()
    assert civilian['display_name'] == 'Outro Nome Completo'
    assert civilian['rank'] is None and civilian['war_name'] is None


@pytest.mark.parametrize('role', ['COORDENADOR_PROJETOS', 'SUPERVISOR_PROJETO', 'CHEFE_ASS_PJT', 'ANALISTA_LICITACOES', 'ANALISTA_CONTRATOS', 'AUDITOR_INTERNO'])
def test_project_profiles_do_not_grant_user_administration(client, role):
    roles = client.get('/api/users/roles').json()
    assert len([r for r in roles if r['code'] == role]) == 1
    response = client.post('/api/users', json=payload(role=role))
    assert response.status_code == 201
    token = client.post('/api/auth/login', json={'login': 'test.user', 'password': 'senha-teste-123'}).json()
    assert token['permissions'] == permissions_for_role(role)
    assert MANAGE_USERS not in token['permissions']
    headers = {'Authorization': 'Bearer ' + token['access_token']}
    assert client.get('/api/users', headers=headers).status_code == 403
    assert client.patch('/api/users/1', json={'role': 'GESTOR_PROGRAMA'}, headers=headers).status_code == 403


def test_last_manager_protection_and_identity_validation_remain_effective(client):
    assert client.patch('/api/users/1', json={'role': 'COORDENADOR_PROJETOS'}).status_code == 422
    assert client.patch('/api/users/1', json={'active': False}).status_code == 422
    assert client.patch('/api/users/1', json={'name': '   '}).status_code == 422


def test_auditor_can_consult_but_cannot_modify_project_data(client):
    assert client.post('/api/users', json=payload(role='AUDITOR_INTERNO')).status_code == 201
    token = client.post('/api/auth/login', json={'login': 'test.user', 'password': 'senha-teste-123'}).json()
    headers = {'Authorization': 'Bearer ' + token['access_token']}
    assert client.get('/api/projects', headers=headers).status_code == 200
    assert client.get('/api/logbooks', headers=headers).status_code == 200
    for path in ['/api/projects', '/api/subprojects', '/api/logbooks', '/api/team-members', '/api/uploads/documents', '/api/subprojects/1/members']:
        assert client.post(path, json={}, headers=headers).status_code == 403
