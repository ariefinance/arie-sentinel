"""Authentication / authorization boundary.

The production boundary is OIDC (see docs/ARCHITECTURE.md §9). Stage 1 uses a
clearly-isolated DEVELOPMENT identity mechanism, active only when ARIE_DEV_AUTH
is true and never in production. This keeps the AuthZ contract (roles enforced
server-side on every mutation) explicit from day one — no fake production auth.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from .config import Settings, get_settings
from .models.enums import Role


@dataclass(frozen=True)
class Principal:
    email: str
    role: Role


def get_current_principal(
    settings: Settings = Depends(get_settings),
    x_dev_role: str | None = Header(default=None, alias="X-Dev-Role"),
) -> Principal:
    """Resolve the current user.

    Stage 1: dev-only. The `X-Dev-Role` header selects analyst/manager against the
    configured dev identities. In production (dev_auth disabled) this raises until
    the real OIDC dependency is wired — the boundary is explicit, not faked.
    """
    if not settings.dev_auth or settings.is_production:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OIDC authentication is not configured in this build.",
        )
    role_value = (x_dev_role or "analyst").strip().lower()
    if role_value == Role.MANAGER.value:
        return Principal(email=settings.dev_manager_email, role=Role.MANAGER)
    return Principal(email=settings.dev_analyst_email, role=Role.ANALYST)


def require_manager(principal: Principal = Depends(get_current_principal)) -> Principal:
    if principal.role is not Role.MANAGER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager role required.")
    return principal
