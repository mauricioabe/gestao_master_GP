from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import bindparam, select, text
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.database import get_cost_db, get_project_db
from app.models import Project, Subproject, SubprojectContract
from app.schemas import SubprojectContractsInput


router = APIRouter(tags=["Contratos do subprojeto"])

# Itens contabeis do Radar Financeiro usados nos paineis de execucao.
ITEM_EMPENHADO, ITEM_LIQUIDADO, ITEM_PAGO = 29, 31, 34

CONTRACT_COLUMNS = """c.cod_contrato AS external_contract_id,
    COALESCE(c.numero_contrato, c.cod_contrato) AS contract_number,
    COALESCE(c.objeto, c.descricao) AS contract_object,
    COALESCE(c.nome_fantasia_fornecedor, c.nome_fornecedor) AS supplier_name,
    c.valor_global AS global_value, c.status,
    c.data_inicio_vigencia AS start_date, c.data_fim_vigencia AS end_date,
    c.cod_instrumento AS instrument_code,
    c.cod_ug_contratante AS contracting_uasg,
    c.abrangencia AS coverage,
    c.tipo_contrato AS contract_type,
    c.acao_orcamentaria AS budget_action,
    c.numero_processo AS process_number,
    c.fundamento_legal AS legal_basis"""


def _subproject(db: Session, subproject_id: int) -> Subproject:
    item = db.scalar(select(Subproject).options(
        joinedload(Subproject.project), selectinload(Subproject.contracts)
    ).where(Subproject.id == subproject_id, Subproject.active.is_(True)))
    if not item:
        raise HTTPException(404, "Subprojeto nao encontrado")
    return item


def _radar_project(cost_db: Session, project_code: str) -> str | None:
    """Projeto do Radar com a mesma sigla do projeto SAD (ex.: SAD3)."""
    return cost_db.execute(
        text("SELECT cod_projeto FROM projeto WHERE UPPER(TRIM(descricao)) = :code LIMIT 1"),
        {"code": project_code.strip().upper()},
    ).scalar()


def _contracts(cost_db: Session, ids: list[str]) -> dict[str, dict]:
    if not ids:
        return {}
    query = text(f"SELECT {CONTRACT_COLUMNS} FROM contrato c WHERE c.cod_contrato IN :ids").bindparams(
        bindparam("ids", expanding=True)
    )
    return {row["external_contract_id"]: dict(row) for row in cost_db.execute(query, {"ids": ids}).mappings()}


def _execution(cost_db: Session, ids: list[str]) -> tuple[str | None, dict[str, dict]]:
    period = cost_db.execute(text("SELECT MAX(ano_mes) FROM periodo")).scalar()
    if not ids or not period:
        return period, {}
    query = text("""SELECT ne.nro_contrato AS cod_contrato,
            COUNT(DISTINCT ne.num_ne) AS commitments,
            SUM(CASE WHEN s.cod_item = :empenhado THEN s.valor_saldo ELSE 0 END) AS committed,
            SUM(CASE WHEN s.cod_item = :liquidado THEN s.valor_saldo ELSE 0 END) AS liquidated,
            SUM(CASE WHEN s.cod_item = :pago THEN s.valor_saldo ELSE 0 END) AS paid
        FROM nota_empenho ne
        JOIN saldo_contabil s ON s.num_ne = ne.num_ne AND s.ano_mes = :mes
        WHERE ne.nro_contrato IN :ids
        GROUP BY ne.nro_contrato""").bindparams(bindparam("ids", expanding=True))
    rows = cost_db.execute(query, {
        "ids": ids, "mes": period,
        "empenhado": ITEM_EMPENHADO, "liquidado": ITEM_LIQUIDADO, "pago": ITEM_PAGO,
    }).mappings()
    return period, {row["cod_contrato"]: dict(row) for row in rows}


