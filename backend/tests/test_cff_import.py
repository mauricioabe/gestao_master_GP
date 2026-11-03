from datetime import date

from decimal import Decimal

from app.api.cff_import import _cff_activity_dates, _cff_execution, _cff_financial_values, _source_key


def test_cff_execution_is_complete_only_with_confirmed_payment():
    assert _cff_execution("CONFIRMADA") == 100


def test_cff_execution_is_zero_without_bank_order():
    assert _cff_execution("SEM_OB") == 0
    assert _cff_execution("NAO_CONFERIDA") == 0
    assert _cff_execution("CANCELADA") == 0


def test_cff_source_key_is_stable():
    assert _source_key(42) == "cff_etapa:42"


def test_cff_activity_date_uses_readiness_letter_when_available():
    letter_date = date(2026, 5, 13)
    assert _cff_activity_dates(letter_date, date(2023, 6, 5)) == (letter_date, letter_date)


def test_cff_activity_date_falls_back_to_subproject_planned_start():
    planned_start = date(2023, 6, 5)
    assert _cff_activity_dates(None, planned_start) == (planned_start, planned_start)


def test_cff_financial_values_use_verified_net_payment():
    value = Decimal("105696.80")
    paid = Decimal("98765.43")
    assert _cff_financial_values(value, paid, "CONFIRMADA") == (value, paid)
    assert _cff_financial_values(value, paid, "NAO_CONFERIDA") == (value, Decimal("0"))
