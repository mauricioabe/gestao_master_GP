from datetime import date
from decimal import Decimal

from sqlalchemy import bindparam, func, select, text
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from app.api.activities import PROJECT_SCHEDULE, _refresh_hierarchy, _serialize, _subproject, _sync_progress
from app.core.database import get_cost_db, get_project_db
from app.models import Activity, SubprojectContract
from app.schemas import CffImportInput, CffImportOut, CffPreviewOut


router = APIRouter(tags=["Importacao CFF"])
SOURCE_SYSTEM = "RADAR_CFF"


def _source_key(stage_id: int) -> str:
    return f"cff_etapa:{stage_id}"


CONFIRMED_PAYMENT = "CONFIRMADA"

def _cff_execution(payment_status: str) -> int:
    return 100 if payment_status == CONFIRMED_PAYMENT else 0

def _cff_financial_values(
    stage_value: Decimal | None, paid_value: Decimal | None, payment_status: str
) -> tuple[Decimal, Decimal]:
    planned = stage_value or Decimal("0")
    realized = (paid_value or Decimal("0")) if _cff_execution(payment_status) == 100 else Decimal("0")
    return planned, realized

def _payment_rows(cost_db: Session, stage_ids: list[int]) -> dict[int, dict]:
    empty = {stage_id: {
        "paid_value": Decimal("0"), "payment_status": "NAO_CONFERIDA",
        "payment_message": "A OB informada no CFF ainda nao possui comprovacao financeira vinculada.",
        "payment_verified_at": None,
    } for stage_id in stage_ids}
    if not stage_ids:
        return empty
    available = {
        row[0] for row in cost_db.execute(text(
            "SHOW TABLES LIKE 'ordem_bancaria'"
        )).all()
    }
    if not available:
        return empty
    if not cost_db.execute(text("SHOW TABLES LIKE 'cff_etapa_ordem_bancaria'")).first():
        return empty
    query = text("""SELECT r.cff_etapa_id, ob.numero_ob, ob.status, ob.ativo,
            ob.valor_pago, ob.valor_cancelado, ob.valor_devolvido,
            ob.verificada_em, r.valor_associado, totais.total_associado
        FROM cff_etapa_ordem_bancaria r
        JOIN ordem_bancaria ob ON ob.id = r.ordem_bancaria_id
        JOIN (
            SELECT ordem_bancaria_id, SUM(valor_associado) total_associado
            FROM cff_etapa_ordem_bancaria GROUP BY ordem_bancaria_id
        ) totais ON totais.ordem_bancaria_id = ob.id
        WHERE r.cff_etapa_id IN :stage_ids
        ORDER BY r.cff_etapa_id, ob.numero_ob""").bindparams(bindparam("stage_ids", expanding=True))
    grouped: dict[int, list[dict]] = {}
    for row in cost_db.execute(query, {"stage_ids": stage_ids}).mappings():
        grouped.setdefault(row["cff_etapa_id"], []).append(dict(row))
    for stage_id, items in grouped.items():
        invalid = []
        paid = Decimal("0")
        verified_at = None
        for item in items:
            net = (item["valor_pago"] or Decimal("0")) - (item["valor_cancelado"] or Decimal("0")) - (item["valor_devolvido"] or Decimal("0"))
            if not item["ativo"] or item["status"] != CONFIRMED_PAYMENT:
                invalid.append(f"{item['numero_ob']}: {item['status'].lower()}")
                continue
            if item["total_associado"] > net:
                invalid.append(f"{item['numero_ob']}: rateio superior ao valor liquido")
                continue
            paid += item["valor_associado"]
            if verified_at is None or item["verificada_em"] > verified_at:
                verified_at = item["verificada_em"]
        if invalid:
            empty[stage_id] = {
                "paid_value": Decimal("0"), "payment_status": "DIVERGENTE",
                "payment_message": "Pagamento nao importado: " + "; ".join(invalid) + ".",
                "payment_verified_at": verified_at,
            }
        elif paid > 0:
            empty[stage_id] = {
                "paid_value": paid, "payment_status": CONFIRMED_PAYMENT,
                "payment_message": "Pagamento confirmado e rateado sem duplicar a OB.",
                "payment_verified_at": verified_at,
            }
    return empty


def _cff_activity_dates(readiness_letter_date: date | None, planned_start_date: date) -> tuple[date, date]:
    effective_date = readiness_letter_date or planned_start_date
    return effective_date, effective_date


def _linked_contracts(db: Session, subproject_id: int) -> list[SubprojectContract]:
    _subproject(db, subproject_id)
    return list(db.scalars(select(SubprojectContract).where(
        SubprojectContract.subproject_id == subproject_id
    ).order_by(SubprojectContract.external_contract_id)).all())


