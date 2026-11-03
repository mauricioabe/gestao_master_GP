import pytest

from app.core.database import validar_sql_somente_leitura


@pytest.mark.parametrize("sql", [
    "SELECT * FROM contrato",
    "  /* painel */ SELECT cod_contrato FROM contrato",
    "SHOW TABLES",
    "DESCRIBE contrato",
    "EXPLAIN SELECT * FROM contrato",
])
def test_permite_consultas(sql):
    validar_sql_somente_leitura(sql)


@pytest.mark.parametrize("sql", [
    "INSERT INTO contrato VALUES (1)",
    "UPDATE contrato SET status='x'",
    "DELETE FROM contrato",
    "ALTER TABLE contrato ADD COLUMN x INT",
    "DROP TABLE contrato",
    "CREATE VIEW x AS SELECT 1",
    "GRANT SELECT ON gestao_custos_sisfron.* TO x",
])
def test_bloqueia_escrita_e_ddl(sql):
    with pytest.raises(PermissionError):
        validar_sql_somente_leitura(sql)

