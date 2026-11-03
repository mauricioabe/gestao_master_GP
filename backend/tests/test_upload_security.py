import pytest
from fastapi import HTTPException

from app.api.uploads import sanitize_filename, validate_extension


def test_remove_caminho_e_caracteres_perigosos():
    assert sanitize_filename("../../Termo de Abertura 01.pdf") == "Termo-de-Abertura-01.pdf"


def test_preserva_extensao_permitida():
    assert validate_extension("planejamento.XLSX") == ".xlsx"


def test_bloqueia_executavel():
    with pytest.raises(HTTPException) as error:
        validate_extension("arquivo.exe")
    assert error.value.status_code == 415
