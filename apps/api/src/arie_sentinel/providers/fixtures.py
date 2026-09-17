"""Deterministic fixture providers for the management demo.

Corporate discovery is driven entirely by ``demo_dataset.DEMO_CASES`` and matches
ONLY on an exact normalised alias — no token, substring, or fuzzy matching — so an
unsupported real company name can never fall into fictional fixture logic. Web
"pages" are curated demo summaries, explicitly flagged as non-live captures.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from ..demo_dataset import CURATION_DATE, DEMO_CASES
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


class FixtureCorporateRegistryProvider:
    """Deterministic registry lookup over the exact supported demo aliases."""

    def discover_candidates(self, company_label: str) -> list[CandidateEntity]:
        norm = normalise_label(company_label)
        tokens = set(re.findall(r"[a-z0-9]+", norm))

        # Deliberate provider-unavailable simulator (scenario S8): the sentinel
        # token "unavailable" exercises the SOURCE_UNAVAILABLE path. It is not a
        # curated company and never returns fixture data.
        if "unavailable" in tokens:
            raise ProviderUnavailable("corporate_registry: fixture source unavailable")

        case = DEMO_CASES.get(norm)
        if case is not None:
            return list(case.candidates)
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
            and jurisdiction == "SG"
            and company_number == "201800202P"
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
                    retrieved_at=CURATION_DATE,
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
                    retrieved_at=CURATION_DATE,
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
                        retrieved_at=CURATION_DATE,
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
                    retrieved_at=CURATION_DATE,
                    publisher="ARIE Finance Ltd",
                ),
                WebResult(
                    title="FSC Mauritius — Payment Intermediary Services licence class",
                    url="https://www.fscmauritius.org/licensing-supervision/codified-list",
                    excerpt="Official regulator description of licence class FS-2.9.",
                    retrieved_at=CURATION_DATE,
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
        # curated=True: this is a demo summary prepared offline, NOT a live capture.
        # The consumer stamps honest provenance from this flag (see investigations).
        return RetrievedPage(
            url=url,
            content=content,
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
            content_type="text/plain",
            retrieved_at=CURATION_DATE,
            curated=True,
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
