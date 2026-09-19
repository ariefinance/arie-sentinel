"""Companies House enrichment: officers + PSC consumption and graph relationships."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from arie_sentinel.models.core import EntityCandidate
from arie_sentinel.models.evidence import Source
from arie_sentinel.providers.companies_house import CompaniesHouseProfile, CompaniesHouseProvider
from arie_sentinel.services.graph import build_graph
from arie_sentinel.services.investigations import (
    _run_supplementary_sources,
    create_investigation,
    get_or_create_counterparty,
)

ANALYST = "analyst@example.test"


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


class _FakeCH:
    def get_company(self, number: str) -> CompaniesHouseProfile:
        return CompaniesHouseProfile(
            company_number=number,
            name="Zenith Global Traders Ltd",
            status="active",
            incorporation_date="2015-01-01",
            registered_address="1 High St, London",
        )

    def get_officers(self, number: str):
        return [
            {
                "name": "Robert Vance",
                "position": "director",
                "start_date": "2015-01-01",
                "end_date": None,
            },
        ]

    def get_psc(self, number: str):
        return [
            {
                "name": "Helena Ward",
                "kind": "individual-person-with-significant-control",
                "natures_of_control": ["ownership-of-shares-75-to-100-percent"],
                "notified_on": "2016-04-06",
                "ceased_on": None,
            },
        ]


def _gb_investigation(db: Session):
    inv = create_investigation(
        db, company_label="Zenith Global Traders Ltd", contact_label="Robert Vance", actor=ANALYST
    )
    db.flush()
    cp, _ = get_or_create_counterparty(
        db,
        EntityCandidate(
            investigation_id=inv.investigation_id,
            legal_name="Zenith Global Traders Ltd",
            jurisdiction="GB",
            registry_class="companies_house",
            registry_id="14750888",
            legal_status="active",
            registered_address=None,
            incorporation_date=None,
            lei=None,
            alternative_names=[],
            provider="test",
            retrieved_at=inv.created_at,
        ),
    )
    inv.counterparty_id = cp.counterparty_id
    inv.counterparty = cp
    db.flush()
    return inv


def test_enrichment_consumes_officers_and_psc(db: Session) -> None:
    inv = _gb_investigation(db)
    _run_supplementary_sources(db, inv, SimpleNamespace(companies_house=_FakeCH()))
    db.flush()
    titles = [
        s.title
        for s in db.scalars(select(Source).where(Source.investigation_id == inv.investigation_id))
    ]
    assert any(t.startswith("Companies House:") for t in titles)
    assert any(t.startswith("Companies House officer:") for t in titles)
    assert any(t.startswith("Companies House PSC:") for t in titles)


def test_officer_match_verifies_contact_and_graph_has_psc_edge(db: Session) -> None:
    inv = _gb_investigation(db)
    _run_supplementary_sources(db, inv, SimpleNamespace(companies_house=_FakeCH()))
    db.flush()
    # The supplied contact matches an officer -> relationship verified.
    assert inv.candidates[0].relationship_state.value == "VERIFIED"
    graph = build_graph(db, inv)
    edge_types = {e.type for e in graph.edges}
    # A "director" officer surfaces as DIRECTOR_OF (OFFICER_OF for other roles).
    assert edge_types & {"DIRECTOR_OF", "OFFICER_OF"}
    assert "PERSON_WITH_SIGNIFICANT_CONTROL_OF" in edge_types
    psc_edge = next(e for e in graph.edges if e.type == "PERSON_WITH_SIGNIFICANT_CONTROL_OF")
    assert psc_edge.source_ids  # carries real provenance


def test_get_psc_parses_items() -> None:
    provider = CompaniesHouseProvider("free-key", "https://ch.test")
    provider.client = _client(
        lambda request: httpx.Response(
            200,
            json={
                "items": [
                    {
                        "name": "Helena Ward",
                        "kind": "individual-person-with-significant-control",
                        "natures_of_control": ["ownership-of-shares-75-to-100-percent"],
                        "notified_on": "2016-04-06",
                    }
                ]
            },
            request=request,
        )
    )
    pscs = provider.get_psc("14750888")
    assert pscs[0]["name"] == "Helena Ward"
    assert pscs[0]["natures_of_control"] == ["ownership-of-shares-75-to-100-percent"]
