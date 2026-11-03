from collections.abc import Generator
import re

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


project_engine = create_engine(settings.project_database_url, pool_pre_ping=True, pool_recycle=1800)
ProjectSession = sessionmaker(bind=project_engine, autoflush=False, expire_on_commit=False)

# Esta engine existe exclusivamente para consultas ao Radar Financeiro.
cost_engine = create_engine(settings.cost_database_url, pool_pre_ping=True, pool_recycle=1800)
CostSession = sessionmaker(bind=cost_engine, autoflush=False, expire_on_commit=False)


def validar_sql_somente_leitura(statement: str) -> None:
    """Bloqueia qualquer comando que nao seja consulta na conexao do Radar."""
    normalized = re.sub(r"/\*.*?\*/", "", statement, flags=re.S).strip().upper()
    if not normalized.startswith(("SELECT ", "SHOW ", "DESCRIBE ", "EXPLAIN ")):
        raise PermissionError("A conexao com gestao_custos_sisfron aceita apenas consultas")


@event.listens_for(cost_engine, "connect")
def _marcar_sessao_somente_leitura(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SET SESSION TRANSACTION READ ONLY")
    finally:
        cursor.close()


@event.listens_for(cost_engine, "before_cursor_execute")
def _proteger_base_custos(_conn, _cursor, statement, _parameters, _context, _executemany) -> None:
    validar_sql_somente_leitura(statement)


def get_project_db() -> Generator[Session, None, None]:
    db = ProjectSession()
    try:
        yield db
    finally:
        db.close()


def get_cost_db() -> Generator[Session, None, None]:
    db = CostSession()
    try:
        yield db
    finally:
        db.close()

