"""Diário de bordo: history, private evidence and relationships."""
import json
import logging
from datetime import datetime, time, timezone, date
from pathlib import Path
from tempfile import SpooledTemporaryFile
from uuid import uuid4
from zipfile import BadZipFile, ZipFile
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.deps import current_user
from app.core.config import settings
from app.core.database import get_project_db
from app.logbook_schemas import LogbookInput, LogbookItemInput, LogbookLinkInput, TeamMemberInput
from app.user_identity import assignment_user_data
from app.models import (Logbook, LogbookItem, LogbookItemAttachment, LogbookLink,
                        Project, ProjectMember, Subproject, SubprojectMember, TeamMember, User)

router = APIRouter(tags=['Diário de bordo'])
PRIVATE_ROOT = Path(__file__).resolve().parents[3] / 'private_storage' / 'logbook_items'
TERMINAL = {'fechado', 'cancelado'}
MIMES = {
    '.pdf': 'application/pdf', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
    '.png': 'image/png', '.tif': 'image/tiff', '.tiff': 'image/tiff',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.mpp': 'application/vnd.ms-project',
    '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.ogg': 'audio/ogg',
    '.m4a': 'audio/mp4', '.aac': 'audio/aac', '.flac': 'audio/flac',
    '.mp4': 'video/mp4', '.webm': 'video/webm', '.mov': 'video/quicktime',
    '.avi': 'video/x-msvideo',
}


