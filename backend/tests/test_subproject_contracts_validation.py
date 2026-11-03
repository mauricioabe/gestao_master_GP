import pytest
from pydantic import ValidationError

from app.schemas import SubprojectContractsInput


def test_contract_ids_are_trimmed_and_deduplicated():
    body = SubprojectContractsInput(external_contract_ids=[" 010/2026 ", "005/2025", "010/2026", "  "])
    assert body.external_contract_ids == ["010/2026", "005/2025"]


def test_empty_selection_unlinks_all_contracts():
    assert SubprojectContractsInput(external_contract_ids=[]).external_contract_ids == []


def test_rejects_contract_id_longer_than_column():
    with pytest.raises(ValidationError):
        SubprojectContractsInput(external_contract_ids=["X" * 61])
