from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_project_db
from app.core.permissions import MANAGE_USERS, ROLES, permissions_for_role
from app.core.security import create_token, hash_password, verify_password
from app.models import User
from app.schemas import LoginRequest, TokenResponse, UserCreate, UserOut, UserUpdate
from .deps import current_user, require_permissions


router = APIRouter(prefix="/auth", tags=["Autenticação"])
users_router = APIRouter(prefix="/users", tags=["Usuários"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_project_db)):
    user = db.scalar(select(User).where(User.login == body.login.strip()))
    if not user or not user.active or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Login ou senha inválidos")
    user.last_login_at = datetime.utcnow()
    db.commit()
    return TokenResponse(access_token=create_token(user.login, user.role), role=user.role, name=user.name, permissions=permissions_for_role(user.role))


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "login": user.login, "name": user.name, "role": user.role, "permissions": permissions_for_role(user.role)}


@users_router.get("/roles")
def roles(_: User = Depends(require_permissions(MANAGE_USERS))):
    return [{"code": code, **data} for code, data in ROLES.items()]


@users_router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_project_db), _: User = Depends(require_permissions(MANAGE_USERS))):
    return list(db.scalars(select(User).order_by(User.name)).all())


@users_router.post("", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, db: Session = Depends(get_project_db), _: User = Depends(require_permissions(MANAGE_USERS))):
    if body.role not in ROLES:
        raise HTTPException(422, "Perfil inválido")
    if db.scalar(select(User).where(User.login == body.login.strip())):
        raise HTTPException(409, "Login já cadastrado")
    user = User(login=body.login.strip(), name=body.name.strip(), password_hash=hash_password(body.password), role=body.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@users_router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, db: Session = Depends(get_project_db), actor: User = Depends(require_permissions(MANAGE_USERS))):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    if body.role is not None and body.role not in ROLES:
        raise HTTPException(422, "Perfil inválido")
    if user.id == actor.id and body.active is False:
        raise HTTPException(422, "Não é permitido desativar o próprio usuário")
    removes_last_manager = user.active and user.role == "GESTOR_PROGRAMA" and (body.active is False or (body.role is not None and body.role != "GESTOR_PROGRAMA"))
    if removes_last_manager:
        total = db.scalar(select(func.count()).select_from(User).where(User.role == "GESTOR_PROGRAMA", User.active.is_(True)))
        if int(total or 0) <= 1:
            raise HTTPException(422, "O sistema deve manter pelo menos um Gestor do Programa ativo")
    if body.name is not None: user.name = body.name.strip()
    if body.role is not None: user.role = body.role
    if body.active is not None: user.active = body.active
    if body.password: user.password_hash = hash_password(body.password)
    db.commit()
    db.refresh(user)
    return user
