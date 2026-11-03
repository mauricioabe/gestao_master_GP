from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas import ActivityCreate
from app.api.activities import _business_days, _finish_for_business_days, _next_business_day


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
