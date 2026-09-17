"""Provider interfaces (Protocols) and shared DTOs.

These are thin, explicit contracts. The core depends only on these, never on a
concrete vendor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


class ProviderError(Exception):
    """Base class for provider failures."""


class ProviderUnavailable(ProviderError):
    """A material source could not be reached (maps to SOURCE_UNAVAILABLE)."""


class ProviderRateLimited(ProviderUnavailable):
    """The provider rejected the request because its rate limit was reached."""


class ProviderInvalidResponse(ProviderError):
    """The provider returned a response that did not satisfy its contract."""


class DemoDatasetUnsupported(ProviderError):
    """The non-live management demo has no configured record for this label."""


@dataclass(frozen=True)
class CandidateEntity:
    """A candidate legal entity returned by discovery/registry lookup."""

    legal_name: str
    jurisdiction: str | None
    registry_class: str | None
    registry_id: str | None
    status: str | None
    incorporation_date: str | None = None
    registered_address: str | None = None
    alternative_names: tuple[str, ...] = ()
    source_ref: str | None = None
    retrieved_at: str | None = None
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
    updated_on: str | None = None
    expires_on: str | None = None
    nameservers: tuple[str, ...] = ()
    statuses: tuple[str, ...] = ()
    raw_reference: str | None = None


@dataclass(frozen=True)
class ScreeningHit:
    subject_label: str
    list_or_source: str
    state: str  # a ScreeningState value
    match_basis: str | None = None
    provider_event_group: str | None = None
    article_count: int | None = None
    profile_id: str | None = None
    score: float | None = None
    explanation: dict[str, Any] = field(default_factory=dict)
    matched_identifiers: dict[str, list[str]] = field(default_factory=dict)
    datasets: tuple[str, ...] = ()
    source_ref: str | None = None
    retrieved_at: str | None = None


@dataclass(frozen=True)
class WebResult:
    """Search discovery metadata; its excerpt is never authoritative evidence."""

    title: str
    url: str
    excerpt: str
    retrieved_at: str
    publisher: str | None = None
    published_at: str | None = None


@dataclass(frozen=True)
class RetrievedPage:
    """A bounded capture of an underlying public page discovered by search."""

    url: str
    content: str
    content_hash: str
    content_type: str
    retrieved_at: str


@dataclass(frozen=True)
class ScreeningSubject:
    label: str
    schema: str = "Person"
    aliases: tuple[str, ...] = ()
    countries: tuple[str, ...] = ()
    birth_dates: tuple[str, ...] = ()
    identifiers: dict[str, tuple[str, ...]] = field(default_factory=dict)


@runtime_checkable
class CorporateRegistryProvider(Protocol):
    def discover_candidates(self, company_label: str) -> list[CandidateEntity]:
        """Return 0..N candidate legal entities for a (normalised) company label."""
        ...


@runtime_checkable
class ScreeningProvider(Protocol):
    def screen(self, subject: ScreeningSubject | str) -> list[ScreeningHit]: ...


@runtime_checkable
class WebResearchProvider(Protocol):
    def search(self, query: str) -> list[WebResult]: ...

    def retrieve(self, url: str) -> RetrievedPage | None: ...


@runtime_checkable
class DomainProvider(Protocol):
    def lookup(self, domain: str) -> DomainRecord | None: ...
