import io
import json
from datetime import date
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api import logbooks
from app.core.database import Base, get_project_db
from app.core.security import create_token
from app.main import app
from app.models import Logbook, LogbookItem, LogbookItemAttachment, Project, ProjectMember, Subproject, SubprojectMember, TeamMember, User


@pytest.fixture
def system(tmp_path, monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    def database():
        with Session(engine, expire_on_commit=False) as db:
            yield db
    app.dependency_overrides[get_project_db] = database
    monkeypatch.setattr(logbooks, 'PRIVATE_ROOT', tmp_path / 'private')
    with Session(engine) as db:
        manager = User(id=1, login='manager', name='Gestor', password_hash='unused', role='GESTOR_PROGRAMA', person_type='MILITAR', rank='Cap', war_name='Silva')
        db.add_all([manager,
                    User(id=2, login='team', name='Equipe', password_hash='unused', role='EQUIPE_PROJETO'),
                    User(id=3, login='analyst', name='Analista', password_hash='unused', role='ANALISTA_PROJETOS'),
                    TeamMember(id=1, rank='Cap', full_name='Responsável Técnico', war_name='Silva', user=manager)])
        for i in [1, 2]:
            db.add(Project(id=i, code=f'P{i}', name=f'Projeto {i}', manager='Gestor'))
        db.commit()
        for i, project in [(1, 1), (2, 1), (3, 2)]:
            db.add(Subproject(id=i, project_id=project, code=f'S{i}', wbs_code=f'1.{i}', name=f'Sub {i}',
                             objective='Objetivo', main_product='Produto', manager='Gerente', responsible_unit='OM',
                             planned_start_date=date(2026, 1, 1), planned_end_date=date(2027, 1, 1)))
        db.commit()
        db.add_all([ProjectMember(project_id=i, user_id=1) for i in [1, 2]])
        db.add_all([SubprojectMember(subproject_id=i, user_id=1) for i in [1, 2, 3]])
        db.commit()
    with TestClient(app) as client:
        client.headers['Authorization'] = f'Bearer {create_token("manager", "GESTOR_PROGRAMA")}'
        yield client, engine, tmp_path / 'private'
    app.dependency_overrides.clear()
    engine.dispose()


def book_body(**changes):
    return {'subject_principal': 'Testes de integração', 'registration_date': '2026-10-01', 'responsible_id': 1, **changes}


def create_book(client, **changes):
    response = client.post('/api/logbooks', json=book_body(**changes))
    assert response.status_code == 201, response.text
    return response.json()


def occurrence(client, book_id, *, item_id=None, files=None, **changes):
    body = {'title': 'Ocorrência', 'content': 'Descrição\nSegunda linha', 'event_date': '2026-11-05T10:30:00-03:00', 'type': 'nota', **changes}
    payload = {'payload': json.dumps(body), 'descriptions': json.dumps(['Comprovante'] * len(files or []))}
    path = f'/api/logbooks/{book_id}/items' + (f'/{item_id}' if item_id else '')
    return client.request('PUT' if item_id else 'POST', path, data=payload, files=files)


def test_scope_counts_distinct_projects_and_search(system):
    client, _, _ = system
    assert create_book(client)['scope'] == 'global'
    one = create_book(client, subproject_ids=[1, 2], tags='radar, teste')
    assert one['scope'] == 'projeto'
    assert {p['id'] for p in one['projects']} == {1}
    multi = create_book(client, project_ids=[1], subproject_ids=[3])
    assert multi['scope'] == 'multi_projeto'
    assert len(client.get('/api/logbooks?search=Silva').json()) == 3
    assert len(client.get('/api/logbooks?search=radar').json()) == 1
    assert len(client.get('/api/logbooks?project_id=2').json()) == 1
    assert len(client.get('/api/logbooks?subproject_id=2').json()) == 1
    assert client.put(f'/api/logbooks/{one["id"]}', json=book_body(project_ids=[1, 2])).json()['scope'] == 'multi_projeto'
    assert client.post('/api/logbooks', json=book_body(subproject_ids=[999])).status_code == 422


@pytest.mark.parametrize('terminal_status', ['fechado', 'cancelado'])
def test_terminal_books_freeze_items_attachments_metadata_and_links(system, terminal_status):
    client, _, _ = system
    book = create_book(client)
    other = create_book(client)
    item = occurrence(client, book['id'], files=[('files', ('evidence.pdf', b'%PDF-1.4\nevidence', 'application/pdf'))]).json()
    assert client.put(f'/api/logbooks/{book["id"]}', json=book_body(status='fechado')).status_code == 422
    assert client.put(f'/api/logbooks/{book["id"]}', json=book_body(status=terminal_status, closure_date='2026-11-06' if terminal_status == 'fechado' else None)).status_code == 200
    assert occurrence(client, book['id']).status_code == 409
    assert occurrence(client, book['id'], item_id=item['id']).status_code == 409
    assert client.delete(f'/api/logbooks/{book["id"]}/items/{item["id"]}').status_code == 409
    assert client.delete(f'/api/logbook-attachments/{item["attachments"][0]["id"]}').status_code == 409
    assert client.put(f'/api/logbooks/{book["id"]}', json=book_body()).status_code == 409
    assert client.delete(f'/api/logbooks/{book["id"]}').status_code == 409
    assert client.post(f'/api/logbooks/{other["id"]}/links', json={'target_logbook_id': book['id'], 'link_type': 'relacionado'}).status_code == 409


def test_upload_is_atomic_and_download_requires_authentication(system, monkeypatch):
    client, engine, root = system
    book = create_book(client)
    response = occurrence(client, book['id'], files=[('files', ('valid.pdf', b'%PDF-1.4\nvalid', 'application/pdf')),
                                                   ('files', ('invalid.png', b'not png', 'image/png'))])
    assert response.status_code == 415
    with Session(engine) as db:
        assert db.scalar(select(func.count(LogbookItem.id))) == 0
        assert db.scalar(select(func.count(LogbookItemAttachment.id))) == 0
    assert not root.exists()
    monkeypatch.setattr(logbooks.settings, 'logbook_max_upload_size', 4)
    assert occurrence(client, book['id'], files=[('files', ('large.pdf', b'%PDF-1.4', 'application/pdf'))]).status_code == 413
    monkeypatch.setattr(logbooks.settings, 'logbook_max_upload_size', 20971520)
    item = occurrence(client, book['id'], files=[('files', ('../evidence.pdf', b'%PDF-1.4\nvalid', 'application/pdf'))]).json()
    attachment = item['attachments'][0]
    assert attachment['file_name'] == 'evidence.pdf'
    path = f'/api/logbook-attachments/{attachment["id"]}/download'
    assert client.get(path).content == b'%PDF-1.4\nvalid'
    assert client.get(path, headers={'Authorization': ''}).status_code == 401
    physical = list(root.iterdir())[0]
    assert client.get(f'/uploads/logbook_items/{physical.name}').status_code == 404
    assert client.delete(f'/api/logbooks/{book["id"]}/items/{item["id"]}').status_code == 204
    assert not list(root.iterdir())
    assert client.get(path).status_code == 404


def test_office_content_validation(system):
    client, _, _ = system
    book = create_book(client)
    archive = io.BytesIO()
    with ZipFile(archive, 'w') as doc:
        doc.writestr('[Content_Types].xml', '<Types/>')
        doc.writestr('word/document.xml', '<document/>')
    assert occurrence(client, book['id'], files=[('files', ('report.docx', archive.getvalue(), 'application/octet-stream'))]).status_code == 201
    assert occurrence(client, book['id'], files=[('files', ('report.xlsx', archive.getvalue(), 'application/octet-stream'))]).status_code == 415


def test_integrated_timeline_is_chronological_and_filters_local_dates(system):
    client, _, _ = system
    first = create_book(client, subproject_ids=[1])
    second = create_book(client, subproject_ids=[1, 3])
    unrelated = create_book(client, subproject_ids=[2])
    occurrence(client, first['id'], title='Mais recente', event_date='2026-11-06T23:30:00-03:00', type='risco')
    occurrence(client, second['id'], title='Retroativo', event_date='2026-10-20T08:00:00', type='decisao')
    occurrence(client, unrelated['id'], title='Outro subprojeto')
    items = client.get('/api/logbooks/timeline?subproject_id=1').json()
    assert [i['title'] for i in items] == ['Retroativo', 'Mais recente']
    assert items[0]['event_date'] == '2026-10-20T11:00:00Z'
    filtered = client.get('/api/logbooks/timeline?subproject_id=1&start=2026-11-06&end=2026-11-06&type=risco').json()
    assert len(filtered) == 1
    assert len(client.get(f'/api/logbooks/timeline?subproject_id=1&logbook_id={second["id"]}').json()) == 1
    assert client.get('/api/logbooks/timeline?subproject_id=1&start=2026-11-07&end=2026-11-06').status_code == 422


def test_permissions_and_author_are_enforced(system):
    client, _, _ = system
    book = create_book(client)
    client.headers['Authorization'] = f'Bearer {create_token("team", "EQUIPE_PROJETO")}'
    assert client.get('/api/logbooks').status_code == 200
    assert client.post('/api/logbooks', json=book_body()).status_code == 403
    assert occurrence(client, book['id']).status_code == 403
    assert client.post('/api/team-members', json={'full_name': 'Outro'}).status_code == 403
    client.headers['Authorization'] = f'Bearer {create_token("analyst", "ANALISTA_PROJETOS")}'
    assert occurrence(client, book['id']).json()['created_by'] == 3
    assert occurrence(client, book['id'], created_by=1).status_code == 422


def test_relationships_are_bidirectional_and_cannot_bypass_terminal_history(system):
    client, _, _ = system
    one, two = create_book(client), create_book(client)
    path = f'/api/logbooks/{one["id"]}/links'
    body = {'target_logbook_id': two['id'], 'link_type': 'depende_de', 'observations': 'Aguarda entrega'}
    link = client.post(path, json=body).json()
    assert client.post(path, json=body).status_code == 409
    assert client.post(path, json={**body, 'target_logbook_id': one['id']}).status_code == 422
    assert len(client.get(f'/api/logbooks/{two["id"]}').json()['links']) == 1
    assert client.put(f'/api/logbooks/{two["id"]}', json=book_body(status='cancelado')).status_code == 200
    assert client.delete(f'{path}/{link["id"]}').status_code == 409
    assert client.delete(f'/api/logbooks/{one["id"]}').status_code == 409


def test_member_inactivation_preserves_existing_responsibility(system):
    client, _, _ = system
    book = create_book(client)
    assert client.put('/api/team-members/1', json={'full_name': 'Responsável', 'active': False}).status_code == 200
    assert client.put(f'/api/logbooks/{book["id"]}', json=book_body()).status_code == 200
    assert client.post('/api/logbooks', json=book_body()).status_code == 422


def test_database_failure_cleans_staged_physical_files(system, monkeypatch):
    client, engine, root = system
    book = create_book(client)
    def fail_commit(_):
        raise RuntimeError('Simulated database failure')
    with monkeypatch.context() as patch:
        patch.setattr(Session, 'commit', fail_commit)
        with pytest.raises(RuntimeError, match='Simulated database failure'):
            occurrence(client, book['id'], files=[('files', ('valid.pdf', b'%PDF-1.4\nevidence', 'application/pdf'))])
    assert not list(root.iterdir())
    with Session(engine) as db:
        assert db.scalar(select(func.count(LogbookItem.id))) == 0
        assert db.scalar(select(func.count(LogbookItemAttachment.id))) == 0


def test_individual_attachment_and_open_book_deletion_clean_files(system):
    client, _, root = system
    book = create_book(client)
    item = occurrence(client, book['id'], files=[('files', ('one.pdf', b'%PDF-1.4\none', 'application/pdf')),
                                               ('files', ('two.pdf', b'%PDF-1.4\ntwo', 'application/pdf'))]).json()
    assert len(list(root.iterdir())) == 2
    assert client.delete(f'/api/logbook-attachments/{item["attachments"][0]["id"]}').status_code == 204
    assert len(list(root.iterdir())) == 1
    detail = client.get(f'/api/logbooks/{book["id"]}').json()
    assert len(detail['items'][0]['attachments']) == 1
    assert client.delete(f'/api/logbooks/{book["id"]}').status_code == 204
    assert not list(root.iterdir())
    assert client.get(f'/api/logbooks/{book["id"]}').status_code == 404


@pytest.mark.parametrize('extension,mime,header', [
    ('.mp3', 'audio/mpeg', b'ID3\x04\x00\x00\x00\x00\x00\x00'),
    ('.mp3', 'audio/mpeg', b'\xff\xfb\x90\x00'),
    ('.wav', 'audio/wav', b'RIFF\x24\x00\x00\x00WAVEfmt '),
    ('.ogg', 'audio/ogg', b'OggS\x00\x02'),
    ('.flac', 'audio/flac', b'fLaC\x80\x00\x00\x22'),
    ('.aac', 'audio/aac', b'\xff\xf1\x50\x80\x00\xff\xfc'),
    ('.m4a', 'audio/mp4', b'\x00\x00\x00\x18ftypM4A \x00\x00\x00\x00isommp42'),
    ('.mp4', 'video/mp4', b'\x00\x00\x00\x18ftypisom\x00\x00\x00\x00isommp42'),
    ('.mov', 'video/quicktime', b'\x00\x00\x00\x14ftypqt  \x00\x00\x00\x00qt  '),
    ('.webm', 'video/webm', b'\x1a\x45\xdf\xa3\x87\x42\x82\x84webm'),
    ('.avi', 'video/x-msvideo', b'RIFF\x24\x00\x00\x00AVI LIST'),
])
def test_audio_video_upload_and_authenticated_download(system, extension, mime, header):
    client, _, _ = system
    book = create_book(client)
    response = occurrence(client, book['id'], files=[('files', ('recording' + extension, header, 'application/octet-stream'))])
    assert response.status_code == 201, response.text
    attachment = response.json()['attachments'][0]
    assert attachment['mime_type'] == mime
    download = client.get(f'/api/logbook-attachments/{attachment["id"]}/download')
    assert download.status_code == 200
    assert download.content == header
    assert download.headers['content-type'] == mime


@pytest.mark.parametrize('extension', ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.mp4', '.mov', '.webm', '.avi'])
def test_media_rejects_renamed_documents_without_orphans(system, extension):
    client, engine, root = system
    book = create_book(client)
    response = occurrence(client, book['id'], files=[('files', ('fake' + extension, b'%PDF-1.4\nNot media', 'audio/mpeg'))])
    assert response.status_code == 415
    assert not root.exists()
    with Session(engine) as db:
        assert db.scalar(select(func.count(LogbookItem.id))) == 0


@pytest.mark.parametrize('extension,header', [
    ('.wav', b'RIFF\x24\x00\x00\x00AVI LIST'),
    ('.avi', b'RIFF\x24\x00\x00\x00WAVEfmt '),
    ('.mp4', b'\x00\x00\x00\x14ftypavif\x00\x00\x00\x00avif'),
    ('.webm', b'\x1a\x45\xdf\xa3\x8b\x42\x82\x88matroska'),
])
def test_media_containers_require_compatible_type(extension, header):
    with pytest.raises(logbooks.HTTPException) as error:
        logbooks.validate_content(io.BytesIO(header), extension)
    assert error.value.status_code == 415
