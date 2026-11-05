from collections import defaultdict
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_project_db
from app.models import Activity, Project, Subproject
from app.schemas import ActivityCreate, ActivityOut, ActivityReorder, ActivityUpdate


router = APIRouter(tags=["Cronograma de atividades"])
MILESTONE = "MILESTONE"
PROJECT_SCHEDULE = "PROJECT"


def _business_days(start_date, finish_date) -> int:
    if finish_date < start_date:
        return 0
    current, total = start_date, 0
    while current <= finish_date:
        if current.weekday() < 5:
            total += 1
        current += timedelta(days=1)
    return total


def _next_business_day(value):
    current = value + timedelta(days=1)
    while current.weekday() >= 5:
        current += timedelta(days=1)
    return current


def _finish_for_business_days(start_date, duration_days: int):
    if duration_days <= 0:
        return start_date
    current = start_date
    counted = 1 if current.weekday() < 5 else 0
    while counted < duration_days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            counted += 1
    return current


def _subproject(db: Session, subproject_id: int) -> Subproject:
    item = db.scalar(select(Subproject).where(Subproject.id == subproject_id, Subproject.active.is_(True)))
    if not item:
        raise HTTPException(404, "Subprojeto nao encontrado")
    return item


def _activity(db: Session, activity_id: int) -> Activity:
    item = db.scalar(select(Activity).options(joinedload(Activity.predecessor)).where(
        Activity.id == activity_id, Activity.active.is_(True)
    ))
    if not item:
        raise HTTPException(404, "Atividade nao encontrada")
    return item


def _items(db: Session, subproject_id: int, schedule_type: str) -> list[Activity]:
    return list(db.scalars(select(Activity).options(joinedload(Activity.predecessor)).where(
        Activity.subproject_id == subproject_id,
        Activity.schedule_type == schedule_type,
        Activity.active.is_(True),
    ).order_by(Activity.sort_order)).all())


def _depth(item: Activity, by_id: dict[int, Activity]) -> int:
    depth, parent_id, visited = 0, item.parent_id, set()
    while parent_id and parent_id in by_id and parent_id not in visited:
        visited.add(parent_id)
        depth += 1
        parent_id = by_id[parent_id].parent_id
    return depth


def _children_map(items: list[Activity]) -> dict[int | None, list[Activity]]:
    children: dict[int | None, list[Activity]] = defaultdict(list)
    ids = {item.id for item in items}
    for item in items:
        parent_id = item.parent_id if item.parent_id in ids else None
        children[parent_id].append(item)
    for group in children.values():
        group.sort(key=lambda item: item.sort_order)
    return children


def _tree_order(items: list[Activity]) -> list[Activity]:
    children = _children_map(items)
    ordered: list[Activity] = []

    def visit(parent_id: int | None) -> None:
        for item in children.get(parent_id, []):
            ordered.append(item)
            visit(item.id)

    visit(None)
    return ordered


def _reorder_sibling_block(
    items: list[Activity],
    item: Activity,
    target: Activity,
    position: str,
) -> None:
    if item.id == target.id:
        return
    if item.parent_id != target.parent_id:
        raise HTTPException(409, "As atividades devem estar no mesmo nivel da hierarquia")
    siblings = _children_map(items).get(item.parent_id, [])
    reordered = [current for current in siblings if current.id != item.id]
    target_index = next((index for index, current in enumerate(reordered) if current.id == target.id), None)
    if target_index is None:
        raise HTTPException(409, "Posicao de destino invalida")
    insert_at = target_index + (1 if position == "after" else 0)
    reordered.insert(insert_at, item)
    for index, current in enumerate(reordered, start=1):
        current.sort_order = index

def _reindex_wbs(items: list[Activity], prefix: str) -> None:
    children = _children_map(items)

    def visit(parent_id: int | None, parent_wbs: str) -> None:
        for index, item in enumerate(children.get(parent_id, []), start=1):
            item.wbs_code = f"{parent_wbs}.{index}"
            visit(item.id, item.wbs_code)

    visit(None, prefix)


