"""Deterministic fixture providers for Stage 1.

They use ONLY the canonical fictional fixtures (docs/EXAMPLE-FIXTURES.md) and
behave enough like real adapters to exercise the workflow and the acceptance
scenarios. No network calls, no real data, fully deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..intake.gate import normalise_label
from .base import (
    CandidateEntity,
    DomainRecord,
    ProviderUnavailable,
    ScreeningHit,
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
        # Unknown label: no authoritative candidate (-> NOT_VERIFIED).
        return []


class FixtureScreeningProvider:
    def screen(self, subject_label: str) -> list[ScreeningHit]:
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
        return []


class FixtureModelProvider:
    """Proposes person-name fragments only. Never establishes identity or evidence."""

    _SEP = re.compile(r"\s*(?:-|/|,|&|\bvia\b)\s*", flags=re.IGNORECASE)

    def extract_person_candidates(self, contact_label: str) -> list[str]:
        parts = [p.strip() for p in self._SEP.split(contact_label) if p.strip()]
        return parts or ([contact_label.strip()] if contact_label.strip() else [])


@dataclass(frozen=True)
class FixtureProviders:
    registry: FixtureCorporateRegistryProvider
    screening: FixtureScreeningProvider
    domain: FixtureDomainProvider
    web: FixtureWebResearchProvider
    model: FixtureModelProvider


def build_fixture_providers() -> FixtureProviders:
    return FixtureProviders(
        registry=FixtureCorporateRegistryProvider(),
        screening=FixtureScreeningProvider(),
        domain=FixtureDomainProvider(),
        web=FixtureWebResearchProvider(),
        model=FixtureModelProvider(),
    )
