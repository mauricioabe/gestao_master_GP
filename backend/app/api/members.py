from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_permissions
from app.core.database import get_project_db
from app.core.permissions import MANAGE_PROJECTS, MANAGE_SUBPROJECTS, VIEW_PROJECTS
from app.models import Project, ProjectMember, Subproject, SubprojectMember, TeamMember, User
from app.schemas import AssignmentUserOut
from app.user_identity import assignment_user_data

router = APIRouter(tags=['Integrantes de projetos e subprojetos'])


class AddMember(BaseModel):
    user_id: int = Field(gt=0)


class ScopeMemberOut(AssignmentUserOut):
    added_at: datetime


def scope_or_404(db, scope, identifier):
    if scope == 'project':
        entity = db.scalar(select(Project).where(Project.id == identifier, Project.active.is_(True)))
        model, key = ProjectMember, ProjectMember.project_id
    else:
        entity = db.scalar(select(Subproject).join(Subproject.project).where(Subproject.id == identifier, Subproject.active.is_(True), Project.active.is_(True)))
        model, key = SubprojectMember, SubprojectMember.subproject_id
    if not entity:
        raise HTTPException(404, 'Projeto ou subprojeto não encontrado')
    return model, key


def list_members(db, scope, identifier):
    model, key = scope_or_404(db, scope, identifier)
    members = db.scalars(select(model).options(joinedload(model.user)).where(key == identifier)).all()
    return sorted([{**assignment_user_data(member.user), 'added_at': member.added_at} for member in members], key=lambda member: member['display_name'].casefold())


def add_member(db, scope, identifier, user_id):
    model, key = scope_or_404(db, scope, identifier)
    user = db.get(User, user_id)
    if not user or not user.active:
        raise HTTPException(422, 'Selecione um usuário ativo cadastrado no sistema')
    if db.scalar(select(model).where(key == identifier, model.user_id == user_id)):
        raise HTTPException(409, 'Usuário já vinculado a este projeto ou subprojeto')
    member = model(**{key.key: identifier, 'user_id': user_id})
    db.add(member)
    # Make the same registered user available as a diary responsible without
    # duplicating identities. This registry is separate from each scope's roster.
    if not db.scalar(select(TeamMember.id).where(TeamMember.user_id == user_id)):
        db.add(TeamMember(user_id=user_id, full_name=user.name, rank=user.rank or '', war_name=user.war_name or '', active=True))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, 'O vínculo já foi registrado. Atualize a lista de integrantes.') from exc
    return {**assignment_user_data(user), 'added_at': member.added_at}


def remove_member(db, scope, identifier, user_id):
    model, key = scope_or_404(db, scope, identifier)
    member = db.scalar(select(model).where(key == identifier, model.user_id == user_id))
    if not member:
        raise HTTPException(404, 'Integrante não vinculado a este projeto ou subprojeto')
    db.delete(member)
    db.commit()
    return Response(status_code=204)


@router.get('/projects/{project_id}/members', response_model=list[ScopeMemberOut])
def project_members(project_id: int, db: Session = Depends(get_project_db), _: User = Depends(require_permissions(VIEW_PROJECTS))):
    return list_members(db, 'project', project_id)


@router.post('/projects/{project_id}/members', response_model=ScopeMemberOut, status_code=201)
def add_project_member(project_id: int, body: AddMember, db: Session = Depends(get_project_db), _: User = Depends(require_permissions(MANAGE_PROJECTS))):
    return add_member(db, 'project', project_id, body.user_id)


@router.delete('/projects/{project_id}/members/{user_id}', status_code=204)
def remove_project_member(project_id: int, user_id: int, db: Session = Depends(get_project_db), _: User = Depends(require_permissions(MANAGE_PROJECTS))):
    return remove_member(db, 'project', project_id, user_id)


@router.get('/subprojects/{subproject_id}/members', response_model=list[ScopeMemberOut])
def subproject_members(subproject_id: int, db: Session = Depends(get_project_db), _: User = Depends(require_permissions(VIEW_PROJECTS))):
    return list_members(db, 'subproject', subproject_id)


@router.post('/subprojects/{subproject_id}/members', response_model=ScopeMemberOut, status_code=201)
def add_subproject_member(subproject_id: int, body: AddMember, db: Session = Depends(get_project_db), _: User = Depends(require_permissions(MANAGE_SUBPROJECTS))):
    return add_member(db, 'subproject', subproject_id, body.user_id)


@router.delete('/subprojects/{subproject_id}/members/{user_id}', status_code=204)
def remove_subproject_member(subproject_id: int, user_id: int, db: Session = Depends(get_project_db), _: User = Depends(require_permissions(MANAGE_SUBPROJECTS))):
    return remove_member(db, 'subproject', subproject_id, user_id)
