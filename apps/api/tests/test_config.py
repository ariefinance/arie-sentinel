"""Production configuration must fail closed before the service starts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from arie_sentinel.config import Settings


def _production_settings(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "env": "production",
        "dev_auth": False,
        "provider_mode": "live",
        "database_url": "postgresql+psycopg://sentinel:secret@db.internal/sentinel",
        "oidc_issuer": "https://idp.example.test",
        "oidc_audience": "sentinel-api",
        "oidc_jwks_url": "https://idp.example.test/.well-known/jwks.json",
    }
    values.update(overrides)
    return values


def test_complete_production_configuration_is_accepted() -> None:
    settings = Settings(**_production_settings())
    assert settings.is_production
    assert settings.provider_mode == "live"


@pytest.mark.parametrize(
    ("override", "expected"),
    [
        ({"dev_auth": True}, "ARIE_DEV_AUTH must be false"),
        ({"provider_mode": "fixture"}, "ARIE_PROVIDER_MODE must be live"),
        (
            {"database_url": "postgresql+psycopg://arie:arie@localhost:5432/arie_sentinel"},
            "ARIE_DATABASE_URL must not use the development default",
        ),
        ({"oidc_issuer": None}, "ARIE_OIDC_ISSUER is required"),
        ({"oidc_audience": None}, "ARIE_OIDC_AUDIENCE is required"),
        ({"oidc_jwks_url": None}, "ARIE_OIDC_JWKS_URL is required"),
    ],
)
def test_unsafe_production_configuration_is_rejected(
    override: dict[str, object], expected: str
) -> None:
    with pytest.raises(ValidationError, match=expected):
        Settings(**_production_settings(**override))