def get_book(db, book_id, *, lock=False):
    query = select(Logbook).where(Logbook.id == book_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    book = db.scalar(query)
    if not book:
        raise HTTPException(404, 'Assunto não encontrado')
    return book


def writable(book):
    if book.status in TERMINAL:
        raise HTTPException(409, 'Assunto fechado ou cancelado: histórico disponível somente para consulta')


def member_data(member):
    if member.user:
        user = assignment_user_data(member.user)
        return {'id': member.id, 'user_id': user['id'], 'rank': user['rank'] or '',
                'full_name': user['name'], 'war_name': user['war_name'] or '',
                'active': member.active and user['active'], 'member_active': member.active,
                'display_name': user['assignment_label'], 'user': user}
    return {'id': member.id, 'rank': member.rank, 'full_name': member.full_name,
            'war_name': member.war_name, 'active': member.active,
            'member_active': member.active, 'user_id': None, 'user': None,
            'display_name': ' '.join(part for part in [member.rank, member.war_name or member.full_name] if part)}


def attachment_data(attachment):
    return {key: getattr(attachment, key) for key in ['id', 'file_name', 'mime_type', 'file_size', 'description']}


def item_data(item):
    return {**{key: getattr(item, key) for key in ['id', 'logbook_id', 'title', 'content', 'type', 'references_text', 'created_by']},
            'event_date': item.event_date.isoformat() + 'Z',
            'created_at': item.created_at.isoformat() + 'Z',
            'updated_at': item.updated_at.isoformat() + 'Z',
            'author_name': item.author.display_name, 'subject_principal': item.logbook.subject_principal,
            'logbook_status': item.logbook.status,
            'attachments': [attachment_data(a) for a in item.attachments]}


def book_data(db, book, detail=False):
    projects = {p.id: p for p in book.projects}
    projects.update({s.project_id: s.project for s in book.subprojects})
    count, last_event = db.execute(select(func.count(LogbookItem.id), func.max(LogbookItem.event_date)).where(LogbookItem.logbook_id == book.id)).one()
    data = {key: getattr(book, key) for key in ['id', 'subject_principal', 'description', 'status', 'registration_date', 'closure_date', 'responsible_id', 'created_by', 'tags', 'created_at', 'updated_at']}
    data.update(scope='global' if not projects else 'projeto' if len(projects) == 1 else 'multi_projeto',
                relator_ids=[m.id for m in book.relators], relators=[member_data(m) for m in book.relators],
                responsible=member_data(book.responsible), project_ids=[p.id for p in book.projects],
                subproject_ids=[s.id for s in book.subprojects],
                projects=[{'id': p.id, 'code': p.code, 'name': p.name} for p in projects.values()],
                subprojects=[{'id': s.id, 'code': s.code, 'name': s.name, 'project_id': s.project_id} for s in book.subprojects],
                item_count=count, last_event_date=last_event.isoformat() + 'Z' if last_event else None)
    if detail:
        data['items'] = [item_data(i) for i in book.items]
        links = db.scalars(select(LogbookLink).where(or_(LogbookLink.source_logbook_id == book.id, LogbookLink.target_logbook_id == book.id))).all()
        data['links'] = [{**{key: getattr(link, key) for key in ['id', 'source_logbook_id', 'target_logbook_id', 'link_type', 'observations']},
                          'source_title': get_book(db, link.source_logbook_id).subject_principal,
                          'target_title': get_book(db, link.target_logbook_id).subject_principal} for link in links]
    return data


def eligible_relator_users(project_ids, subproject_ids):
    projects = select(ProjectMember.user_id).join(Project, Project.id == ProjectMember.project_id).where(Project.active.is_(True))
    subs = select(SubprojectMember.user_id).join(Subproject, Subproject.id == SubprojectMember.subproject_id).join(Project, Project.id == Subproject.project_id).where(Subproject.active.is_(True), Project.active.is_(True))
    if project_ids or subproject_ids:
        projects = projects.where(ProjectMember.project_id.in_(project_ids))
        subs = subs.where(SubprojectMember.subproject_id.in_(subproject_ids))
    return projects.union(subs)


def apply_book(db, book, body):
    project_ids, subproject_ids = set(body.project_ids), set(body.subproject_ids)
    projects = list(db.scalars(select(Project).where(Project.id.in_(project_ids), Project.active.is_(True))))
    subs = list(db.scalars(select(Subproject).join(Subproject.project).where(Subproject.id.in_(subproject_ids), Subproject.active.is_(True), Project.active.is_(True))))
    # Previously linked inactive entities may remain for historical context.
    existing_projects = {p.id: p for p in book.projects} if book.id else {}
    existing_subs = {s.id: s for s in book.subprojects} if book.id else {}
    projects += [existing_projects[i] for i in project_ids - {p.id for p in projects} if i in existing_projects]
    subs += [existing_subs[i] for i in subproject_ids - {s.id for s in subs} if i in existing_subs]
    if len(projects) != len(project_ids) or len(subs) != len(subproject_ids):
        raise HTTPException(422, 'Projeto ou subprojeto inexistente ou inativo')
    identifiers = list(dict.fromkeys(body.relator_ids if body.relator_ids is not None else [body.responsible_id]))
    eligible_users = set(db.scalars(eligible_relator_users(project_ids, subproject_ids)))
    existing_relators = {m.id for m in book.relators} if book.id else set()
    if book.id:
        existing_relators.add(book.responsible_id)
    unchanged_scope = (project_ids == {p.id for p in book.projects} and subproject_ids == {s.id for s in book.subprojects}) if book.id else False
    relators = []
    for identifier in identifiers:
        member = db.get(TeamMember, identifier)
        retained = identifier in existing_relators and unchanged_scope
        if not member or (not retained and (not member_data(member)['active'] or member.user_id not in eligible_users)):
            raise HTTPException(422, 'Selecione somente relatores ativos integrantes dos projetos ou subprojetos vinculados')
        relators.append(member)
    for key, value in body.model_dump(exclude={'project_ids', 'subproject_ids', 'relator_ids', 'responsible_id'}).items():
        setattr(book, key, value)
    book.relators = relators
    # Compatibility for existing clients and the original non-null foreign key.
    book.responsible, book.responsible_id = relators[0], relators[0].id
    book.projects, book.subprojects = projects, subs
    effective = project_ids | {s.project_id for s in subs}
    book.scope = 'global' if not effective else 'projeto' if len(effective) == 1 else 'multi_projeto'


@router.get('/team-members')
def list_members(project_ids: list[int] = Query(default=[]), subproject_ids: list[int] = Query(default=[]),
                 db: Session = Depends(get_project_db)):
    query = select(TeamMember).options(joinedload(TeamMember.user)).order_by(TeamMember.full_name)
    if project_ids or subproject_ids:
        users = select(ProjectMember.user_id).where(ProjectMember.project_id.in_(project_ids)).union(
            select(SubprojectMember.user_id).where(SubprojectMember.subproject_id.in_(subproject_ids)))
        query = query.where(TeamMember.user_id.in_(users))
    return [member_data(m) for m in db.scalars(query)]


@router.get('/logbooks/relator-options')
def relator_options(project_ids: list[int] = Query(default=[]), subproject_ids: list[int] = Query(default=[]), db: Session = Depends(get_project_db)):
    query = select(TeamMember).join(TeamMember.user).options(joinedload(TeamMember.user)).where(
        TeamMember.active.is_(True), User.active.is_(True), TeamMember.user_id.in_(eligible_relator_users(project_ids, subproject_ids)))
    return [member_data(m) for m in db.scalars(query.order_by(TeamMember.full_name))]


def set_member_user(db, member, user_id):
    user = db.get(User, user_id) if user_id else None
    if not user or not user.active:
        raise HTTPException(422, 'Selecione um usuário ativo cadastrado no sistema')
    if member.user_id and member.user_id != user_id:
        raise HTTPException(409, 'Este integrante já está vinculado a outro usuário')
    duplicate = db.scalar(select(TeamMember).where(TeamMember.user_id == user_id))
    if duplicate and duplicate.id != member.id:
        raise HTTPException(409, 'Este usuário já está cadastrado como integrante')
    member.user = user
    member.user_id = user.id
    member.full_name = user.name
    member.rank = user.rank or ''
    member.war_name = user.war_name or ''


def commit_member(db):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, 'Este usuário já está cadastrado como integrante') from exc


