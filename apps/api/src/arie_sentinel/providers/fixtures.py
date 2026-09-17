"""Deterministic fixture providers for Stage 1.

They use the canonical fictional fixtures plus one deliberately documented
public validation record for ARIE Finance Ltd. No network calls are made and
unsupported labels fail with an explicit non-live dataset limitation.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from ..intake.gate import normalise_label
from .base import (
    CandidateEntity,
    DemoDatasetUnsupported,
    DomainRecord,
    ProviderUnavailable,
    RetrievedPage,
    ScreeningHit,
    ScreeningSubject,
    WebResult,
)

_VANTAR_FZE = CandidateEntity(
    legal_name="Vantar Energy Trading FZE",
    jurisdiction="AE",
    registry_class="uae_free_zone",
    registry_id="12345",
    status="Active",
    incorporation_date="2025-02-14",
    match_basis="registration number + jurisdiction match",
)
_VANTAR_LTD = CandidateEntity(
    legal_name="Vantar Energy Trading Ltd",
    jurisdiction="GB",
    registry_class="companies_house",
    registry_id="09876543",
    status="Active",
    match_basis="name + jurisdiction (registry number differs)",
)
_VANTAR_LLC = CandidateEntity(
    legal_name="Vantar Energy Trading LLC",
    jurisdiction="US-DE",
    registry_class="us_state_registry",
    registry_id="DE-LLC-2025",
    status="Active",
    match_basis="name only — weak",
)
_CASTELLAN = CandidateEntity(
    legal_name="Castellan Trading FZE",
    jurisdiction="AE",
    registry_class="uae_free_zone",
    registry_id="22345",
    status="Active",
    incorporation_date="2024-06-01",
    match_basis="registration number + jurisdiction match",
)

# Fictional commodities-counterparty scenarios used by the management demo.
_ORION_AE = CandidateEntity(
    legal_name="Orion Petro Trading FZE",
    jurisdiction="AE",
    registry_class="uae_free_zone",
    registry_id="OPT-41001",
    status="Active",
    incorporation_date="2019-04-18",
    registered_address="Demo Trade Centre, Dubai, AE",
    match_basis="name + jurisdiction; analyst selection required",
)
_ORION_GB = CandidateEntity(
    legal_name="Orion Petro Trading Ltd",
    jurisdiction="GB",
    registry_class="companies_house",
    registry_id="14200101",
    status="Active",
    incorporation_date="2021-09-03",
    registered_address="10 Fictional Wharf, London, GB",
    match_basis="name match; different jurisdiction and registry identifier",
)
_ORION_SG = CandidateEntity(
    legal_name="Orion Petro Trading Pte. Ltd.",
    jurisdiction="SG",
    registry_class="acra",
    registry_id="202200101Z",
    status="Active",
    incorporation_date="2022-01-10",
    registered_address="1 Example Quay, Singapore",
    match_basis="name match; different jurisdiction and registry identifier",
)
_PACIFIC = CandidateEntity(
    legal_name="Pacific Energy Procurement Ltd",
    jurisdiction="SG",
    registry_class="acra",
    registry_id="201800202P",
    status="Active",
    incorporation_date="2018-06-12",
    registered_address="20 Demo Harbour Road, Singapore",
    match_basis="exact legal name + jurisdiction + registry identifier",
)
_ATLAS = CandidateEntity(
    legal_name="Atlas Global Fuels FZE",
    jurisdiction="AE",
    registry_class="uae_free_zone",
    registry_id="AGF-52003",
    status="Active",
    incorporation_date="2020-11-08",
    registered_address="5 Fictional Free Zone, Fujairah, AE",
    match_basis="exact legal name + jurisdiction + registry identifier",
)
_NORTHSTAR = CandidateEntity(
    legal_name="Northstar Petroleum Trading Ltd",
    jurisdiction="GB",
    registry_class="companies_house",
    registry_id="15100404",
    status="Active",
    incorporation_date="2023-02-21",
    registered_address="24 Example Street, London, GB",
    match_basis="exact legal name + jurisdiction + registry identifier",
)
_MERIDIAN = CandidateEntity(
    legal_name="Meridian Energy Supplies Ltd",
    jurisdiction="GB",
    registry_class="companies_house",
    registry_id="13700505",
    status="Active",
    incorporation_date="2020-07-15",
    registered_address="8 Test Square, London, GB",
    match_basis="exact legal name + jurisdiction + registry identifier",
)

_ARIE_FINANCE = CandidateEntity(
    legal_name="ARIE Finance Ltd",
    jurisdiction="MU",
    registry_class="mauritius_corporate_and_business_registration",
    registry_id="C221997",
    status="Current status not established from cited source",
    alternative_names=("ARIE Finance",),
    source_ref=(
        "https://companies.govmu.org/Communique/"
        "List%20of%20Companies%20with%20Registration%20Fees%20Due%202026%20"
        "as%20at%2016%20December%202025.pdf"
    ),
    retrieved_at="2026-09-16T00:00:00Z",
    match_basis=(
        "exact legal name + Mauritius company registration identifier in an official public "
        "corporate-registry publication"
    ),
)


class FixtureCorporateRegistryProvider:
    """Deterministic registry lookup over the canonical fictional entities."""

    def discover_candidates(self, company_label: str) -> list[CandidateEntity]:
        norm = normalise_label(company_label)
        tokens = set(re.findall(r"[a-z0-9]+", norm))

        if "unavailable" in tokens:  # scenario S8 trigger
            raise ProviderUnavailable("corporate_registry: fixture source unavailable")

        # Combined "Vantar - Castellan" resolves to a single legal entity.
        if "vantar" in tokens and "castellan" in tokens:
            return [_VANTAR_FZE]
        if "castellan" in tokens:
            return [_CASTELLAN]
        # Bare "Vantar" / "Vantar Energy Trading" is ambiguous across jurisdictions.
        if "vantar" in tokens:
            return [_VANTAR_FZE, _VANTAR_LTD, _VANTAR_LLC]
        if "orion" in tokens and "petro" in tokens:
            return [_ORION_AE, _ORION_GB, _ORION_SG]
        if "pacific" in tokens and "procurement" in tokens:
            return [_PACIFIC]
        if "atlas" in tokens and "fuels" in tokens:
            return [_ATLAS]
        if "northstar" in tokens and "petroleum" in tokens:
            return [_NORTHSTAR]
        if "meridian" in tokens and "energy" in tokens:
            return [_MERIDIAN]
        if norm in {"arie finance", "arie finance ltd"}:
            return [_ARIE_FINANCE]
        raise DemoDatasetUnsupported(
            "Not available in the management-demo dataset. Live registry/provider search is "
            "disabled in this management environment. Use one of the demonstration cases or "
            "the ARIE Finance public validation example."
        )

    def discover_officers(
        self, person_name: str, jurisdiction: str, company_number: str
    ) -> list[dict[str, str | None]]:
        if (
            normalise_label(person_name) == "daniel kim"
            and jurisdiction == _PACIFIC.jurisdiction
            and company_number == _PACIFIC.registry_id
        ):
            return [
                {
                    "name": "Daniel Kim",
                    "position": "Director",
                    "start_date": "2019-01-14",
                    "end_date": None,
                    "opencorporates_url": "https://registry.example.test/pacific/officers/daniel-kim",
                }
            ]
        return []


class FixtureScreeningProvider:
    def screen(self, subject: ScreeningSubject | str) -> list[ScreeningHit]:
        subject_label = subject.label if isinstance(subject, ScreeningSubject) else subject
        norm = normalise_label(subject_label)
        hits: list[ScreeningHit] = []
        if "amara" in norm:  # scenario S9: PEP potential match requiring review
            hits.append(
                ScreeningHit(
                    subject_label=subject_label,
                    list_or_source="PEP (fixture)",
                    state="MATCH_REQUIRES_REVIEW",
                    match_basis="name match; date-of-birth not confirmed",
                )
            )
        if "vantar" in norm:  # adverse-media with provider-supplied event grouping
            hits.append(
                ScreeningHit(
                    subject_label=subject_label,
                    list_or_source="Adverse media (fixture)",
                    state="POTENTIAL_MATCH",
                    match_basis="name mention across grouped articles",
                    provider_event_group="evt-0001",
                    article_count=3,
                )
            )
        if "victor lane" in norm:
            hits.append(
                ScreeningHit(
                    subject_label=subject_label,
                    list_or_source="Sanctions screening (fictional fixture)",
                    state="POTENTIAL_MATCH",
                    match_basis=(
                        "name similarity only; date of birth, nationality, and identifiers are not "
                        "established"
                    ),
                    profile_id="fixture-profile-victor-lane-01",
                    score=0.78,
                    explanation={"name": "similar", "identifiers": "not established"},
                    matched_identifiers={"name": ["Victor Lane"]},
                    datasets=("fictional-demo-screening-list",),
                    source_ref="https://screening.example.test/entities/victor-lane-01",
                    retrieved_at="2026-09-16T00:00:00Z",
                )
            )
        return hits


class FixtureDomainProvider:
    def lookup(self, domain: str) -> DomainRecord | None:
        norm = domain.strip().lower()
        if norm == "vantar-energy.test":
            # Registered after incorporation (2025-02-14) -> anomaly (scenario S7).
            return DomainRecord(
                domain=norm, registered_on="2025-03-01", registrar="fixture-registrar"
            )
        return None


class FixtureWebResearchProvider:
    def search(self, query: str) -> list[WebResult]:
        norm = normalise_label(query)
        if "vantar" in norm:
            return [
                WebResult(
                    title="Vantar Energy Trading — About",
                    url="https://vantar-energy.test/about",
                    excerpt="Operating in energy trading since 2011.",
                    retrieved_at="2026-09-04T00:00:00Z",
                )
            ]
        pages = {
            "pacific energy procurement": (
                "Pacific Energy Procurement — Company profile",
                "https://pacific-energy.example.test/company",
                "Fictional public company profile for management demonstration.",
            ),
            "atlas global fuels": (
                "Atlas Global Fuels — Company profile",
                "https://atlas-fuels.example.test/company",
                "Fictional public company profile for management demonstration.",
            ),
            "northstar petroleum trading": (
                "Northstar Petroleum Trading — Company profile",
                "https://northstar-petroleum.example.test/company",
                "Fictional public company profile for management demonstration.",
            ),
            "meridian energy supplies": (
                "Meridian Energy Supplies — Company profile",
                "https://meridian-energy.example.test/company",
                "Fictional public company profile for management demonstration.",
            ),
        }
        for company, (title, url, excerpt) in pages.items():
            if company in norm:
                return [
                    WebResult(
                        title=title,
                        url=url,
                        excerpt=excerpt,
                        retrieved_at="2026-09-16T00:00:00Z",
                    )
                ]
        if "arie finance" in norm:
            return [
                WebResult(
                    title="ARIE Finance — official public website",
                    url="https://www.ariefinance.com/",
                    excerpt=(
                        "Company-controlled public website identifying ARIE Finance Ltd and its "
                        "stated Mauritius regulatory information."
                    ),
                    retrieved_at="2026-09-16T00:00:00Z",
                    publisher="ARIE Finance Ltd",
                ),
                WebResult(
                    title="FSC Mauritius — Payment Intermediary Services licence class",
                    url="https://www.fscmauritius.org/licensing-supervision/codified-list",
                    excerpt="Official regulator description of licence class FS-2.9.",
                    retrieved_at="2026-09-16T00:00:00Z",
                    publisher="Financial Services Commission, Mauritius",
                ),
            ]
        return []

    def retrieve(self, url: str) -> RetrievedPage | None:
        content_by_url = {
            "https://vantar-energy.test/about": "Operating in energy trading since 2011.",
            "https://pacific-energy.example.test/company": (
                "Pacific Energy Procurement Ltd is a fictional procurement company used only "
                "for the ARIE Sentinel management demonstration."
            ),
            "https://atlas-fuels.example.test/company": (
                "Atlas Global Fuels FZE is a fictional fuels intermediary used only for the "
                "ARIE Sentinel management demonstration."
            ),
            "https://northstar-petroleum.example.test/company": (
                "Northstar Petroleum Trading Ltd is a fictional company used only for the ARIE "
                "Sentinel management demonstration."
            ),
            "https://meridian-energy.example.test/company": (
                "Meridian Energy Supplies Ltd is a fictional supplier used only for the ARIE "
                "Sentinel management demonstration."
            ),
            "https://www.ariefinance.com/": (
                "ARIE Finance Ltd identifies itself on its public website as a Mauritius-based "
                "payment intermediary and states licence number GB25205028. This is a "
                "company-controlled public statement, not independent regulator confirmation."
            ),
            "https://www.fscmauritius.org/licensing-supervision/codified-list": (
                "The Financial Services Commission Mauritius codified list identifies FS-2.9 "
                "as the Payment Intermediary Services licence class. This source establishes "
                "the licence category, not that ARIE Finance Ltd currently holds it."
            ),
        }
        content = content_by_url.get(url)
        if content is None:
            return None
        return RetrievedPage(
            url=url,
            content=content,
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
            content_type="text/plain",
            retrieved_at="2026-09-04T00:00:00Z",
        )


@dataclass(frozen=True)
class FixtureProviders:
    registry: FixtureCorporateRegistryProvider
    screening: FixtureScreeningProvider
    domain: FixtureDomainProvider
    web: FixtureWebResearchProvider


def build_fixture_providers() -> FixtureProviders:
    return FixtureProviders(
        registry=FixtureCorporateRegistryProvider(),
        screening=FixtureScreeningProvider(),
        domain=FixtureDomainProvider(),
        web=FixtureWebResearchProvider(),
    )
