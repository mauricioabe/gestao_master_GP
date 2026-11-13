from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.deps import current_user
from app.core.database import Base, get_project_db
from app.main import app
from app.models import Project, Subproject, TeamMember, User


@pytest.fixture
def system():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([
            User(id=1, login='manager', name='Gestor', password_hash='unused', role='GESTOR_PROGRAMA'),
            User(id=2, login='military', name='Nome Militar', password_hash='unused', person_type='MILITAR', rank='Cel R1', war_name='Silva', role='COORDENADOR_PROJETOS'),
            User(id=3, login='inactive', name='Usuário Inativo', password_hash='unused', active=False),
        ])
        for identifier in [1, 2]:
            db.add(Project(id=identifier, code=f'P{identifier}', name=f'Projeto {identifier}', manager='Gestor'))
        db.commit()
        for identifier in [1, 2]:
            db.add(Subproject(id=identifier, project_id=identifier, code=f'S{identifier}', wbs_code='1.1', name=f'Subprojeto {identifier}',
                              objective='Objetivo', main_product='Produto', manager='Gestor', responsible_unit='OM',
                              planned_start_date=date(2026, 1, 1), planned_end_date=date(2027, 1, 1)))
        db.commit()
    def database():
        with Session(engine, expire_on_commit=False) as db:
            yield db
    actor = {'role': 'GESTOR_PROGRAMA'}
    app.dependency_overrides[get_project_db] = database
    app.dependency_overrides[current_user] = lambda: User(id=1, role=actor['role'])
    try:
        with TestClient(app) as client:
            yield client, engine, actor
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_members_are_bound_to_independent_project_and_subproject_rosters(system):
    client, engine, _ = system
    paths = ['/api/projects/1/members', '/api/projects/2/members', '/api/subprojects/1/members', '/api/subprojects/2/members']
    for path in paths:
        assert client.get(path).json() == []
    first = client.post(paths[0], json={'user_id': 2})
    assert first.status_code == 201, first.text
    assert first.json()['assignment_label'] == 'Cel R1 Silva · Coordenador de Projetos'
    assert first.json()['added_at']
    assert 'login' not in first.json() and 'password_hash' not in first.json()
    for path in paths[1:]:
        assert client.get(path).json() == []
        assert client.post(path, json={'user_id': 2}).status_code == 201
    with Session(engine) as db:
        assert db.scalar(select(func.count(TeamMember.id)).where(TeamMember.user_id == 2)) == 1
    assert client.delete(paths[0] + '/2').status_code == 204
    assert client.get(paths[0]).json() == []
    for path in paths[1:]:
        assert client.get(path).json()[0]['id'] == 2
    with Session(engine) as db:
        assert db.get(User, 2) is not None
        member_id = db.scalar(select(TeamMember.id).where(TeamMember.user_id == 2))
        assert member_id is not None
    diary = client.post('/api/logbooks', json={'subject_principal': 'Histórico', 'responsible_id': member_id})
    assert diary.status_code == 201


@pytest.mark.parametrize('kind', ['projects', 'subprojects'])
def test_duplicate_inactive_and_missing_user_validation(system, kind):
    client, _, _ = system
    path = f'/api/{kind}/1/members'
    assert client.post(path, json={'user_id': 2}).status_code == 201
    assert client.post(path, json={'user_id': 2}).status_code == 409
    assert client.post(path, json={'user_id': 3}).status_code == 422
    assert client.post(path, json={'user_id': 999}).status_code == 422
    assert client.post(path, json={'user_id': 0}).status_code == 422
    assert len(client.get(path).json()) == 1
    assert client.delete(f'/api/{kind}/2/members/2').status_code == 404
    assert client.get(path).json()[0]['id'] == 2
    assert client.get(f'/api/{kind}/999/members').status_code == 404


@pytest.mark.parametrize('role,project_status,subproject_status', [
    ('GESTOR_PROGRAMA', 201, 201), ('GERENTE_PROJETOS', 201, 201),
    ('COORDENADOR_PROJETOS', 201, 201), ('CHEFE_ASS_PJT', 201, 201),
    ('ANALISTA_PROJETOS', 403, 201), ('SUPERVISOR_PROJETO', 403, 201),
    ('EQUIPE_PROJETO', 403, 403),
])
def test_membership_permissions_follow_parent_management(system, role, project_status, subproject_status):
    client, _, actor = system
    actor['role'] = role
    for kind, expected in [('projects', project_status), ('subprojects', subproject_status)]:
        path = f'/api/{kind}/1/members'
        assert client.get(path).status_code == 200
        assert client.post(path, json={'user_id': 2}).status_code == expected
        assert client.delete(path + '/2').status_code == (204 if expected == 201 else 403)


def test_user_inactivation_preserves_existing_membership_and_blocks_new_links(system):
    client, engine, _ = system
    assert client.post('/api/subprojects/1/members', json={'user_id': 2}).status_code == 201
    with Session(engine) as db:
        db.get(User, 2).active = False
        db.commit()
    assert client.get('/api/subprojects/1/members').json()[0]['active'] is False
    assert client.post('/api/projects/1/members', json={'user_id': 2}).status_code == 422
    assert client.delete('/api/subprojects/1/members/2').status_code == 204


