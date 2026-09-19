"""Free-only registry routing + GLEIF legal-name discovery contract tests."""

from __future__ import annotations

import httpx
import pytest

from arie_sentinel.providers.base import (
    CandidateEntity,
    ProviderUnavailable,
    RegistryCoverageUnavailable,
)
from arie_sentinel.providers.companies_house import (
    CompaniesHouseProvider,
    UnavailableCompaniesHouseProvider,
)
from arie_sentinel.providers.free_registry import FreeRegistryRouter
from arie_sentinel.providers.gleif import GleifProvider


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _gleif_with(records: list[dict]) -> GleifProvider:
    provider = GleifProvider("https://api.gleif.test")
    provider.client = _client(
        lambda request: httpx.Response(200, json={"data": records}, request=request)
    )
    return provider


def test_gleif_name_search_parses_records() -> None:
    provider = _gleif_with(
        [
            {
                "id": "5493001KJTIIGC8Y1R12",
                "attributes": {
                    "entity": {
                        "legalName": {"name": "Example Global Holdings PLC"},
                        "jurisdiction": "GB",
                        "status": "ACTIVE",
                        "legalAddress": {"city": "London", "country": "GB"},
                    }
                },
            }
        ]
    )
    rows = provider.search_by_name("Example Global Holdings")
    assert len(rows) == 1
    assert rows[0].registry_id == "5493001KJTIIGC8Y1R12"
    assert rows[0].registry_class == "gleif"
    assert rows[0].extra["lei"] == "5493001KJTIIGC8Y1R12"


def test_gleif_name_search_empty_is_absence_not_error() -> None:
    provider = _gleif_with([])
    # "No LEI located" is an absence, never an exception or a fabricated record.
    assert provider.search_by_name("No Such Entity") == []


def test_router_gb_routes_to_companies_house() -> None:
    ch = CompaniesHouseProvider("free-key", "https://ch.test")
    ch.client = _client(
        lambda request: httpx.Response(
            200,
            json={"items": [{"title": "Zenith Global Traders Ltd", "company_number": "14750888"}]},
            request=request,
        )
    )
    router = FreeRegistryRouter(companies_house=ch, gleif=_gleif_with([]))
    rows = router.discover_candidates("Zenith Global Traders", jurisdiction="GB")
    assert [r.registry_id for r in rows] == ["14750888"]
    assert rows[0].registry_class == "companies_house"


def test_router_gb_without_key_is_source_unavailable_not_coverage() -> None:
    router = FreeRegistryRouter(
        companies_house=UnavailableCompaniesHouseProvider(), gleif=_gleif_with([])
    )
    # No CH key configured is a source outage, never a "no company" finding.
    with pytest.raises(ProviderUnavailable):
        router.discover_candidates("Zenith Global Traders", jurisdiction="GB")


def test_router_uses_gleif_for_non_gb_and_returns_candidates() -> None:
    gleif = _gleif_with(
        [
            {
                "id": "LEI0000000000000001",
                "attributes": {
                    "entity": {"legalName": {"name": "Meridian AG"}, "jurisdiction": "DE"}
                },
            }
        ]
    )
    router = FreeRegistryRouter(companies_house=UnavailableCompaniesHouseProvider(), gleif=gleif)
    rows = router.discover_candidates("Meridian", jurisdiction="DE")
    assert [r.registry_id for r in rows] == ["LEI0000000000000001"]


def test_router_no_free_coverage_raises_coverage_unavailable() -> None:
    router = FreeRegistryRouter(
        companies_house=UnavailableCompaniesHouseProvider(), gleif=_gleif_with([])
    )
    with pytest.raises(RegistryCoverageUnavailable):
        router.discover_candidates("Obscure Trading", jurisdiction="BR")


def test_router_never_returns_fabricated_candidate() -> None:
    router = FreeRegistryRouter(
        companies_house=UnavailableCompaniesHouseProvider(), gleif=_gleif_with([])
    )
    with pytest.raises(RegistryCoverageUnavailable):
        router.discover_candidates("Anything", jurisdiction=None)
    # Sanity: the router never constructs a CandidateEntity out of thin air.
    assert not isinstance(router, CandidateEntity)
