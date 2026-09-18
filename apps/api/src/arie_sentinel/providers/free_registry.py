"""Free-only corporate registry routing.

Replaces the paid OpenCorporates default on the live path. Discovery is routed to
FREE authoritative sources only:

- GB  → UK Companies House (free key) as the PRIMARY authoritative registry.
- any → GLEIF legal-name search (free, CC0) for LEI-registered entities. An empty
        GLEIF result is "no LEI located" — an absence, never a nonexistence finding.
- US  → SEC EDGAR is corroboration-only (consumed in enrichment), NOT a discovery
        registry, so it does not resolve identity here.
- other jurisdictions with no GLEIF hit → RegistryCoverageUnavailable (an explicit
        coverage limitation). The router NEVER silently falls back to a paid provider
        and NEVER fabricates a confirmation from web search.
"""

from __future__ import annotations

from .base import (
    CandidateEntity,
    RegistryCoverageUnavailable,
)
from .companies_house import CompaniesHouseProvider, UnavailableCompaniesHouseProvider
from .gleif import GleifProvider

_NO_FREE_COVERAGE = (
    "Free authoritative registry coverage is not currently available for this "
    "jurisdiction. GLEIF returned no LEI-registered match (absence of an LEI is not a "
    "nonexistence finding), and no free primary registry integration exists for it. "
    "Sentinel does not fall back to any paid registry or fabricate a confirmation."
)


class FreeRegistryRouter:
    """Routes company discovery across free authoritative registries only."""

    def __init__(
        self,
        *,
        companies_house: CompaniesHouseProvider | UnavailableCompaniesHouseProvider,
        gleif: GleifProvider,
    ) -> None:
        self._companies_house = companies_house
        self._gleif = gleif

    def discover_candidates(
        self, company_label: str, jurisdiction: str | None = None
    ) -> list[CandidateEntity]:
        juris = (jurisdiction or "").strip().upper()

        # GB: Companies House is the free authoritative primary registry. When no key
        # is configured the provider raises ProviderUnavailable (a source outage, not a
        # "no company" finding) — that is honest and handled upstream.
        if juris.startswith("GB") or juris == "UK":
            return self._companies_house.search_company(company_label)

        # Any jurisdiction: free GLEIF legal-name discovery. Propagates
        # ProviderUnavailable/ProviderInvalidResponse to the caller unchanged.
        candidates = self._gleif.search_by_name(company_label, juris or None)
        if candidates:
            return candidates

        # No free authoritative primary registry produced a candidate. This is a
        # coverage limitation, never a nonexistence finding.
        raise RegistryCoverageUnavailable(_NO_FREE_COVERAGE)