def _linked(item: Subproject, cost_db: Session) -> dict:
    links = sorted(item.contracts, key=lambda link: link.external_contract_id)
    ids = [link.external_contract_id for link in links]
    current = _contracts(cost_db, ids)
    period, execution = _execution(cost_db, ids)
    contracts = []
    for link in links:
        # O Radar e a unica fonte de exibicao do card. A base deste sistema
        # conserva somente o identificador do vinculo; snapshots antigos nao
        # podem substituir dados contratuais oficiais.
        data = current.get(link.external_contract_id) or {
            "external_contract_id": link.external_contract_id,
            "contract_number": None,
            "contract_object": None,
            "supplier_name": None,
            "global_value": None,
            "status": None, "start_date": None, "end_date": None,
            "instrument_code": None, "contracting_uasg": None,
            "coverage": None, "contract_type": None, "budget_action": None,
            "process_number": None, "legal_basis": None,
        }
        values = execution.get(link.external_contract_id, {})
        contracts.append({
            **data,
            "id": link.id,
            "linked_at": link.linked_at,
            "available_in_radar": link.external_contract_id in current,
            "source_system": "RADAR_FINANCEIRO_ORCAMENTARIO",
            "commitments": values.get("commitments") or 0,
            "committed": values.get("committed") or 0,
            "liquidated": values.get("liquidated") or 0,
            "paid": values.get("paid") or 0,
        })
    return {"period": period, "contracts": contracts}


@router.get("/subprojects/{subproject_id}/contracts")
def list_subproject_contracts(
    subproject_id: int,
    db: Session = Depends(get_project_db),
    cost_db: Session = Depends(get_cost_db),
):
    return _linked(_subproject(db, subproject_id), cost_db)


@router.get("/projects/{project_id}/subproject-contract-options")
def contract_options(
    project_id: int,
    search: str | None = None,
    all_projects: bool = False,
    limit: int = Query(default=100, ge=1, le=300),
    db: Session = Depends(get_project_db),
    cost_db: Session = Depends(get_cost_db),
):
    # Recebe o projeto para atender tambem o cadastro de um subprojeto ainda nao salvo.
    project = db.scalar(select(Project).where(Project.id == project_id, Project.active.is_(True)))
    if not project:
        raise HTTPException(404, "Projeto nao encontrado")
    radar_project = _radar_project(cost_db, project.code)
    filters, params = [], {"limit": limit}
    if radar_project and not all_projects:
        filters.append("EXISTS (SELECT 1 FROM projeto_contrato pc WHERE pc.cod_contrato = c.cod_contrato AND pc.cod_projeto = :projeto)")
        params["projeto"] = radar_project
    if search and search.strip():
        filters.append("""(c.cod_contrato LIKE :search OR c.numero_contrato LIKE :search OR c.objeto LIKE :search
            OR c.nome_fornecedor LIKE :search OR c.nome_fantasia_fornecedor LIKE :search)""")
        params["search"] = f"%{search.strip()}%"
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    rows = cost_db.execute(text(f"""SELECT {CONTRACT_COLUMNS} FROM contrato c {where}
        ORDER BY c.ano_contrato DESC, c.cod_contrato LIMIT :limit"""), params).mappings().all()
    return {
        "radar_project": radar_project,
        "filtered_by_project": bool(radar_project and not all_projects),
        "items": [dict(row) for row in rows],
    }


@router.put("/subprojects/{subproject_id}/contracts")
def replace_subproject_contracts(
    subproject_id: int,
    body: SubprojectContractsInput,
    db: Session = Depends(get_project_db),
    cost_db: Session = Depends(get_cost_db),
):
    item = _subproject(db, subproject_id)
    found = _contracts(cost_db, body.external_contract_ids)
    existing = {link.external_contract_id: link for link in item.contracts}
    missing = [code for code in body.external_contract_ids if code not in found and code not in existing]
    if missing:
        raise HTTPException(422, f"Contrato nao encontrado no Radar Financeiro: {', '.join(missing)}")
    wanted = set(body.external_contract_ids)
    for code, link in existing.items():
        if code not in wanted:
            item.contracts.remove(link)
    for code in body.external_contract_ids:
        data = found.get(code)
        link = existing.get(code)
        if not link:
            link = SubprojectContract(external_contract_id=code)
            item.contracts.append(link)
        if data:
            link.contract_number = (data["contract_number"] or "")[:50] or None
            link.contract_object = data["contract_object"]
            link.supplier_name = (data["supplier_name"] or "")[:255] or None
            link.global_value = data["global_value"]
    db.commit()
    return _linked(_subproject(db, subproject_id), cost_db)