def _latest_files(cost_db: Session, contract_ids: list[str]) -> list[dict]:
    if not contract_ids:
        return []
    query = text("""SELECT id, cod_contrato, versao, status, qtd_etapas, dt_processamento
        FROM cff_arquivo
        WHERE ativo = 1 AND cod_contrato IN :ids
        ORDER BY cod_contrato, versao DESC, id DESC""").bindparams(bindparam("ids", expanding=True))
    latest: dict[str, dict] = {}
    for row in cost_db.execute(query, {"ids": contract_ids}).mappings():
        latest.setdefault(row["cod_contrato"], dict(row))
    return list(latest.values())


def _stage_rows(cost_db: Session, files: list[dict]) -> list[dict]:
    if not files:
        return []
    file_ids = [item["id"] for item in files]
    query = text("""SELECT e.id, e.cff_id, a.cod_contrato, a.versao,
            e.nro_linha, e.numero_etapa, e.descricao_etapa, e.valor_etapa,
            e.valor_empenhado, e.data_carta_aprestamento, e.numero_ob
        FROM cff_etapa e
        JOIN cff_arquivo a ON a.id = e.cff_id
        WHERE e.cff_id IN :file_ids
        ORDER BY a.cod_contrato, e.nro_linha, e.id""").bindparams(bindparam("file_ids", expanding=True))
    return [dict(row) for row in cost_db.execute(query, {"file_ids": file_ids}).mappings()]


def _available_stages(db: Session, cost_db: Session, subproject_id: int) -> tuple[list[SubprojectContract], list[dict], list[dict]]:
    links = _linked_contracts(db, subproject_id)
    files = _latest_files(cost_db, [link.external_contract_id for link in links])
    return links, files, _stage_rows(cost_db, files)


def _preview(db: Session, cost_db: Session, subproject_id: int) -> dict:
    subproject = _subproject(db, subproject_id)
    links, files, rows = _available_stages(db, cost_db, subproject_id)
    contract_numbers = {link.external_contract_id: link.contract_number for link in links}
    source_keys = [_source_key(row["id"]) for row in rows]
    payments = _payment_rows(cost_db, [row["id"] for row in rows])
    imported = {}
    if source_keys:
        items = db.scalars(select(Activity).where(
            Activity.subproject_id == subproject_id,
            Activity.schedule_type == PROJECT_SCHEDULE,
            Activity.source_system == SOURCE_SYSTEM,
            Activity.source_key.in_(source_keys),
            Activity.active.is_(True),
        )).all()
        imported = {item.source_key: item for item in items}
    stages = []
    for row in rows:
        key = _source_key(row["id"])
        activity = imported.get(key)
        name = (row["descricao_etapa"] or f"Etapa {row['numero_etapa'] or row['id']}").strip()
        import_start, import_finish = _cff_activity_dates(
            row["data_carta_aprestamento"], subproject.planned_start_date
        )
        payment = payments[row["id"]]
        if not row["numero_ob"]:
            payment = {
                "paid_value": Decimal("0"), "payment_status": "SEM_OB",
                "payment_message": "Etapa sem Ordem Bancaria informada.",
                "payment_verified_at": None,
            }
        stages.append({
            "id": row["id"],
            "cff_id": row["cff_id"],
            "contract_id": row["cod_contrato"],
            "contract_number": contract_numbers.get(row["cod_contrato"]),
            "cff_version": row["versao"],
            "stage_number": row["numero_etapa"],
            "name": name,
            "stage_value": row["valor_etapa"],
            "readiness_letter_date": row["data_carta_aprestamento"],
            "import_start_date": import_start,
            "import_finish_date": import_finish,
            "bank_order": row["numero_ob"],
            **payment,
            "execution_percentage": _cff_execution(payment["payment_status"]),
            # Etapas sem Carta de Aprestamento tambem podem ser trazidas. Na
            # importacao, elas recebem provisoriamente o inicio planejado do
            # subprojeto e podem ser ajustadas no cronograma oficial.
            "importable": True,
            "imported": activity is not None,
            "imported_activity_id": activity.id if activity else None,
        })
    return {"linked_contracts": len(links), "cff_files": len(files), "stages": stages}


@router.get("/subprojects/{subproject_id}/cff", response_model=CffPreviewOut)
def list_cff(
    subproject_id: int,
    db: Session = Depends(get_project_db),
    cost_db: Session = Depends(get_cost_db),
):
    return _preview(db, cost_db, subproject_id)


