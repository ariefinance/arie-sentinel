"""Demo-data discipline — fictional fixtures plus one documented public case.

We deliberately do not embed any real/management-derived label here (a denylist
would itself reintroduce that operational data). Instead we assert that the
fictional fixtures only emit the canonical invented names. ARIE Finance is the
sole public validation record and is tested separately against public references.
Secret scanning (gitleaks) and the committed-data guard live in CI.
"""

from __future__ import annotations

import pytest

from arie_sentinel.providers import DemoDatasetUnsupported
from arie_sentinel.providers.fixtures import build_fixture_providers

# The ONLY entity name-stems permitted anywhere in fixtures/tests/examples.
ALLOWED_NAME_STEMS = (
    "Vantar",
    "Castellan",
    "Orion",
    "Pacific",
    "Atlas",
    "Northstar",
    "Meridian",
)
ALLOWED_DOMAINS = ("vantar-energy.test",)


def test_registry_fixtures_emit_only_canonical_names() -> None:
    reg = build_fixture_providers().registry
    labels = [
        "Vantar - Castellan",
        "Vantar Energy Trading",
        "Castellan Trading",
        "Orion Petro Trading",
        "Pacific Energy Procurement Ltd",
        "Atlas Global Fuels",
        "Northstar Petroleum Trading",
        "Meridian Energy Supplies Ltd",
    ]
    for label in labels:
        for cand in reg.discover_candidates(label):
            assert cand.legal_name.startswith(ALLOWED_NAME_STEMS), cand.legal_name


@pytest.mark.parametrize("label", ["ARIE Finance", "ARIE Finance Ltd"])
def test_public_validation_case_is_explicit_and_sourced(label: str) -> None:
    candidates = build_fixture_providers().registry.discover_candidates(label)
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.legal_name == "ARIE Finance Ltd"
    assert candidate.jurisdiction == "MU"
    assert candidate.registry_id == "C221997"
    assert candidate.source_ref is not None
    assert candidate.source_ref.startswith("https://companies.govmu.org/")


def test_unknown_company_fails_with_explicit_demo_limitation() -> None:
    with pytest.raises(DemoDatasetUnsupported, match="management-demo dataset"):
        build_fixture_providers().registry.discover_candidates("Unknown Example Holdings")


def test_domain_fixture_uses_canonical_test_domain() -> None:
    dom = build_fixture_providers().domain.lookup("vantar-energy.test")
    assert dom is not None
    assert dom.domain in ALLOWED_DOMAINS
    assert dom.domain.endswith(".test")  # fictional TLD only


def test_screening_fixture_subject_is_fictional() -> None:
    scr = build_fixture_providers().screening
    for hit in scr.screen("Amara"):
        # match_basis / list names must not carry a real entity name.
        assert hit.subject_label == "Amara"


def test_management_demo_relationship_and_screening_are_deterministic() -> None:
    providers = build_fixture_providers()
    officers = providers.registry.discover_officers("Daniel Kim", "SG", "201800202P")
    assert [officer["name"] for officer in officers] == ["Daniel Kim"]
    assert providers.registry.discover_officers("Michael Grant", "AE", "AGF-52003") == []

    hits = providers.screening.screen("Victor Lane")
    assert len(hits) == 1
    assert hits[0].state == "POTENTIAL_MATCH"
    assert hits[0].profile_id == "fixture-profile-victor-lane-01"
    assert providers.screening.screen("Amira Hassan") == []
