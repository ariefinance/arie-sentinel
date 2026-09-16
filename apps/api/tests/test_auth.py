"""Production OIDC validation fails closed for claims and Sentinel roles."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from arie_sentinel import auth
from arie_sentinel.config import Settings

_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PUBLIC_KEY = _PRIVATE_KEY.public_key()


class _Jwks:
    def __init__(self, url: str) -> None:
        self.url = url

    def get_signing_key_from_jwt(self, token: str):
        return SimpleNamespace(key=_PUBLIC_KEY)


@pytest.fixture(autouse=True)
def _jwks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth, "PyJWKClient", _Jwks)


def _settings() -> Settings:
    return Settings(
        dev_auth=False,
        oidc_issuer="https://idp.example.test",
        oidc_audience="sentinel-api",
        oidc_jwks_url="https://idp.example.test/jwks",
    )


def _token(**overrides: object) -> str:
    claims: dict[str, object] = {
        "sub": "public-user-1",
        "iss": "https://idp.example.test",
        "aud": "sentinel-api",
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "roles": ["sentinel-analyst"],
    }
    claims.update(overrides)
    return jwt.encode(claims, _PRIVATE_KEY, algorithm="RS256")


@pytest.mark.parametrize(
    "token",
    [
        _token(exp=datetime.now(UTC) - timedelta(minutes=1)),
        _token(iss="https://wrong-issuer.example.test"),
        _token(aud="wrong-audience"),
    ],
)
def test_invalid_required_claims_are_rejected(token: str) -> None:
    with pytest.raises(HTTPException) as exc:
        auth._oidc_principal(token, _settings())
    assert exc.value.status_code == 401


def test_missing_exp_is_rejected() -> None:
    claims = {
        "sub": "public-user-1",
        "iss": "https://idp.example.test",
        "aud": "sentinel-api",
        "roles": ["sentinel-analyst"],
    }
    token = jwt.encode(claims, _PRIVATE_KEY, algorithm="RS256")
    with pytest.raises(HTTPException) as exc:
        auth._oidc_principal(token, _settings())
    assert exc.value.status_code == 401


@pytest.mark.parametrize("roles", [None, 7, {"role": "sentinel-manager"}, [7]])
def test_malformed_role_claim_fails_closed(roles: object) -> None:
    with pytest.raises(HTTPException) as exc:
        auth._oidc_principal(_token(roles=roles), _settings())
    assert exc.value.status_code == 403


def test_missing_sentinel_role_is_forbidden() -> None:
    with pytest.raises(HTTPException) as exc:
        auth._oidc_principal(_token(roles=["unrelated-role"]), _settings())
    assert exc.value.status_code == 403