@router.post('/team-members', status_code=201)
def create_member(body: TeamMemberInput, db: Session = Depends(get_project_db)):
    member = TeamMember(active=body.active)
    set_member_user(db, member, body.user_id)
    db.add(member)
    commit_member(db)
    return member_data(member)


@router.put('/team-members/{member_id}')
def update_member(member_id: int, body: TeamMemberInput, db: Session = Depends(get_project_db)):
    member = db.get(TeamMember, member_id)
    if not member:
        raise HTTPException(404, 'Integrante não encontrado')
    if 'user_id' in body.model_fields_set:
        if body.user_id is None:
            raise HTTPException(422, 'Não é permitido remover o vínculo com o usuário')
        if body.user_id != member.user_id:
            set_member_user(db, member, body.user_id)
    member.active = body.active
    commit_member(db)
    return member_data(member)


def filtered_books(search=None, status=None, project_id=None, subproject_id=None):
    query = select(Logbook)
    if search:
        term = f'%{search.strip()}%'
        matching_member = or_(TeamMember.full_name.like(term), TeamMember.war_name.like(term), TeamMember.user.has(or_(User.name.like(term), User.war_name.like(term))))
        query = query.where(or_(Logbook.subject_principal.contains(search.strip(), autoescape=True), Logbook.tags.contains(search.strip(), autoescape=True), Logbook.relators.any(matching_member)))
    if status:
        query = query.where(Logbook.status == status)
    if project_id:
        query = query.where(or_(Logbook.projects.any(Project.id == project_id), Logbook.subprojects.any(Subproject.project_id == project_id)))
    if subproject_id:
        query = query.where(Logbook.subprojects.any(Subproject.id == subproject_id))
    return query


@router.get('/logbooks')
def list_books(search: str | None = None, status: str | None = None, project_id: int | None = None,
               subproject_id: int | None = None, db: Session = Depends(get_project_db)):
    return [book_data(db, b) for b in db.scalars(filtered_books(search, status, project_id, subproject_id).order_by(Logbook.updated_at.desc(), Logbook.id.desc()))]


