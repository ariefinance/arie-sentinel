"""Free official sanctions layer — normalized model + identifier-aware matcher.

Consolidates the free, authoritative government feeds (OFAC, UK OFSI, UN, EU) into
one normalized model and screens a subject against it. Matching is identifier-aware:
name-only similarity is only ever a POTENTIAL_MATCH requiring analyst review, and
supplied date-of-birth / country evidence is used to suppress obvious false positives.
It never returns a CONFIRMED_MATCH automatically.

This module is the matching engine + provider. Live download + scheduled refresh of
each official feed (and PostgreSQL caching) is wired via ``load_entities``; per-feed
formats are documented in docs/FREE-DATA-SOURCES.md.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from .base import ProviderUnavailable, ScreeningHit, ScreeningSubject


@dataclass(frozen=True)
class SanctionedEntity:
    name: str
    source_list: str  # OFAC | UK | UN | EU
    entity_type: str = "entity"  # "person" | "entity"
    aliases: tuple[str, ...] = ()
    birth_dates: tuple[str, ...] = ()
    countries: tuple[str, ...] = ()
    identifiers: tuple[str, ...] = ()
    profile_id: str | None = None


def _norm(value: str) -> str:
    return " ".join(value.lower().split())


def _norm_id(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


@dataclass
class SanctionsMatcher:
    """Screens a subject against a normalized set of official sanctions entities."""

    entities: tuple[SanctionedEntity, ...] = field(default_factory=tuple)

    def screen(self, subject: ScreeningSubject) -> list[ScreeningHit]:
        subj_names = {_norm(subject.label)} | {_norm(a) for a in subject.aliases}
        subj_ids = {_norm_id(v) for values in subject.identifiers.values() for v in values if v}
        subj_dobs = set(subject.birth_dates)
        subj_countries = {c.upper() for c in subject.countries}
        hits: list[ScreeningHit] = []
        for entity in self.entities:
            ent_names = {_norm(entity.name)} | {_norm(a) for a in entity.aliases}
            ent_ids = {_norm_id(i) for i in entity.identifiers if i}
            id_overlap = subj_ids & ent_ids
            name_overlap = subj_names & ent_names
            basis: str | None = None
            score = 0.0
            if id_overlap:
                basis = f"identifier match ({', '.join(sorted(id_overlap))}); requires review"
                score = 0.95
            elif name_overlap:
                # Use DOB / country to suppress obvious false positives.
                if subj_dobs and entity.birth_dates and not (subj_dobs & set(entity.birth_dates)):
                    continue  # same name, different date of birth -> not a match
                if (
                    subj_countries
                    and entity.countries
                    and not (subj_countries & {c.upper() for c in entity.countries})
                ):
                    basis = "name match; country differs — analyst review required"
                    score = 0.55
                else:
                    basis = "name/alias match; identity not confirmed — analyst review required"
                    score = 0.6
            if basis is None:
                continue
            hits.append(
                ScreeningHit(
                    subject_label=subject.label,
                    list_or_source=f"Sanctions: {entity.source_list}",
                    state="POTENTIAL_MATCH",  # never auto-confirmed
                    match_basis=basis,
                    profile_id=entity.profile_id,
                    score=score,
                    matched_identifiers={"id": sorted(id_overlap)} if id_overlap else {},
                    datasets=(entity.source_list,),
                )
            )
        return hits


class OfficialSanctionsProvider:
    """A ScreeningProvider backed by loaded official-feed entities.

    Fails closed (ProviderUnavailable) until the official feeds have been loaded, so a
    not-yet-refreshed dataset is never silently reported as "no material match".
    """

    def __init__(self, entities: Iterable[SanctionedEntity] | None = None) -> None:
        self._loaded = entities is not None
        self._matcher = SanctionsMatcher(tuple(entities or ()))

    def load_entities(self, entities: Iterable[SanctionedEntity]) -> None:
        self._matcher = SanctionsMatcher(tuple(entities))
        self._loaded = True

    def screen(self, subject: ScreeningSubject | str) -> list[ScreeningHit]:
        if not self._loaded:
            raise ProviderUnavailable("sanctions: official feeds have not been loaded/refreshed")
        subject_obj = (
            subject if isinstance(subject, ScreeningSubject) else ScreeningSubject(subject)
        )
        return self._matcher.screen(subject_obj)
