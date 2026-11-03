import getpass

from sqlalchemy import select

from app.core.database import ProjectSession
from app.core.security import hash_password
from app.models import User


login = input("Login do Gestor do Programa [admin]: ").strip() or "admin"
name = input("Nome completo: ").strip()
password = getpass.getpass("Senha (mínimo 8 caracteres): ")
if len(password) < 8:
    raise SystemExit("Senha muito curta")
with ProjectSession() as db:
    if db.scalar(select(User).where(User.login == login)):
        raise SystemExit("Usuário já existe")
    db.add(User(login=login, name=name or "Gestor do Programa", password_hash=hash_password(password), role="GESTOR_PROGRAMA"))
    db.commit()
print("Gestor do Programa criado com sucesso.")