def _leaf_descendants(item: Activity, children: dict[int | None, list[Activity]]) -> list[Activity]:
    direct = children.get(item.id, [])
    if not direct:
        return [item]
    leaves: list[Activity] = []
    for child in direct:
        leaves.extend(_leaf_descendants(child, children))
    return leaves


def _weighted_progress(items: list[Activity]) -> int:
    total_days = sum(_business_days(item.start_date, item.finish_date) for item in items)
    if not total_days:
        return 0
    completed = sum(
        _business_days(item.start_date, item.finish_date) * item.execution_percentage
        for item in items
    )
    return round(completed / total_days)


def _rollup_summaries(items: list[Activity]) -> None:
    children = _children_map(items)
    by_id = {item.id: item for item in items}
    summaries = [item for item in items if children.get(item.id)]
    summaries.sort(key=lambda item: _depth(item, by_id), reverse=True)
    for summary in summaries:
        leaves = _leaf_descendants(summary, children)
        summary.start_date = min(item.start_date for item in leaves)
        summary.finish_date = max(item.finish_date for item in leaves)
        summary.execution_percentage = _weighted_progress(leaves)
        summary.planned_value = sum((item.planned_value for item in leaves), start=0)
        summary.actual_value = sum((item.actual_value for item in leaves), start=0)


def _leaf_items(items: list[Activity]) -> list[Activity]:
    parent_ids = {item.parent_id for item in items if item.parent_id is not None}
    return [item for item in items if item.id not in parent_ids]


def _sync_progress(db: Session, subproject_id: int) -> None:
    subproject = db.get(Subproject, subproject_id)
    if not subproject:
        return
    subproject_items = _items(db, subproject_id, PROJECT_SCHEDULE)
    subproject.execution_percentage = _weighted_progress(_leaf_items(subproject_items))
    project_items = list(db.scalars(select(Activity).join(Subproject).where(
        Subproject.project_id == subproject.project_id,
        Subproject.active.is_(True),
        Activity.schedule_type == PROJECT_SCHEDULE,
        Activity.active.is_(True),
    )).all())
    project = db.get(Project, subproject.project_id)
    if project:
        project.progress = _weighted_progress(_leaf_items(project_items))


def _predecessor(
    db: Session,
    subproject_id: int,
    schedule_type: str,
    predecessor_id: int | None,
    activity_id: int | None = None,
) -> Activity | None:
    if predecessor_id is None:
        return None
    if predecessor_id == activity_id:
        raise HTTPException(422, "A atividade nao pode ser predecessora dela mesma")
    predecessor = _activity(db, predecessor_id)
    if predecessor.subproject_id != subproject_id or predecessor.schedule_type != schedule_type:
        raise HTTPException(422, "A predecessora deve pertencer ao mesmo cronograma")
    ancestor, visited = predecessor, set()
    while ancestor:
        if ancestor.id in visited or (activity_id is not None and ancestor.predecessor_id == activity_id):
            raise HTTPException(422, "O vinculo informado cria um ciclo de dependencias")
        visited.add(ancestor.id)
        ancestor = ancestor.predecessor
    return predecessor


def _validate_start(predecessor: Activity | None, start_date) -> None:
    suggested = _next_business_day(predecessor.finish_date) if predecessor else None
    if suggested and start_date < suggested:
        raise HTTPException(
            422,
            f"A sucessora deve iniciar apos o termino da predecessora. Data minima: {suggested.isoformat()}",
        )


