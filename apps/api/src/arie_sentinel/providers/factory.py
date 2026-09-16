"""Environment-driven provider composition."""

from __future__ import annotations

from dataclasses import dataclass

from ..config import Settings
from .base import (
    CorporateRegistryProvider,
    DomainProvider,
    ModelProvider,
    ProviderUnavailable,
    ScreeningHit,
    ScreeningProvider,
    ScreeningSubject,
    WebResearchProvider,
    WebResult,
)
from .fixtures import FixtureModelProvider, build_fixture_providers
from .gleif import GleifProvider
from .opencorporates import OpenCorporatesProvider
from .opensanctions import OpenSanctionsProvider
from .rdap import RdapDomainProvider
from .web_search import StructuredWebSearchProvider


@dataclass(frozen=True)
class Providers:
    registry: CorporateRegistryProvider
    screening: ScreeningProvider
    domain: DomainProvider
    web: WebResearchProvider
    model: ModelProvider
    gleif: GleifProvider | None = None


class UnavailableScreeningProvider:
    def screen(self, subject: ScreeningSubject | str) -> list[ScreeningHit]:
        raise ProviderUnavailable("screening: API key is not configured")


class UnavailableWebResearchProvider:
    def search(self, query: str) -> list[WebResult]:
        raise ProviderUnavailable("web_search: approved endpoint is not configured")


def build_providers(settings: Settings) -> Providers:
    if settings.provider_mode == "fixture":
        fixture = build_fixture_providers()
        return Providers(
            registry=fixture.registry,
            screening=fixture.screening,
            domain=fixture.domain,
            web=fixture.web,
            model=fixture.model,
        )
    if settings.provider_mode != "live":
        raise ValueError("ARIE_PROVIDER_MODE must be 'fixture' or 'live'")
    web = (
        StructuredWebSearchProvider(
            settings.web_search_base_url,
            settings.web_search_api_key or "",
            settings.provider_timeout_seconds,
        )
        if settings.web_search_base_url
        else UnavailableWebResearchProvider()
    )
    return Providers(
        registry=OpenCorporatesProvider(
            settings.opencorporates_base_url,
            settings.opencorporates_api_key,
            settings.provider_timeout_seconds,
        ),
        screening=(
            OpenSanctionsProvider(
                settings.opensanctions_base_url,
                settings.opensanctions_api_key,
                settings.opensanctions_dataset,
                settings.provider_timeout_seconds,
            )
            if settings.opensanctions_api_key
            else UnavailableScreeningProvider()
        ),
        domain=RdapDomainProvider(settings.rdap_base_url, settings.provider_timeout_seconds),
        web=web,
        model=FixtureModelProvider(),
        gleif=GleifProvider(settings.gleif_base_url, settings.provider_timeout_seconds),
    )
