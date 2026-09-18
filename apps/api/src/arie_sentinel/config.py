"""Application configuration via Pydantic Settings (env-driven, no secrets in code)."""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import model_validator
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
    # Free, no-key public sources (US SEC filers; public-news discovery).
    sec_edgar_base_url: str = "https://efts.sec.gov"
    gdelt_base_url: str = "https://api.gdeltproject.org"
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

    @model_validator(mode="after")
    def validate_production_safety(self) -> Settings:
        """Reject development or incomplete identity settings in production."""
        if not self.is_production:
            return self
        errors: list[str] = []
        if self.dev_auth:
            errors.append("ARIE_DEV_AUTH must be false")
        if self.provider_mode != "live":
            errors.append("ARIE_PROVIDER_MODE must be live")
        if self.database_url == "postgresql+psycopg://arie:arie@localhost:5432/arie_sentinel":
            errors.append("ARIE_DATABASE_URL must not use the development default")
        if not self.oidc_issuer:
            errors.append("ARIE_OIDC_ISSUER is required")
        if not self.oidc_audience:
            errors.append("ARIE_OIDC_AUDIENCE is required")
        if not self.oidc_jwks_url:
            errors.append("ARIE_OIDC_JWKS_URL is required")

        https_endpoints = {
            "ARIE_OIDC_ISSUER": self.oidc_issuer,
            "ARIE_OIDC_JWKS_URL": self.oidc_jwks_url,
            "ARIE_OPENCORPORATES_BASE_URL": self.opencorporates_base_url,
            "ARIE_GLEIF_BASE_URL": self.gleif_base_url,
            "ARIE_OPENSANCTIONS_BASE_URL": self.opensanctions_base_url,
            "ARIE_RDAP_BASE_URL": self.rdap_base_url,
            "ARIE_WEB_SEARCH_BASE_URL": self.web_search_base_url,
        }
        for name, value in https_endpoints.items():
            if value and not _is_https_url(value):
                errors.append(f"{name} must be a valid HTTPS URL")

        origins = [origin.strip() for origin in self.cors_origins.split(",")]
        if not origins or any(not origin for origin in origins):
            errors.append("ARIE_CORS_ORIGINS must contain at least one HTTPS origin")
        for origin in origins:
            if not _is_https_origin(origin):
                errors.append(f"ARIE_CORS_ORIGINS contains an invalid HTTPS origin: {origin}")
        if errors:
            raise ValueError("Unsafe production configuration: " + "; ".join(errors))
        return self


def _is_https_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError:
        return False
    return parsed.scheme.lower() == "https" and parsed.hostname is not None


def _is_https_origin(value: str) -> bool:
    if value == "*":
        return False
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme.lower() == "https"
        and parsed.hostname is not None
        and parsed.username is None
        and parsed.password is None
        and parsed.path == ""
        and parsed.query == ""
        and parsed.fragment == ""
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