@pytest.mark.parametrize('kind', ['projects', 'subprojects'])
def test_membership_rejects_archived_parent(system, kind):
    client, engine, _ = system
    with Session(engine) as db:
        db.get(Project if kind == 'projects' else Subproject, 1).active = False
        db.commit()
    assert client.post(f'/api/{kind}/1/members', json={'user_id': 2}).status_code == 404


def test_diary_responsible_options_match_linked_project_and_subproject_teams(system):
    client, engine, _ = system
    assert client.post('/api/projects/1/members', json={'user_id': 2}).status_code == 201
    assert client.post('/api/subprojects/1/members', json={'user_id': 1}).status_code == 201
    assert client.post('/api/subprojects/2/members', json={'user_id': 2}).status_code == 201
    with Session(engine) as db:
        db.add(TeamMember(full_name='Integrante antigo sem vínculo'))
        db.commit()
    def users(query):
        response = client.get('/api/team-members' + query)
        assert response.status_code == 200
        return [member['user_id'] for member in response.json()]
    assert users('?project_ids=1') == [2]
    assert users('?subproject_ids=1') == [1]
    assert set(users('?project_ids=1&subproject_ids=1')) == {1, 2}
    assert users('?project_ids=1&subproject_ids=2') == [2]
    assert users('?subproject_ids=999') == []
    assert len(users('')) == 3


def test_multiple_relators_persist_and_search_matches_any_relator(system):
    client, _, _ = system
    assert client.post('/api/projects/1/members', json={'user_id': 1}).status_code == 201
    assert client.post('/api/subprojects/1/members', json={'user_id': 2}).status_code == 201
    options = client.get('/api/logbooks/relator-options?project_ids=1&subproject_ids=1').json()
    members = {m['user_id']: m['id'] for m in options}
    assert set(members) == {1, 2}
    body = {'subject_principal': 'Relato conjunto', 'project_ids': [1], 'subproject_ids': [1],
            'relator_ids': [members[1], members[2], members[1]]}
    created = client.post('/api/logbooks', json=body)
    assert created.status_code == 201, created.text
    book = created.json()
    assert set(book['relator_ids']) == {members[1], members[2]}
    assert len(book['relators']) == 2
    assert book['responsible_id'] == members[1]  # compatibility for older clients
    assert client.get('/api/logbooks?search=Silva').json()[0]['id'] == book['id']
    assert len(client.get(f'/api/logbooks/{book["id"]}').json()['relators']) == 2
    updated = client.put(f'/api/logbooks/{book["id"]}', json={**body, 'relator_ids': [members[2]]})
    assert updated.status_code == 200
    assert updated.json()['relator_ids'] == [members[2]]
    assert updated.json()['responsible_id'] == members[2]
    assert client.put(f'/api/logbooks/{book["id"]}', json={**body, 'relator_ids': [], 'responsible_id': members[1]}).status_code == 422


def test_relators_must_belong_to_linked_scope_even_for_legacy_payload(system):
    client, _, _ = system
    client.post('/api/projects/2/members', json={'user_id': 1})
    client.post('/api/subprojects/1/members', json={'user_id': 2})
    members = {m['user_id']: m['id'] for m in client.get('/api/team-members').json()}
    options = client.get('/api/logbooks/relator-options?subproject_ids=1').json()
    assert [m['user_id'] for m in options] == [2]
    base = {'subject_principal': 'Assunto', 'subproject_ids': [1]}
    assert client.post('/api/logbooks', json={**base, 'relator_ids': [members[1]]}).status_code == 422
    assert client.post('/api/logbooks', json={**base, 'responsible_id': members[1]}).status_code == 422
    assert client.post('/api/logbooks', json={**base, 'relator_ids': [members[1], members[2]]}).status_code == 422
    assert client.post('/api/logbooks', json={**base, 'relator_ids': [members[2]]}).status_code == 201


def test_unassigned_registered_users_are_not_relator_options(system):
    client, _, _ = system
    member = client.post('/api/team-members', json={'user_id': 1}).json()
    assert client.get('/api/logbooks/relator-options').json() == []
    assert client.post('/api/logbooks', json={'subject_principal': 'Sem equipe', 'relator_ids': [member['id']]}).status_code == 422


def test_historical_relators_retained_but_cannot_move_to_unrelated_team(system):
    client, engine, _ = system
    client.post('/api/subprojects/1/members', json={'user_id': 2})
    member = client.get('/api/logbooks/relator-options?subproject_ids=1').json()[0]
    body = {'subject_principal': 'Histórico de relatores', 'subproject_ids': [1], 'relator_ids': [member['id']]}
    created = client.post('/api/logbooks', json=body).json()
    with Session(engine) as db:
        db.get(User, 2).active = False
        db.commit()
    assert client.get('/api/logbooks/relator-options?subproject_ids=1').json() == []
    assert client.post('/api/logbooks', json=body).status_code == 422
    assert client.put(f'/api/logbooks/{created["id"]}', json=body).status_code == 200
    assert client.put(f'/api/logbooks/{created["id"]}', json={**body, 'subproject_ids': [2]}).status_code == 422
