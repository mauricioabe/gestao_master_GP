from decimal import Decimal
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_cost_db, get_project_db
from app.models import Project, ProjectContract, ProjectDocument, ProjectOm
from app.schemas import ProjectCreate, ProjectOut, ProjectUpdate


router = APIRouter(tags=["Projetos"])

CMAS = [
    {"code": "CMA", "name": "Comando Militar da Amazonia"},
    {"code": "CMN", "name": "Comando Militar do Norte"},
    {"code": "CMNE", "name": "Comando Militar do Nordeste"},
    {"code": "CMO", "name": "Comando Militar do Oeste"},
    {"code": "CMP", "name": "Comando Militar do Planalto"},
    {"code": "CML", "name": "Comando Militar do Leste"},
    {"code": "CMSE", "name": "Comando Militar do Sudeste"},
    {"code": "CMS", "name": "Comando Militar do Sul"},
]
OMS = [
    "1a Brigada de Infantaria de Selva", "2a Brigada de Infantaria de Selva",
    "4a Brigada de Cavalaria Mecanizada", "5a Brigada de Cavalaria Blindada",
    "6a Divisao de Exercito", "9a Regiao Militar", "10a Regiao Militar",
    "13a Brigada de Infantaria Motorizada", "13o Pelotao de Policia do Exercito",
    "17o Batalhao de Fronteira", "18a Brigada de Infantaria de Pantanal",
    "18a Companhia de Comunicacoes", "18o Grupo de Artilharia de Campanha",
    "2o Batalhao de Fronteira", "3o Batalhao de Comunicacoes",
    "4o Centro de Geoinformacao", "6o Batalhao de Inteligencia Militar",
    "Centro de Comunicacoes e Guerra Eletronica do Exercito",
    "Centro Integrado de Telematica do Exercito", "Comando de Operacoes Terrestres",
]


def _load_options():
    return (selectinload(Project.contracts), selectinload(Project.oms), selectinload(Project.documents))


def _project_or_404(db: Session, project_id: int) -> Project:
    project = db.scalar(select(Project).options(*_load_options()).where(Project.id == project_id, Project.active.is_(True)))
    if not project:
        raise HTTPException(404, "Projeto nao encontrado")
    return project


def _apply(project: Project, body: ProjectCreate | ProjectUpdate) -> None:
    for field, value in body.model_dump(exclude={"contracts", "oms", "documents"}).items():
        setattr(project, field, value.strip() if isinstance(value, str) else value)
    project.code = project.code.upper()


def _append_children(project: Project, body: ProjectCreate | ProjectUpdate) -> None:
    for item in body.contracts:
        project.contracts.append(ProjectContract(**item.model_dump()))
    for item in body.oms:
        project.oms.append(ProjectOm(**item.model_dump()))
    for item in body.documents:
        project.documents.append(ProjectDocument(**item.model_dump()))


def _sync_children(project: Project, body: ProjectUpdate, db: Session) -> None:
    project.contracts.clear()
    project.oms.clear()
    project.documents.clear()
    db.flush()
    _append_children(project, body)


def _commit(db: Session, duplicate_message: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, duplicate_message) from exc


def _natural_key(project: Project):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", project.code)]


@router.get("/project-options")
def project_options():
    return {"cmas": CMAS, "oms": OMS}


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(
    search: str | None = None,
    code: str | None = None,
    phase: str | None = None,
    cma: str | None = None,
    project_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_project_db),
):
    query = select(Project).options(*_load_options()).where(Project.active.is_(True))
    if search:
        term = f"%{search.strip()}%"
        query = query.where(or_(Project.name.like(term), Project.manager.like(term), Project.description.like(term)))
    if code:
        query = query.where(Project.code.like(f"%{code.strip()}%"))
    if phase:
        query = query.where(Project.phase == phase)
    if cma:
        query = query.where(Project.cma == cma)
    if project_status:
        query = query.where(Project.status == project_status)
    projects = list(db.scalars(query).unique().all())
    return sorted(projects, key=_natural_key)


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_project_db)):
    return _project_or_404(db, project_id)


@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, db: Session = Depends(get_project_db)):
    project = Project()
    _apply(project, body)
    _append_children(project, body)
    db.add(project)
    _commit(db, "A sigla do projeto ou algum vinculo ja esta cadastrado")
    return _project_or_404(db, project.id)


@router.put("/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, body: ProjectUpdate, db: Session = Depends(get_project_db)):
    project = _project_or_404(db, project_id)
    _apply(project, body)
    _sync_children(project, body, db)
    _commit(db, "A sigla do projeto ou algum vinculo esta duplicado")
    return _project_or_404(db, project.id)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_project_db)):
    project = _project_or_404(db, project_id)
    project.active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/contracts")
def list_contracts(
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_cost_db),
):
    where = ""
    params: dict = {"limit": limit}
    if search:
        where = """WHERE c.cod_contrato LIKE :search OR c.numero_contrato LIKE :search
            OR c.objeto LIKE :search OR c.nome_fornecedor LIKE :search"""
        params["search"] = f"%{search.strip()}%"
    rows = db.execute(text(f"""SELECT c.cod_contrato AS external_contract_id,
            COALESCE(c.numero_contrato, c.cod_contrato) AS contract_number,
            c.objeto AS contract_object, c.nome_fornecedor AS supplier_name,
            c.valor_global AS global_value, c.status,
            c.data_inicio_vigencia AS start_date, c.data_fim_vigencia AS end_date
        FROM contrato c {where}
        ORDER BY c.ano_contrato DESC, c.cod_contrato
        LIMIT :limit"""), params).mappings().all()
    return [dict(row) for row in rows]


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_project_db)):
    active_filter = Project.active.is_(True)
    total = db.scalar(select(func.count(Project.id)).where(active_filter)) or 0
    avg_progress = db.scalar(select(func.avg(Project.progress)).where(active_filter)) or 0
    active = db.scalar(select(func.count(Project.id)).where(active_filter, Project.phase == "EXECUCAO")) or 0
    delayed = db.scalar(select(func.count(Project.id)).where(active_filter, Project.status == "ATRASADO")) or 0
    contracts = db.scalar(select(func.count(ProjectContract.id)).join(Project).where(active_filter)) or 0
    by_status = db.execute(select(Project.phase, func.count(Project.id)).where(active_filter).group_by(Project.phase)).all()
    return {
        "total_projects": total,
        "active_projects": active,
        "delayed_projects": delayed,
        "linked_contracts": contracts,
        "average_progress": round(float(avg_progress), 1),
        "by_status": [{"status": item[0], "total": item[1]} for item in by_status],
    }