@router.get('/logbooks/timeline')
def timeline(subproject_id: int, logbook_id: int | None = None, type: str | None = None,
             start: date | None = None, end: date | None = None, db: Session = Depends(get_project_db)):
    if not db.get(Subproject, subproject_id):
        raise HTTPException(404, 'Subprojeto não encontrado')
    if start and end and start > end:
        raise HTTPException(422, 'Período inválido')
    query = select(LogbookItem).join(LogbookItem.logbook).where(Logbook.subprojects.any(Subproject.id == subproject_id))
    if logbook_id:
        query = query.where(LogbookItem.logbook_id == logbook_id)
    if type:
        query = query.where(LogbookItem.type == type)
    if start:
        boundary = datetime.combine(start, time.min, ZoneInfo('America/Sao_Paulo')).astimezone(timezone.utc).replace(tzinfo=None)
        query = query.where(LogbookItem.event_date >= boundary)
    if end:
        boundary = datetime.combine(end, time.max, ZoneInfo('America/Sao_Paulo')).astimezone(timezone.utc).replace(tzinfo=None)
        query = query.where(LogbookItem.event_date <= boundary)
    return [item_data(i) for i in db.scalars(query.order_by(LogbookItem.event_date, LogbookItem.id))]


@router.post('/logbooks', status_code=201)
def create_book(body: LogbookInput, db: Session = Depends(get_project_db), user: User = Depends(current_user)):
    book = Logbook(created_by=user.id)
    apply_book(db, book, body)
    db.add(book)
    db.commit()
    return book_data(db, book, True)


@router.get('/logbooks/{book_id}')
def show_book(book_id: int, db: Session = Depends(get_project_db)):
    return book_data(db, get_book(db, book_id), True)


@router.put('/logbooks/{book_id}')
def update_book(book_id: int, body: LogbookInput, db: Session = Depends(get_project_db)):
    book = get_book(db, book_id, lock=True)
    writable(book)
    apply_book(db, book, body)
    db.commit()
    return book_data(db, book, True)


def remove_files(names):
    for name in names:
        try:
            (PRIVATE_ROOT / name).unlink(missing_ok=True)
        except OSError:
            logging.exception('Falha ao remover anexo privado %s', name)


@router.delete('/logbooks/{book_id}', status_code=204)
def delete_book(book_id: int, db: Session = Depends(get_project_db)):
    book = get_book(db, book_id, lock=True)
    writable(book)
    related = list(db.scalars(select(LogbookLink).where(or_(LogbookLink.source_logbook_id == book_id, LogbookLink.target_logbook_id == book_id))))
    for link in related:
        other = get_book(db, link.target_logbook_id if link.source_logbook_id == book_id else link.source_logbook_id)
        writable(other)
    names = [a.stored_name for i in book.items for a in i.attachments]
    db.execute(delete(LogbookLink).where(or_(LogbookLink.source_logbook_id == book_id, LogbookLink.target_logbook_id == book_id)))
    db.delete(book)
    db.commit()
    remove_files(names)
    return Response(status_code=204)


