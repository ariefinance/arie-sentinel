"""Application configuration via Pydantic Settings (env-driven, no secrets in code)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. All values come from the environment (prefix ARIE_)."""

    model_config = SettingsConfigDict(env_prefix="ARIE_", env_file=".env", extra="ignore")

    env: str = "development"
    log_level: str = "info"
    database_url: str = "postgresql+psycopg://arie:arie@localhost:5432/arie_sentinel"

    # CORS: explicit allow-list only; never "*".
    cors_origins: str = "http://localhost:5173"

    # Development identity mechanism — clearly isolated, dev-only.
    # The production auth boundary (OIDC) is explicit but not wired in Stage 1.
    dev_auth: bool = True
    dev_analyst_email: str = "analyst@example.test"
    dev_manager_email: str = "manager@example.test"

    # Provider mode: Stage 1 supports "fixture" only. Real modes arrive later.
    provider_mode: str = "fixture"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.env.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