@router.post("/subprojects/{subproject_id}/cff/import", response_model=CffImportOut)
def import_cff(
    subproject_id: int,
    body: CffImportInput,
    db: Session = Depends(get_project_db),
    cost_db: Session = Depends(get_cost_db),
):
    subproject = _subproject(db, subproject_id)
    parent = db.scalar(select(Activity).where(
        Activity.id == body.parent_activity_id,
        Activity.subproject_id == subproject_id,
        Activity.schedule_type == PROJECT_SCHEDULE,
        Activity.active.is_(True),
    ))
    if not parent:
        raise HTTPException(422, "O local escolhido para importar o CFF nao pertence a este cronograma")
    _, _, rows = _available_stages(db, cost_db, subproject_id)
    payments = _payment_rows(cost_db, [row["id"] for row in rows])
    available = {row["id"]: row for row in rows}
    missing = [stage_id for stage_id in body.stage_ids if stage_id not in available]
    if missing:
        raise HTTPException(422, "Uma ou mais etapas nao pertencem ao CFF ativo dos contratos vinculados")
    keys = [_source_key(stage_id) for stage_id in body.stage_ids]
    existing = {item.source_key: item for item in db.scalars(select(Activity).where(
        Activity.subproject_id == subproject_id,
        Activity.schedule_type == PROJECT_SCHEDULE,
        Activity.source_system == SOURCE_SYSTEM,
        Activity.source_key.in_(keys),
    )).all()}
    if parent.id in {item.id for item in existing.values()}:
        raise HTTPException(422, "Uma atividade do CFF selecionada nao pode ser usada como seu proprio nivel superior")

    # Evita ciclos caso uma etapa anteriormente importada tenha recebido
    # subtarefas e o gerente tente movê-la para baixo de uma descendente.
    ancestors, current = set(), parent
    while current.parent_id and current.parent_id not in ancestors:
        ancestors.add(current.parent_id)
        current = db.get(Activity, current.parent_id)
        if current is None:
            break
    if any(item.id in ancestors for item in existing.values()):
        raise HTTPException(422, "O local escolhido criaria um ciclo na estrutura da EAP")
    order = int(db.scalar(select(func.max(Activity.sort_order)).where(
        Activity.subproject_id == subproject_id,
        Activity.schedule_type == PROJECT_SCHEDULE,
    )) or 0)
    imported = updated = skipped = 0
    for stage_id in body.stage_ids:
        row = available[stage_id]
        key = _source_key(stage_id)
        name = (row["descricao_etapa"] or f"Etapa {row['numero_etapa'] or stage_id}").strip()[:255]
        start_date, finish_date = _cff_activity_dates(
            row["data_carta_aprestamento"], subproject.planned_start_date
        )
        payment = payments[stage_id]
        if not row["numero_ob"]:
            payment = {"paid_value": Decimal("0"), "payment_status": "SEM_OB"}
        percentage = _cff_execution(payment["payment_status"])
        planned_value, actual_value = _cff_financial_values(
            row["valor_etapa"], payment["paid_value"], payment["payment_status"]
        )
        item = existing.get(key)
        if item:
            changed = (
                not item.active or item.name != name or item.start_date != start_date
                or item.finish_date != finish_date or item.execution_percentage != percentage
                or item.planned_value != planned_value or item.actual_value != actual_value
                or item.parent_id != parent.id
            )
            if not changed:
                skipped += 1
                continue
            if not item.active:
                order += 1
                item.sort_order = order
                item.parent_id = parent.id
                item.predecessor_id = None
            item.active = True
            item.parent_id = parent.id
            item.name = name
            item.start_date = start_date
            item.finish_date = finish_date
            item.execution_percentage = percentage
            item.planned_value = planned_value
            item.actual_value = actual_value
            item.delivery_status = "ENCERRADA" if percentage == 100 else "EM_PLANEJAMENTO"
            updated += 1
            continue
        order += 1
        item = Activity(
            subproject_id=subproject_id,
            schedule_type=PROJECT_SCHEDULE,
            source_system=SOURCE_SYSTEM,
            source_key=key,
            parent_id=parent.id,
            predecessor_id=None,
            wbs_code=f"{subproject.wbs_code}.{order}",
            sort_order=order,
            name=name,
            start_date=start_date,
            finish_date=finish_date,
            resource_names=None,
            execution_percentage=percentage,
            planned_value=planned_value,
            actual_value=actual_value,
            delivery_status="ENCERRADA" if percentage == 100 else "EM_PLANEJAMENTO",
        )
        db.add(item)
        imported += 1

    db.flush()
    items = _refresh_hierarchy(db, subproject, PROJECT_SCHEDULE)
    _sync_progress(db, subproject_id)
    db.commit()
    return {
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "activities": [_serialize(item, items) for item in items],
    }
