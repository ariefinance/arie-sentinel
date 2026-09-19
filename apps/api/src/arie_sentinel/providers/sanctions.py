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
from .normalization import (
    identifier_key,
    name_match_key,
    name_similarity,
    org_name_key,
)


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


# A fuzzy name match at or above this similarity is surfaced as a POTENTIAL_MATCH for
# analyst review. Fuzzy matches are NEVER auto-confirmed.
_FUZZY_THRESHOLD = 0.86


def _keys(label: str, aliases: tuple[str, ...]) -> tuple[set[str], set[str]]:
    """Return (name_match_keys, org_name_keys) for a label and its aliases."""
    values = [label, *aliases]
    name_keys = {name_match_key(v) for v in values if v}
    org_keys = {org_name_key(v) for v in values if v}
    return {k for k in name_keys if k}, {k for k in org_keys if k}


@dataclass
class SanctionsMatcher:
    """Screens a subject against a normalized set of official sanctions entities.

    Normalization and fuzzy similarity are delegated to ``rigour`` (see
    ``providers/normalization.py``). Identity is never auto-confirmed: identifier and
    exact-name overlaps and fuzzy near-matches all yield POTENTIAL_MATCH; conflicting
    date-of-birth evidence suppresses obvious false positives.
    """

    entities: tuple[SanctionedEntity, ...] = field(default_factory=tuple)

    def screen(self, subject: ScreeningSubject) -> list[ScreeningHit]:
        subj_names, subj_orgs = _keys(subject.label, subject.aliases)
        subj_ids = {
            identifier_key(v) for values in subject.identifiers.values() for v in values if v
        }
        subj_ids.discard("")
        subj_dobs = set(subject.birth_dates)
        subj_countries = {c.upper() for c in subject.countries}
        hits: list[ScreeningHit] = []
        for entity in self.entities:
            ent_names, ent_orgs = _keys(entity.name, entity.aliases)
            ent_ids = {identifier_key(i) for i in entity.identifiers if i}
            ent_ids.discard("")
            id_overlap = subj_ids & ent_ids
            name_overlap = (subj_names & ent_names) or (subj_orgs & ent_orgs)
            dob_conflict = bool(
                subj_dobs and entity.birth_dates and not (subj_dobs & set(entity.birth_dates))
            )
            basis: str | None = None
            score = 0.0
            if id_overlap:
                basis = f"identifier match ({', '.join(sorted(id_overlap))}); requires review"
                score = 0.95
            elif name_overlap:
                if dob_conflict:
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
            else:
                # Fuzzy near-match (typo/transliteration). Never auto-confirmed; suppressed
                # by a conflicting date of birth.
                similarity = self._best_similarity(subj_orgs, ent_orgs)
                if similarity >= _FUZZY_THRESHOLD and not dob_conflict:
                    basis = (
                        f"fuzzy name match (similarity {similarity:.2f}); "
                        "identity not confirmed — analyst review required"
                    )
                    score = round(similarity, 2)
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

    @staticmethod
    def _best_similarity(left: set[str], right: set[str]) -> float:
        best = 0.0
        for a in left:
            for b in right:
                # Cheap prefilter: only compare when a leading character is shared, to
                # bound the cost of fuzzy comparison across a large feed.
                if not a or not b or a[0] != b[0]:
                    continue
                best = max(best, name_similarity(a, b))
                if best >= 0.999:
                    return best
        return best


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
