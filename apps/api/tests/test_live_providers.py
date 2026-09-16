"""Deterministic contract tests for live-provider adapters."""

from __future__ import annotations

import httpx
import pytest

from arie_sentinel.config import Settings
from arie_sentinel.providers.base import (
    ProviderInvalidResponse,
    ProviderRateLimited,
    ProviderUnavailable,
    ScreeningSubject,
)
from arie_sentinel.providers.factory import build_providers
from arie_sentinel.providers.opencorporates import OpenCorporatesProvider
from arie_sentinel.providers.opensanctions import OpenSanctionsProvider
from arie_sentinel.providers.rdap import RdapDomainProvider


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_opencorporates_success_multiple_and_no_result() -> None:
    provider = OpenCorporatesProvider("https://registry.example.test", None)
    provider.client = _client(
        lambda request: httpx.Response(
            200,
            json={
                "results": {
                    "companies": [
                        {
                            "company": {
                                "name": "Example Public Company Ltd",
                                "jurisdiction_code": "gb",
                                "company_number": "12345678",
                                "current_status": "Active",
                                "opencorporates_url": "https://opencorporates.com/companies/gb/12345678",
                            }
                        },
                        {
                            "company": {
                                "name": "Example Public Company LLC",
                                "jurisdiction_code": "us_de",
                                "company_number": "7654321",
                            }
                        },
                    ]
                }
            },
            request=request,
        )
    )
    rows = provider.discover_candidates("Example Public Company")
    assert len(rows) == 2
    assert rows[0].registry_id == "12345678"

    provider.client = _client(
        lambda request: httpx.Response(200, json={"results": {"companies": []}}, request=request)
    )
    assert provider.discover_candidates("No Such Public Company") == []


@pytest.mark.parametrize("status", [429, 503])
def test_provider_rate_limit_and_unavailable(status: int) -> None:
    provider = OpenCorporatesProvider("https://registry.example.test", "not-a-real-key")
    provider.client = _client(lambda request: httpx.Response(status, request=request))
    error = ProviderRateLimited if status == 429 else ProviderUnavailable
    with pytest.raises(error):
        provider.discover_candidates("Example Public Company")


def test_provider_timeout_and_invalid_response() -> None:
    provider = OpenCorporatesProvider("https://registry.example.test", None)

    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    provider.client = _client(timeout)
    with pytest.raises(ProviderUnavailable):
        provider.discover_candidates("Example Public Company")

    provider.client = _client(
        lambda request: httpx.Response(200, json={"unexpected": True}, request=request)
    )
    with pytest.raises(ProviderInvalidResponse):
        provider.discover_candidates("Example Public Company")


def test_opensanctions_zero_and_potential_match() -> None:
    provider = OpenSanctionsProvider("https://screening.example.test", "not-a-real-key")
    provider.client = _client(
        lambda request: httpx.Response(
            200,
            json={"responses": {"subject": {"results": []}}},
            request=request,
        )
    )
    subject = ScreeningSubject(label="Example Public Person")
    assert provider.screen(subject) == []

    provider.client = _client(
        lambda request: httpx.Response(
            200,
            json={
                "responses": {
                    "subject": {
                        "results": [
                            {
                                "id": "public-profile-1",
                                "caption": "Example Public Person",
                                "score": 0.91,
                                "datasets": ["public_list"],
                                "properties": {
                                    "topics": ["sanction"],
                                    "idNumber": ["PUBLIC-123"],
                                },
                                "explanations": {"name": "strong"},
                            }
                        ]
                    }
                }
            },
            request=request,
        )
    )
    hits = provider.screen(subject)
    assert len(hits) == 1
    assert hits[0].state == "POTENTIAL_MATCH"
    assert hits[0].profile_id == "public-profile-1"
    assert hits[0].score == 0.91


def test_rdap_contract() -> None:
    provider = RdapDomainProvider("https://rdap.example.test")
    provider.client = _client(
        lambda request: httpx.Response(
            200,
            json={
                "ldhName": "EXAMPLE.TEST",
                "status": ["active"],
                "events": [{"eventAction": "registration", "eventDate": "2020-01-01T00:00:00Z"}],
                "nameservers": [{"ldhName": "NS1.EXAMPLE.TEST"}],
                "entities": [{"roles": ["registrar"], "handle": "PUBLIC-REGISTRAR"}],
            },
            request=request,
        )
    )
    record = provider.lookup("example.test")
    assert record is not None
    assert record.domain == "example.test"
    assert record.nameservers == ("ns1.example.test",)


def test_live_mode_missing_credentials_fails_safe() -> None:
    providers = build_providers(Settings(provider_mode="live"))
    with pytest.raises(ProviderUnavailable):
        providers.screening.screen("Example Public Person")
    with pytest.raises(ProviderUnavailable):
        providers.web.search("Example Public Company")
