from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_project_db
from app.core.permissions import MANAGE_DOCUMENTS, MANAGE_PROJECTS, MANAGE_SCHEDULE, MANAGE_SUBPROJECTS, permissions_for_role
from app.core.security import decode_token
from app.models import User


bearer = HTTPBearer(auto_error=False)


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_project_db)) -> User:
    if not credentials:
        raise HTTPException(401, "Autenticação necessária")
    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(401, str(exc)) from exc
    user = db.scalar(select(User).where(User.login == payload.get("sub"), User.active.is_(True)))
    if not user:
        raise HTTPException(401, "Usuário inativo ou inexistente")
    return user


def require_permissions(*permissions: str):
    def dependency(user: User = Depends(current_user)) -> User:
        granted = set(permissions_for_role(user.role))
        if any(permission not in granted for permission in permissions):
            raise HTTPException(403, "Perfil sem permissão para esta operação")
        return user
    return dependency


def authorize_api(request: Request, user: User = Depends(current_user)) -> User:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return user
    path = request.url.path
    required = MANAGE_PROJECTS
    if path.startswith("/api/uploads"):
        required = MANAGE_DOCUMENTS
    elif "/activities" in path or path.startswith("/api/activities") or path.endswith("/cff/import"):
        required = MANAGE_SCHEDULE
    elif path.startswith("/api/subprojects"):
        required = MANAGE_SUBPROJECTS
    if required not in permissions_for_role(user.role):
        raise HTTPException(403, "Perfil sem permissão para esta operação")
    return user
