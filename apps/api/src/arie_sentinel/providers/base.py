"""Provider interfaces (Protocols) and shared DTOs.

These are thin, explicit contracts. The core depends only on these, never on a
concrete vendor. Stage 1 ships fixture implementations (see fixtures.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


class ProviderError(Exception):
    """Base class for provider failures."""


class ProviderUnavailable(ProviderError):
    """A material source could not be reached (maps to SOURCE_UNAVAILABLE)."""


@dataclass(frozen=True)
class CandidateEntity:
    """A candidate legal entity returned by discovery/registry lookup."""

    legal_name: str
    jurisdiction: str | None
    registry_class: str | None
    registry_id: str | None
    status: str | None
    incorporation_date: str | None = None
    match_basis: str | None = None  # plain-language "why matched" + identifiers
    extra: dict[str, Any] = field(default_factory=dict)

    def identity_key(self) -> str:
        """Canonical dedupe key: f(jurisdiction, registry_id). Never label-based."""
        juris = (self.jurisdiction or "?").strip().lower()
        rid = (self.registry_id or "?").strip().lower()
        return f"{juris}:{rid}"


@dataclass(frozen=True)
class DomainRecord:
    domain: str
    registered_on: str | None
    registrar: str | None = None
    source_ref: str | None = None


@dataclass(frozen=True)
class ScreeningHit:
    subject_label: str
    list_or_source: str
    state: str  # a ScreeningState value
    match_basis: str | None = None
    provider_event_group: str | None = None
    article_count: int | None = None


@dataclass(frozen=True)
class WebResult:
    title: str
    url: str
    excerpt: str
    retrieved_at: str


@runtime_checkable
class CorporateRegistryProvider(Protocol):
    def discover_candidates(self, company_label: str) -> list[CandidateEntity]:
        """Return 0..N candidate legal entities for a (normalised) company label."""
        ...


@runtime_checkable
class ScreeningProvider(Protocol):
    def screen(self, subject_label: str) -> list[ScreeningHit]: ...


@runtime_checkable
class WebResearchProvider(Protocol):
    def search(self, query: str) -> list[WebResult]: ...


@runtime_checkable
class DomainProvider(Protocol):
    def lookup(self, domain: str) -> DomainRecord | None: ...


@runtime_checkable
class ModelProvider(Protocol):
    def extract_person_candidates(self, contact_label: str) -> list[str]:
        """Propose person-name fragments from a raw contact label.

        The model only *proposes*; it never establishes identity, resolves
        entities, or produces evidence by itself (docs/SECURITY-BOUNDARIES.md §2).
        """
        ...