def validate_content(stream, extension):
    head = stream.read(4096)
    stream.seek(0)
    valid = False
    if extension == '.pdf':
        valid = head.startswith(b'%PDF-')
    elif extension in {'.jpg', '.jpeg'}:
        valid = head.startswith(b'\xff\xd8\xff')
    elif extension == '.png':
        valid = head.startswith(b'\x89PNG\r\n\x1a\n')
    elif extension in {'.tif', '.tiff'}:
        valid = head.startswith((b'II*\x00', b'MM\x00*'))
    elif extension == '.mpp':
        valid = head.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1')
    elif extension == '.mp3':
        valid = head.startswith(b'ID3') or (
            len(head) >= 4 and head[0] == 0xff and head[1] & 0xe0 == 0xe0
            and head[1] & 0x18 != 0x08 and head[1] & 0x06 != 0
            and head[2] & 0xf0 not in {0, 0xf0} and head[2] & 0x0c != 0x0c
        )
    elif extension in {'.wav', '.avi'}:
        valid = head.startswith(b'RIFF') and head[8:12] == (b'WAVE' if extension == '.wav' else b'AVI ')
    elif extension == '.ogg':
        valid = head.startswith(b'OggS\x00')
    elif extension == '.flac':
        valid = head.startswith(b'fLaC')
    elif extension == '.aac':
        valid = len(head) >= 7 and head[0] == 0xff and head[1] & 0xf6 == 0xf0
    elif extension in {'.mp4', '.m4a', '.mov'}:
        # ISO Base Media / QuickTime containers: check the file-type box and brand.
        brands = {b'isom', b'iso2', b'iso3', b'iso4', b'iso5', b'iso6', b'iso8',
                  b'iso9', b'mp41', b'mp42', b'avc1', b'dash', b'M4A ', b'M4B ',
                  b'M4V ', b'qt  ', b'MSNV', b'3gp4', b'3gp5', b'3gp6'}
        box_size = int.from_bytes(head[:4], 'big')
        valid = (len(head) >= 16 and head[4:8] == b'ftyp' and box_size >= 16
                 and (head[8:12] in brands or any(head[i:i+4] in brands for i in range(16, min(box_size, len(head)) - 3, 4))))
    elif extension == '.webm':
        valid = head.startswith(b'\x1a\x45\xdf\xa3') and b'\x42\x82\x84webm' in head
    else:
        try:
            with ZipFile(stream) as archive:
                names = set(archive.namelist())
                folder = {'.docx': 'word/', '.xlsx': 'xl/', '.pptx': 'ppt/'}[extension]
                valid = '[Content_Types].xml' in names and any(n.startswith(folder) for n in names)
        except (BadZipFile, KeyError):
            valid = False
    stream.seek(0)
    if not valid:
        raise HTTPException(415, 'Conteúdo do arquivo incompatível com a extensão informada')


async def stage_uploads(files, descriptions):
    staged = []
    try:
        if len(files) > 20 or len(files) != len(descriptions):
            raise HTTPException(422, 'Informe uma descrição por arquivo; máximo de 20 anexos por envio')
        total = 0
        for file, description in zip(files, descriptions):
            name = Path((file.filename or '').replace('\\', '/')).name
            extension = Path(name).suffix.lower()
            if extension not in MIMES or len(name) > 255 or len(description) > 500:
                raise HTTPException(415, 'Nome, descrição ou extensão de anexo inválida')
            stream = SpooledTemporaryFile(max_size=1024 * 1024)
            staged.append((stream, name, extension, description, 0))
            size = 0
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                total += len(chunk)
                if size > settings.logbook_max_upload_size or total > settings.logbook_max_batch_size:
                    raise HTTPException(413, 'Limite de tamanho dos anexos excedido')
                stream.write(chunk)
            if size == 0:
                raise HTTPException(422, 'Arquivo vazio não permitido')
            stream.seek(0)
            validate_content(stream, extension)
            staged[-1] = (stream, name, extension, description, size)
        return staged
    except BaseException:
        for stream, *_ in staged:
            stream.close()
        raise
    finally:
        for file in files:
            await file.close()


async def save_item(db, book_id, item_id, payload, files, descriptions, user_id):
    try:
        body = LogbookItemInput.model_validate_json(payload)
        desc = json.loads(descriptions)
        if not isinstance(desc, list) or any(not isinstance(d, str) for d in desc):
            raise ValueError()
    except (ValidationError, ValueError, TypeError) as exc:
        raise HTTPException(422, 'Dados da ocorrência ou descrições inválidos') from exc
    staged = await stage_uploads(files, desc)
    names = []
    try:
        book = get_book(db, book_id, lock=True)
        writable(book)
        item = db.get(LogbookItem, item_id) if item_id else LogbookItem(logbook_id=book_id, created_by=user_id)
        if not item or item.logbook_id != book_id:
            raise HTTPException(404, 'Ocorrência não encontrada')
        for key, value in body.model_dump().items():
            setattr(item, key, value)
        db.add(item)
        PRIVATE_ROOT.mkdir(parents=True, exist_ok=True)
        for stream, filename, extension, description, size in staged:
            stored = f'lba_{uuid4().hex}{extension}'
            names.append(stored)
            with (PRIVATE_ROOT / stored).open('xb') as output:
                while chunk := stream.read(1024 * 1024):
                    output.write(chunk)
            item.attachments.append(LogbookItemAttachment(file_name=filename, stored_name=stored,
                mime_type=MIMES[extension], file_size=size, description=description))
        book.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
    except BaseException:
        db.rollback()
        remove_files(names)
        raise
    finally:
        for stream, *_ in staged:
            stream.close()
    db.refresh(item)
    return item_data(item)


