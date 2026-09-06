"""External provider interfaces and their Stage 1 deterministic fixture implementations.

Simple, explicit interfaces (Protocols) — no plugin framework. Real providers
replace the fixtures later without touching the core.
"""

from .base import (
    CandidateEntity,
    CorporateRegistryProvider,
    DomainProvider,
    DomainRecord,
    ModelProvider,
    ProviderError,
    ProviderUnavailable,
    ScreeningHit,
    ScreeningProvider,
    WebResearchProvider,
    WebResult,
)
from .fixtures import (
    FixtureCorporateRegistryProvider,
    FixtureDomainProvider,
    FixtureModelProvider,
    FixtureScreeningProvider,
    FixtureWebResearchProvider,
    build_fixture_providers,
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
    "ModelProvider",
    "FixtureCorporateRegistryProvider",
    "FixtureScreeningProvider",
    "FixtureWebResearchProvider",
    "FixtureDomainProvider",
    "FixtureModelProvider",
    "build_fixture_providers",
]
