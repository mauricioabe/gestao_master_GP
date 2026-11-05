from datetime import date
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas import ActivityCreate
from app.api.activities import (
    _business_days,
    _finish_for_business_days,
    _move_activity_block,
    _next_business_day,
    _reorder_sibling_block,
    _tree_order,
)


def payload(**changes):
    data = {
        "name": "Elaborar entrega",
        "start_date": date(2026, 10, 19),
        "finish_date": date(2026, 10, 20),
        "resource_names": "Equipe SAD",
        "predecessor_id": None,
    }
    data.update(changes)
    return data


def test_activity_accepts_valid_period():
    item = ActivityCreate(**payload())
    assert item.name == "Elaborar entrega"
    assert item.planned_value == 0
    assert item.actual_value == 0
    assert item.delivery_status == "EM_PLANEJAMENTO"


@pytest.mark.parametrize("delivery_status", ["ENCERRADA", "EM_EXECUCAO", "CANCELADA", "EM_PLANEJAMENTO"])
def test_activity_accepts_delivery_status(delivery_status):
    assert ActivityCreate(**payload(delivery_status=delivery_status)).delivery_status == delivery_status


def test_activity_rejects_unknown_delivery_status():
    with pytest.raises(ValidationError):
        ActivityCreate(**payload(delivery_status="SUSPENSA"))


def test_activity_rejects_finish_before_start():
    with pytest.raises(ValidationError):
        ActivityCreate(**payload(finish_date=date(2026, 10, 18)))


def test_activity_rejects_blank_name():
    with pytest.raises(ValidationError):
        ActivityCreate(**payload(name=" "))


@pytest.mark.parametrize("field", ["planned_value", "actual_value"])
def test_activity_rejects_negative_financial_values(field):
    with pytest.raises(ValidationError):
        ActivityCreate(**payload(**{field: -0.01}))

@pytest.mark.parametrize("percentage", [-1, 101])
def test_activity_rejects_progress_outside_range(percentage):
    with pytest.raises(ValidationError):
        ActivityCreate(**payload(execution_percentage=percentage))

def test_duration_counts_only_business_days():
    assert _business_days(date(2026, 10, 16), date(2026, 10, 19)) == 2
    assert _business_days(date(2026, 10, 17), date(2026, 10, 18)) == 0


def test_dependency_adjustment_skips_weekend():
    assert _next_business_day(date(2026, 10, 16)) == date(2026, 10, 19)
    assert _finish_for_business_days(date(2026, 10, 16), 2) == date(2026, 10, 19)


def activity(item_id, parent_id, sort_order):
    return SimpleNamespace(id=item_id, parent_id=parent_id, sort_order=sort_order)


def test_reorder_parent_moves_its_complete_block():
    parent = activity(1, None, 1)
    child = activity(2, 1, 2)
    sibling = activity(3, None, 3)
    items = [parent, child, sibling]

    _reorder_sibling_block(items, parent, sibling, "after")

    assert [item.id for item in _tree_order(items)] == [3, 1, 2]


def test_reorder_children_preserves_parent():
    parent = activity(1, None, 1)
    first = activity(2, 1, 2)
    second = activity(3, 1, 3)
    items = [parent, first, second]

    _reorder_sibling_block(items, second, first, "before")

    assert [item.id for item in _tree_order(items)] == [1, 3, 2]
    assert second.parent_id == parent.id


def test_move_activity_to_another_deliverable():
    first_parent = activity(1, None, 1)
    child = activity(2, 1, 2)
    second_parent = activity(3, None, 3)
    second_child = activity(4, 3, 4)
    items = [first_parent, child, second_parent, second_child]

    _move_activity_block(items, child, second_parent, "inside")

    assert child.parent_id == second_parent.id
    assert [item.id for item in _tree_order(items)] == [1, 3, 4, 2]


def test_move_activity_between_children_of_another_deliverable():
    first_parent = activity(1, None, 1)
    child = activity(2, 1, 2)
    second_parent = activity(3, None, 3)
    second_child = activity(4, 3, 4)
    items = [first_parent, child, second_parent, second_child]

    _move_activity_block(items, child, second_child, "before")

    assert child.parent_id == second_parent.id
    assert [item.id for item in _tree_order(items)] == [1, 3, 2, 4]


def test_move_rejects_parent_inside_own_descendant():
    parent = activity(1, None, 1)
    child = activity(2, 1, 2)

    with pytest.raises(Exception) as error:
        _move_activity_block([parent, child], parent, child, "inside")

    assert getattr(error.value, "status_code", None) == 409
