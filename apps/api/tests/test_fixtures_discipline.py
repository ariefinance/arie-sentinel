"""Fictional-fixture discipline — enforced by an ALLOW-LIST, never a denylist.

We deliberately do not embed any real/management-derived label here (a denylist
would itself reintroduce that operational data). Instead we assert that the
fixtures only ever emit the canonical invented names from docs/EXAMPLE-FIXTURES.md.
Secret scanning (gitleaks) and the committed-data guard live in CI.
"""

from __future__ import annotations

from arie_sentinel.providers.fixtures import build_fixture_providers

# The ONLY entity name-stems permitted anywhere in fixtures/tests/examples.
ALLOWED_NAME_STEMS = ("Vantar", "Castellan")
ALLOWED_DOMAINS = ("vantar-energy.test",)


def test_registry_fixtures_emit_only_canonical_names() -> None:
    reg = build_fixture_providers().registry
    labels = ["Vantar - Castellan", "Vantar Energy Trading", "Castellan Trading", "unknown co"]
    for label in labels:
        for cand in reg.discover_candidates(label):
            assert cand.legal_name.startswith(ALLOWED_NAME_STEMS), cand.legal_name


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