@router.post('/logbooks/{book_id}/items', status_code=201)
async def create_item(book_id: int, payload: str = Form(...), descriptions: str = Form('[]'), files: list[UploadFile] = File(default=[]),
                      db: Session = Depends(get_project_db), user: User = Depends(current_user)):
    return await save_item(db, book_id, None, payload, files, descriptions, user.id)


@router.put('/logbooks/{book_id}/items/{item_id}')
async def update_item(book_id: int, item_id: int, payload: str = Form(...), descriptions: str = Form('[]'), files: list[UploadFile] = File(default=[]),
                      db: Session = Depends(get_project_db), user: User = Depends(current_user)):
    return await save_item(db, book_id, item_id, payload, files, descriptions, user.id)


@router.delete('/logbooks/{book_id}/items/{item_id}', status_code=204)
def delete_item(book_id: int, item_id: int, db: Session = Depends(get_project_db)):
    writable(get_book(db, book_id, lock=True))
    item = db.get(LogbookItem, item_id)
    if not item or item.logbook_id != book_id:
        raise HTTPException(404, 'Ocorrência não encontrada')
    names = [a.stored_name for a in item.attachments]
    db.delete(item)
    db.commit()
    remove_files(names)
    return Response(status_code=204)


@router.get('/logbook-attachments/{attachment_id}/download')
def download_attachment(attachment_id: int, db: Session = Depends(get_project_db)):
    attachment = db.get(LogbookItemAttachment, attachment_id)
    if not attachment or not (PRIVATE_ROOT / attachment.stored_name).is_file():
        raise HTTPException(404, 'Anexo não encontrado')
    return FileResponse(PRIVATE_ROOT / attachment.stored_name, filename=attachment.file_name,
                        media_type=attachment.mime_type, headers={'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-store'})


@router.delete('/logbook-attachments/{attachment_id}', status_code=204)
def delete_attachment(attachment_id: int, db: Session = Depends(get_project_db)):
    attachment = db.get(LogbookItemAttachment, attachment_id)
    if not attachment:
        raise HTTPException(404, 'Anexo não encontrado')
    item = db.get(LogbookItem, attachment.item_id)
    writable(get_book(db, item.logbook_id, lock=True))
    name = attachment.stored_name
    db.delete(attachment)
    db.commit()
    remove_files([name])
    return Response(status_code=204)


@router.post('/logbooks/{book_id}/links', status_code=201)
def create_link(book_id: int, body: LogbookLinkInput, db: Session = Depends(get_project_db)):
    if book_id == body.target_logbook_id:
        raise HTTPException(422, 'Um assunto não pode relacionar-se consigo mesmo')
    for identifier in sorted([book_id, body.target_logbook_id]):
        writable(get_book(db, identifier, lock=True))
    link = LogbookLink(source_logbook_id=book_id, **body.model_dump())
    db.add(link)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, 'Relacionamento já cadastrado') from exc
    return {'id': link.id}


@router.delete('/logbooks/{book_id}/links/{link_id}', status_code=204)
def delete_link(book_id: int, link_id: int, db: Session = Depends(get_project_db)):
    link = db.get(LogbookLink, link_id)
    if not link or book_id not in {link.source_logbook_id, link.target_logbook_id}:
        raise HTTPException(404, 'Relacionamento não encontrado')
    for identifier in sorted([link.source_logbook_id, link.target_logbook_id]):
        writable(get_book(db, identifier, lock=True))
    db.delete(link)
    db.commit()
    return Response(status_code=204)
