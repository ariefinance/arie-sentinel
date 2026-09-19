"""rigour-backed sanctions matching: normalization, fuzzy, and false-positive control."""

from __future__ import annotations

from arie_sentinel.providers.base import ScreeningSubject
from arie_sentinel.providers.sanctions import SanctionedEntity, SanctionsMatcher


def _matcher(**kw) -> SanctionsMatcher:
    entity = SanctionedEntity(
        name=kw.get("name", "Vladimir Petrov"),
        source_list="OFAC",
        entity_type=kw.get("entity_type", "person"),
        aliases=kw.get("aliases", ()),
        birth_dates=kw.get("birth_dates", ()),
        countries=kw.get("countries", ()),
        identifiers=kw.get("identifiers", ()),
        profile_id="P1",
    )
    return SanctionsMatcher((entity,))


def _screen(matcher: SanctionsMatcher, **kw):
    return matcher.screen(
        ScreeningSubject(
            label=kw.get("label", "Vladimir Petrov"),
            schema=kw.get("schema", "Person"),
            aliases=kw.get("aliases", ()),
            countries=kw.get("countries", ()),
            birth_dates=kw.get("birth_dates", ()),
            identifiers=kw.get("identifiers", {}),
        )
    )


def test_case_and_punctuation_variation_matches() -> None:
    hits = _screen(_matcher(name="ACME Corp., Ltd."), label="acme corp ltd", schema="Company")
    assert hits and hits[0].state == "POTENTIAL_MATCH"


def test_legal_form_variation_matches() -> None:
    # "ACME Trading Limited" vs "ACME Trading Ltd" — legal-form normalization.
    hits = _screen(
        _matcher(name="ACME Trading Limited", entity_type="entity"),
        label="ACME Trading Ltd",
        schema="Company",
    )
    assert hits and hits[0].state == "POTENTIAL_MATCH"


def test_accented_transliteration_variation_matches() -> None:
    hits = _screen(_matcher(name="Café Müller"), label="Cafe Muller", schema="Company")
    assert hits and hits[0].state == "POTENTIAL_MATCH"


def test_small_typo_is_fuzzy_potential_match_never_confirmed() -> None:
    hits = _screen(
        _matcher(name="Zenith Global Traders", entity_type="entity"),
        label="Zenith Globel Traders",
        schema="Company",
    )
    assert hits, "a near-identical typo should surface a fuzzy candidate"
    assert hits[0].state == "POTENTIAL_MATCH"  # never CONFIRMED
    assert "fuzzy" in (hits[0].match_basis or "")
    assert 0.0 < (hits[0].score or 0) < 1.0


def test_same_name_conflicting_dob_is_suppressed() -> None:
    hits = _screen(
        _matcher(name="Vladimir Petrov", birth_dates=("1970-01-01",)),
        label="Vladimir Petrov",
        birth_dates=("1990-12-31",),
    )
    assert hits == []  # same name, conflicting DOB -> not a match


def test_identifier_match_scores_high_but_not_confirmed() -> None:
    hits = _screen(
        _matcher(name="Totally Different Name", identifiers=("A1234567",)),
        label="Unrelated Subject",
        identifiers={"passportNumber": ("A1234567",)},
    )
    assert hits and hits[0].state == "POTENTIAL_MATCH"
    assert (hits[0].score or 0) >= 0.9


def test_unrelated_name_does_not_match() -> None:
    hits = _screen(_matcher(name="Vladimir Petrov"), label="Maria Gonzalez")
    assert hits == []
