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
    # Production uses the OIDC settings below when dev auth is disabled.
    dev_auth: bool = True
    dev_analyst_email: str = "analyst@example.test"
    dev_manager_email: str = "manager@example.test"

    # Use "fixture" for deterministic local/test data and "live" for adapters.
    provider_mode: str = "fixture"

    provider_timeout_seconds: float = 15.0
    opencorporates_base_url: str = "https://api.opencorporates.com/v0.4"
    opencorporates_api_key: str | None = None
    gleif_base_url: str = "https://api.gleif.org/api/v1"
    opensanctions_base_url: str = "https://api.opensanctions.org"
    opensanctions_api_key: str | None = None
    opensanctions_dataset: str = "default"
    rdap_base_url: str = "https://rdap.org"
    web_search_base_url: str | None = None
    web_search_api_key: str | None = None
    web_search_provider: str = "structured"

    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    oidc_roles_claim: str = "roles"
    oidc_analyst_role: str = "sentinel-analyst"
    oidc_manager_role: str = "sentinel-manager"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.env.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
