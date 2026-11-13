VIEW_PROJECTS = "VIEW_PROJECTS"
MANAGE_PROJECTS = "MANAGE_PROJECTS"
MANAGE_SUBPROJECTS = "MANAGE_SUBPROJECTS"
MANAGE_SCHEDULE = "MANAGE_SCHEDULE"
MANAGE_DOCUMENTS = "MANAGE_DOCUMENTS"
MANAGE_USERS = "MANAGE_USERS"

ROLES = {
    "GESTOR_PROGRAMA": {
        "name": "Gestor do programa",
        "permissions": [VIEW_PROJECTS, MANAGE_PROJECTS, MANAGE_SUBPROJECTS, MANAGE_SCHEDULE, MANAGE_DOCUMENTS, MANAGE_USERS],
    },
    "GERENTE_PROJETOS": {
        "name": "Gerente de projetos",
        "permissions": [VIEW_PROJECTS, MANAGE_PROJECTS, MANAGE_SUBPROJECTS, MANAGE_SCHEDULE, MANAGE_DOCUMENTS],
    },
    "COORDENADOR_PROJETOS": {
        "name": "Coordenador de Projetos",
        "permissions": [VIEW_PROJECTS, MANAGE_PROJECTS, MANAGE_SUBPROJECTS, MANAGE_SCHEDULE, MANAGE_DOCUMENTS],
    },
    "CHEFE_ASS_PJT": {
        "name": "Chefe Ass Pjt",
        "permissions": [VIEW_PROJECTS, MANAGE_PROJECTS, MANAGE_SUBPROJECTS, MANAGE_SCHEDULE, MANAGE_DOCUMENTS],
    },
    "SUPERVISOR_PROJETO": {
        "name": "Supervisor do projeto",
        "permissions": [VIEW_PROJECTS, MANAGE_SUBPROJECTS, MANAGE_SCHEDULE, MANAGE_DOCUMENTS],
    },
    "ANALISTA_PROJETOS": {
        "name": "Analista de projetos",
        "permissions": [VIEW_PROJECTS, MANAGE_SUBPROJECTS, MANAGE_SCHEDULE, MANAGE_DOCUMENTS],
    },
    "ANALISTA_LICITACOES": {
        "name": "Analista de licitações",
        "permissions": [VIEW_PROJECTS, MANAGE_SUBPROJECTS, MANAGE_SCHEDULE, MANAGE_DOCUMENTS],
    },
    "ANALISTA_CONTRATOS": {
        "name": "Analista de contratos",
        "permissions": [VIEW_PROJECTS, MANAGE_SUBPROJECTS, MANAGE_SCHEDULE, MANAGE_DOCUMENTS],
    },
    "AUDITOR_INTERNO": {
        "name": "Auditor interno",
        "permissions": [VIEW_PROJECTS],
    },
    "EQUIPE_PROJETO": {
        "name": "Equipe de projeto",
        "permissions": [VIEW_PROJECTS, MANAGE_SCHEDULE],
    },
}


def permissions_for_role(role: str) -> list[str]:
    return list(ROLES.get(role, {}).get("permissions", []))
