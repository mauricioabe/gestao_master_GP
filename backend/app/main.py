from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.projects import router
from app.api.uploads import UPLOAD_ROOT, router as uploads_router
from app.api.subprojects import router as subprojects_router
from app.api.activities import router as activities_router
from app.api.subproject_contracts import router as subproject_contracts_router
from app.api.cff_import import router as cff_import_router
from app.api.auth import router as auth_router, users_router
from app.api.deps import authorize_api
from app.core.config import settings


app = FastAPI(title=settings.app_name, version="0.1.0", docs_url="/docs")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(users_router, prefix=settings.api_prefix)
protected = [Depends(authorize_api)]
app.include_router(router, prefix=settings.api_prefix, dependencies=protected)
app.include_router(uploads_router, prefix=settings.api_prefix, dependencies=protected)
app.include_router(subprojects_router, prefix=settings.api_prefix, dependencies=protected)
app.include_router(activities_router, prefix=settings.api_prefix, dependencies=protected)
app.include_router(subproject_contracts_router, prefix=settings.api_prefix, dependencies=protected)
app.include_router(cff_import_router, prefix=settings.api_prefix, dependencies=protected)
app.mount("/uploads", StaticFiles(directory=UPLOAD_ROOT), name="uploads")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "write_database": "gestao_projetos_sisfron",
        "cost_database_mode": "read-only",
    }
