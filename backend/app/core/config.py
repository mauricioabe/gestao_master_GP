from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Gestao de Projetos SAD"
    api_prefix: str = "/api"
    project_database_url: str
    cost_database_url: str
    jwt_secret: str = "altere-esta-chave-em-producao"
    jwt_expire_minutes: int = 480
    cors_origins: str = "http://localhost:5174"
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    @field_validator("project_database_url")
    @classmethod
    def validar_base_projetos(cls, value: str) -> str:
        if "/gestao_projetos_sisfron" not in value:
            raise ValueError("PROJECT_DATABASE_URL deve apontar para gestao_projetos_sisfron")
        return value

    @field_validator("cost_database_url")
    @classmethod
    def validar_base_custos(cls, value: str) -> str:
        if "/gestao_custos_sisfron" not in value:
            raise ValueError("COST_DATABASE_URL deve apontar para gestao_custos_sisfron")
        return value

    @property
    def cors_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
