from app.core.permissions import (
    MANAGE_PROJECTS,
    MANAGE_SCHEDULE,
    MANAGE_USERS,
    ROLES,
    permissions_for_role,
)
from app.core.security import create_token, decode_token, hash_password, verify_password


def test_expected_project_roles_are_available():
    assert set(ROLES) == {
        "GERENTE_PROJETOS",
        "ANALISTA_PROJETOS",
        "EQUIPE_PROJETO",
        "GESTOR_PROGRAMA",
        "SUPERVISOR_PROJETO",
    }


def test_program_manager_governs_users_and_projects():
    permissions = permissions_for_role("GESTOR_PROGRAMA")
    assert MANAGE_USERS in permissions
    assert MANAGE_PROJECTS in permissions


def test_project_team_can_update_schedule_but_not_manage_users():
    permissions = permissions_for_role("EQUIPE_PROJETO")
    assert MANAGE_SCHEDULE in permissions
    assert MANAGE_USERS not in permissions


def test_password_is_hashed_and_verified():
    hashed = hash_password("senha-segura-123")
    assert hashed != "senha-segura-123"
    assert verify_password("senha-segura-123", hashed)
    assert not verify_password("senha-incorreta", hashed)


def test_token_contains_subject_and_role():
    token = create_token("mauricio.abe", "GESTOR_PROGRAMA")
    payload = decode_token(token)
    assert payload["sub"] == "mauricio.abe"
    assert payload["role"] == "GESTOR_PROGRAMA"
