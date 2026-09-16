"""External provider interfaces; fixture implementations stay test/local-only."""

from .base import (
    CandidateEntity,
    CorporateRegistryProvider,
    DomainProvider,
    DomainRecord,
    ProviderError,
    ProviderUnavailable,
    ScreeningHit,
    ScreeningProvider,
    WebResearchProvider,
    WebResult,
)

__all__ = [
    "CandidateEntity",
    "DomainRecord",
    "ScreeningHit",
    "WebResult",
    "ProviderError",
    "ProviderUnavailable",
    "CorporateRegistryProvider",
    "ScreeningProvider",
    "WebResearchProvider",
    "DomainProvider",
]
