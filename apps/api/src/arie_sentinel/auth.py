"""OIDC authentication with a clearly isolated development identity fallback."""

from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from .config import Settings, get_settings
from .models.enums import Role


@dataclass(frozen=True)
class Principal:
    email: str
    role: Role


bearer = HTTPBearer(auto_error=False)


def _oidc_principal(token: str, settings: Settings) -> Principal:
    if not settings.oidc_issuer or not settings.oidc_audience or not settings.oidc_jwks_url:
        raise HTTPException(status_code=503, detail="OIDC configuration is incomplete.")
    try:
        signing_key = PyJWKClient(settings.oidc_jwks_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
            options={"require": ["exp", "iss", "aud"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid bearer token.") from exc
    roles_value = claims.get(settings.oidc_roles_claim, [])
    if isinstance(roles_value, str):
        roles = {roles_value}
    elif isinstance(roles_value, list) and all(isinstance(role, str) for role in roles_value):
        roles = set(roles_value)
    else:
        raise HTTPException(status_code=403, detail="Sentinel role claim is malformed.")
    if settings.oidc_manager_role in roles:
        role = Role.MANAGER
    elif settings.oidc_analyst_role in roles:
        role = Role.ANALYST
    else:
        raise HTTPException(status_code=403, detail="Sentinel role required.")
    email = claims.get("email") or claims.get("preferred_username") or claims.get("sub")
    if not isinstance(email, str):
        raise HTTPException(status_code=401, detail="Token has no user identifier.")
    return Principal(email=email, role=role)


def get_current_principal(
    settings: Settings = Depends(get_settings),
    x_dev_role: str | None = Header(default=None, alias="X-Dev-Role"),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Principal:
    """Resolve the current user.

    The `X-Dev-Role` header selects analyst/manager only when development auth is
    enabled outside production. Otherwise, a validated OIDC bearer token is required.
    """
    if not settings.dev_auth or settings.is_production:
        if credentials is None:
            raise HTTPException(status_code=401, detail="Bearer token required.")
        return _oidc_principal(credentials.credentials, settings)
    role_value = (x_dev_role or "analyst").strip().lower()
    if role_value == Role.MANAGER.value:
        return Principal(email=settings.dev_manager_email, role=Role.MANAGER)
    return Principal(email=settings.dev_analyst_email, role=Role.ANALYST)


def require_manager(principal: Principal = Depends(get_current_principal)) -> Principal:
    if principal.role is not Role.MANAGER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager role required.")
    return principal
