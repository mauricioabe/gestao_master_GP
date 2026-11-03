import re

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.database import get_project_db
from app.models import Project, Subproject
from app.schemas import SubprojectCreate, SubprojectOut, SubprojectUpdate


router = APIRouter(tags=["Subprojetos"])


def _query():
    return select(Subproject).options(
        joinedload(Subproject.project),
        joinedload(Subproject.parent),
        selectinload(Subproject.children),
    )


def _get_or_404(db: Session, subproject_id: int) -> Subproject:
    item = db.scalar(_query().where(Subproject.id == subproject_id, Subproject.active.is_(True)))
    if not item:
        raise HTTPException(404, "Subprojeto nao encontrado")
    return item


def _serialize(item: Subproject) -> dict:
    data = {column.name: getattr(item, column.name) for column in Subproject.__table__.columns}
    data.update({
        "project_name": item.project.name,
        "project_code": item.project.code,
        "parent_name": item.parent.name if item.parent else None,
        "children_count": sum(1 for child in item.children if child.active),
    })
    return data


def _project_or_404(db: Session, project_id: int) -> Project:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.active.is_(True)))
    if not project:
        raise HTTPException(422, "O projeto pai nao existe ou esta inativo")
    return project


def _validate_parent(db: Session, project_id: int, parent_id: int | None) -> Subproject | None:
    if parent_id is None:
        return None
    parent = _get_or_404(db, parent_id)
    if parent.project_id != project_id:
        raise HTTPException(422, "O subprojeto superior deve pertencer ao mesmo projeto SAD")
    return parent


def _next_wbs(db: Session, project_id: int, parent: Subproject | None) -> tuple[str, int]:
    parent_id = parent.id if parent else None
    condition = Subproject.parent_id == parent_id if parent_id else Subproject.parent_id.is_(None)
    last_order = db.scalar(select(func.max(Subproject.sort_order)).where(
        Subproject.project_id == project_id, condition
    )) or 0
    order = int(last_order) + 1
    prefix = parent.wbs_code if parent else "1"
    return f"{prefix}.{order}", order


def _apply(item: Subproject, body: SubprojectCreate | SubprojectUpdate) -> None:
    for field, value in body.model_dump(exclude={"project_id", "parent_id"}).items():
        setattr(item, field, value.strip() if isinstance(value, str) else value)
    item.code = item.code.upper()


def _natural_wbs(item: Subproject) -> tuple[int, ...]:
    return tuple(int(part) for part in item.wbs_code.split("."))


@router.get("/subprojects", response_model=list[SubprojectOut])
def list_subprojects(
    project_id: int | None = None,
    search: str | None = None,
    item_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_project_db),
):
    query = _query().where(Subproject.active.is_(True), Project.active.is_(True)).join(Subproject.project)
    if project_id:
        query = query.where(Subproject.project_id == project_id)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(or_(Subproject.code.like(term), Subproject.name.like(term), Subproject.short_name.like(term)))
    if item_status:
        query = query.where(Subproject.status == item_status)
    items = list(db.scalars(query).unique().all())
    items.sort(key=lambda item: (item.project.code, _natural_wbs(item)))
    return [_serialize(item) for item in items]


@router.get("/projects/{project_id}/subprojects", response_model=list[SubprojectOut])
def project_subprojects(project_id: int, db: Session = Depends(get_project_db)):
    _project_or_404(db, project_id)
    items = list(db.scalars(_query().where(
        Subproject.project_id == project_id, Subproject.active.is_(True)
    )).unique().all())
    items.sort(key=_natural_wbs)
    return [_serialize(item) for item in items]


@router.get("/subprojects/{subproject_id}", response_model=SubprojectOut)
def get_subproject(subproject_id: int, db: Session = Depends(get_project_db)):
    return _serialize(_get_or_404(db, subproject_id))


@router.post("/subprojects", response_model=SubprojectOut, status_code=status.HTTP_201_CREATED)
def create_subproject(body: SubprojectCreate, db: Session = Depends(get_project_db)):
    _project_or_404(db, body.project_id)
    parent = _validate_parent(db, body.project_id, body.parent_id)
    wbs_code, sort_order = _next_wbs(db, body.project_id, parent)
    item = Subproject(project_id=body.project_id, parent_id=body.parent_id, wbs_code=wbs_code, sort_order=sort_order)
    _apply(item, body)
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "O codigo do subprojeto ja existe neste projeto") from exc
    return _serialize(_get_or_404(db, item.id))


@router.put("/subprojects/{subproject_id}", response_model=SubprojectOut)
def update_subproject(subproject_id: int, body: SubprojectUpdate, db: Session = Depends(get_project_db)):
    item = _get_or_404(db, subproject_id)
    if body.project_id != item.project_id or body.parent_id != item.parent_id:
        raise HTTPException(422, "O projeto pai e o nivel hierarquico nao podem ser alterados apos o cadastro")
    _apply(item, body)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "O codigo do subprojeto ja existe neste projeto") from exc
    return _serialize(_get_or_404(db, item.id))


@router.delete("/subprojects/{subproject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subproject(subproject_id: int, db: Session = Depends(get_project_db)):
    item = _get_or_404(db, subproject_id)
    active_children = db.scalar(select(func.count(Subproject.id)).where(
        Subproject.parent_id == item.id, Subproject.active.is_(True)
    )) or 0
    if active_children:
        raise HTTPException(409, "Exclua primeiro os subprojetos subordinados")
    item.active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