def _cascade_successors(db: Session, predecessor: Activity, visited: set[int] | None = None) -> int:
    visited = visited or set()
    if predecessor.id in visited:
        return 0
    visited.add(predecessor.id)
    changed = 0
    successors = list(db.scalars(select(Activity).where(
        Activity.predecessor_id == predecessor.id,
        Activity.schedule_type == predecessor.schedule_type,
        Activity.active.is_(True),
    )).all())
    for successor in successors:
        minimum_start = _next_business_day(predecessor.finish_date)
        if successor.start_date < minimum_start:
            duration = _business_days(successor.start_date, successor.finish_date)
            successor.start_date = minimum_start
            successor.finish_date = _finish_for_business_days(minimum_start, duration)
            changed += 1
        changed += _cascade_successors(db, successor, visited)
    return changed


def _serialize(item: Activity, items: list[Activity] | None = None) -> dict:
    all_items = items or [item]
    by_id = {current.id: current for current in all_items}
    children = _children_map(all_items)
    direct_children = children.get(item.id, [])
    leaves = _leaf_descendants(item, children) if direct_children else [item]
    start_date = min(current.start_date for current in leaves)
    finish_date = max(current.finish_date for current in leaves)
    execution = _weighted_progress(leaves) if direct_children else item.execution_percentage
    planned_value = sum((current.planned_value for current in leaves), start=0) if direct_children else item.planned_value
    actual_value = sum((current.actual_value for current in leaves), start=0) if direct_children else item.actual_value
    if direct_children:
        statuses = {current.delivery_status for current in leaves}
        if statuses == {"CANCELADA"}:
            delivery_status = "CANCELADA"
        elif statuses == {"ENCERRADA"}:
            delivery_status = "ENCERRADA"
        elif "EM_EXECUCAO" in statuses or "ENCERRADA" in statuses:
            delivery_status = "EM_EXECUCAO"
        else:
            delivery_status = "EM_PLANEJAMENTO"
    else:
        delivery_status = item.delivery_status
    return {
        "id": item.id,
        "subproject_id": item.subproject_id,
        "schedule_type": item.schedule_type,
        "source_system": item.source_system,
        "source_key": item.source_key,
        "wbs_code": item.wbs_code,
        "sort_order": item.sort_order,
        "name": item.name,
        "duration_days": _business_days(start_date, finish_date),
        "start_date": start_date,
        "finish_date": finish_date,
        "resource_names": None if direct_children else item.resource_names,
        "execution_percentage": execution,
        "planned_value": planned_value,
        "actual_value": actual_value,
        "delivery_status": delivery_status,
        "predecessor_id": item.predecessor_id,
        "predecessor_wbs": item.predecessor.wbs_code if item.predecessor else None,
        "parent_id": item.parent_id,
        "depth": _depth(item, by_id),
        "is_summary": bool(direct_children),
        "active": item.active,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _refresh_hierarchy(db: Session, subproject: Subproject, schedule_type: str) -> list[Activity]:
    items = _tree_order(_items(db, subproject.id, schedule_type))
    for index, item in enumerate(items, start=1):
        item.sort_order = index

    # A troca direta dos codigos pode colidir com a restricao unica enquanto
    # outra atividade ainda ocupa o codigo de destino. Libera todos os codigos
    # em uma primeira etapa e somente depois grava a numeracao EAP definitiva.
    for item in items:
        item.wbs_code = f"__tmp_wbs_{item.id}__"
    db.flush()
    _reindex_wbs(items, subproject.wbs_code)
    db.flush()

    _rollup_summaries(items)
    return items


def _list_schedule(db: Session, subproject_id: int, schedule_type: str) -> list[dict]:
    subproject = _subproject(db, subproject_id)
    items = _tree_order(_items(db, subproject_id, schedule_type))
    _reindex_wbs(items, subproject.wbs_code)
    return [_serialize(item, items) for item in items]


def _recalculate_schedule(db: Session, subproject_id: int, schedule_type: str) -> list[dict]:
    subproject = _subproject(db, subproject_id)
    items = _refresh_hierarchy(db, subproject, schedule_type)
    for item in items:
        _cascade_successors(db, item)
    items = _refresh_hierarchy(db, subproject, schedule_type)
    if schedule_type == PROJECT_SCHEDULE:
        _sync_progress(db, subproject_id)
    db.commit()
    return [_serialize(item, items) for item in items]


def _create_schedule(db: Session, subproject_id: int, schedule_type: str, body: ActivityCreate) -> dict:
    subproject = _subproject(db, subproject_id)
    predecessor = _predecessor(db, subproject_id, schedule_type, body.predecessor_id)
    _validate_start(predecessor, body.start_date)
    order = int(db.scalar(select(func.max(Activity.sort_order)).where(
        Activity.subproject_id == subproject_id,
        Activity.schedule_type == schedule_type,
    )) or 0) + 1
    item = Activity(
        subproject_id=subproject_id,
        schedule_type=schedule_type,
        parent_id=None,
        wbs_code=f"{subproject.wbs_code}.{order}",
        sort_order=order,
        **body.model_dump(),
    )
    db.add(item)
    db.flush()
    items = _refresh_hierarchy(db, subproject, schedule_type)
    if schedule_type == PROJECT_SCHEDULE:
        _sync_progress(db, subproject_id)
    db.commit()
    return _serialize(item, items)


@router.get("/subprojects/{subproject_id}/activities", response_model=list[ActivityOut])
def list_activities(subproject_id: int, db: Session = Depends(get_project_db)):
    return _list_schedule(db, subproject_id, MILESTONE)


@router.get("/subprojects/{subproject_id}/project-activities", response_model=list[ActivityOut])
def list_project_activities(subproject_id: int, db: Session = Depends(get_project_db)):
    return _list_schedule(db, subproject_id, PROJECT_SCHEDULE)


@router.get("/subprojects/{subproject_id}/activities/progress")
def milestone_progress(subproject_id: int, db: Session = Depends(get_project_db)):
    # Consolidado proprio dos Milestones; nao altera nem le o progresso oficial.
    subproject = _subproject(db, subproject_id)
    project_items = list(db.scalars(select(Activity).join(Subproject).where(
        Subproject.project_id == subproject.project_id,
        Subproject.active.is_(True),
        Activity.schedule_type == MILESTONE,
        Activity.active.is_(True),
    )).all())
    return {
        "project_progress": _weighted_progress(_leaf_items(project_items)),
        "subproject_progress": _weighted_progress(_leaf_items(_items(db, subproject_id, MILESTONE))),
    }


@router.post("/subprojects/{subproject_id}/activities/recalculate", response_model=list[ActivityOut])
def recalculate_activities(subproject_id: int, db: Session = Depends(get_project_db)):
    return _recalculate_schedule(db, subproject_id, MILESTONE)


@router.post("/subprojects/{subproject_id}/project-activities/recalculate", response_model=list[ActivityOut])
def recalculate_project_activities(subproject_id: int, db: Session = Depends(get_project_db)):
    return _recalculate_schedule(db, subproject_id, PROJECT_SCHEDULE)


@router.post("/subprojects/{subproject_id}/activities", response_model=ActivityOut, status_code=status.HTTP_201_CREATED)
def create_activity(subproject_id: int, body: ActivityCreate, db: Session = Depends(get_project_db)):
    return _create_schedule(db, subproject_id, MILESTONE, body)


@router.post("/subprojects/{subproject_id}/project-activities", response_model=ActivityOut, status_code=status.HTTP_201_CREATED)
def create_project_activity(subproject_id: int, body: ActivityCreate, db: Session = Depends(get_project_db)):
    return _create_schedule(db, subproject_id, PROJECT_SCHEDULE, body)


@router.put("/activities/{activity_id}", response_model=ActivityOut)
def update_activity(activity_id: int, body: ActivityUpdate, db: Session = Depends(get_project_db)):
    item = _activity(db, activity_id)
    predecessor = _predecessor(db, item.subproject_id, item.schedule_type, body.predecessor_id, item.id)
    _validate_start(predecessor, body.start_date)
    for field, value in body.model_dump().items():
        setattr(item, field, value.strip() if isinstance(value, str) else value)
    db.flush()
    _cascade_successors(db, item)
    subproject = _subproject(db, item.subproject_id)
    items = _refresh_hierarchy(db, subproject, item.schedule_type)
    if item.schedule_type == PROJECT_SCHEDULE:
        _sync_progress(db, item.subproject_id)
    db.commit()
    return _serialize(item, items)


@router.post("/activities/{activity_id}/indent", response_model=list[ActivityOut])
def indent_activity(activity_id: int, db: Session = Depends(get_project_db)):
    item = _activity(db, activity_id)
    subproject = _subproject(db, item.subproject_id)
    items = _items(db, item.subproject_id, item.schedule_type)
    by_id = {current.id: current for current in items}
    current_depth = _depth(item, by_id)
    candidates = [
        current for current in items
        if current.sort_order < item.sort_order and _depth(current, by_id) == current_depth
    ]
    if not candidates:
        raise HTTPException(409, "Nao existe uma tarefa anterior no mesmo nivel para receber a identacao")
    item.parent_id = candidates[-1].id
    items = _refresh_hierarchy(db, subproject, item.schedule_type)
    if item.schedule_type == PROJECT_SCHEDULE:
        _sync_progress(db, item.subproject_id)
    db.commit()
    return [_serialize(current, items) for current in items]


@router.post("/activities/{activity_id}/outdent", response_model=list[ActivityOut])
def outdent_activity(activity_id: int, db: Session = Depends(get_project_db)):
    item = _activity(db, activity_id)
    if item.parent_id is None:
        raise HTTPException(409, "A atividade ja esta no nivel principal")
    parent = _activity(db, item.parent_id)
    item.parent_id = parent.parent_id
    subproject = _subproject(db, item.subproject_id)
    items = _refresh_hierarchy(db, subproject, item.schedule_type)
    if item.schedule_type == PROJECT_SCHEDULE:
        _sync_progress(db, item.subproject_id)
    db.commit()
    return [_serialize(current, items) for current in items]


@router.post("/activities/{activity_id}/reorder", response_model=list[ActivityOut])
def reorder_activity(activity_id: int, body: ActivityReorder, db: Session = Depends(get_project_db)):
    item = _activity(db, activity_id)
    target = _activity(db, body.target_id)
    if item.subproject_id != target.subproject_id or item.schedule_type != target.schedule_type:
        raise HTTPException(409, "A atividade de destino pertence a outro cronograma")
    subproject = _subproject(db, item.subproject_id)
    current_items = _items(db, item.subproject_id, item.schedule_type)
    _reorder_sibling_block(current_items, item, target, body.position)
    items = _refresh_hierarchy(db, subproject, item.schedule_type)
    if item.schedule_type == PROJECT_SCHEDULE:
        _sync_progress(db, item.subproject_id)
    db.commit()
    return [_serialize(current, items) for current in items]


@router.delete("/activities/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(activity_id: int, db: Session = Depends(get_project_db)):
    item = _activity(db, activity_id)
    children = int(db.scalar(select(func.count(Activity.id)).where(
        Activity.parent_id == item.id, Activity.active.is_(True)
    )) or 0)
    if children:
        raise HTTPException(409, "Desindente ou exclua primeiro as subtarefas")
    successors = int(db.scalar(select(func.count(Activity.id)).where(
        Activity.predecessor_id == item.id, Activity.active.is_(True)
    )) or 0)
    if successors:
        raise HTTPException(409, "Remova primeiro o vinculo das atividades sucessoras")
    # Libera o codigo EAP para a renumeracao das atividades ativas.
    item.wbs_code = f"deleted-{item.id}-{item.wbs_code}"
    item.active = False
    db.flush()
    subproject = _subproject(db, item.subproject_id)
    _refresh_hierarchy(db, subproject, item.schedule_type)
    if item.schedule_type == PROJECT_SCHEDULE:
        _sync_progress(db, item.subproject_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
