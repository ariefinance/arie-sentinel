"""API: async vertical path, validation (no silent filter fallback), worklist, audit."""

from __future__ import annotations

from fastapi.testclient import TestClient

from arie_sentinel.db import SessionLocal
from arie_sentinel.jobs.worker import run_pending_jobs

ANALYST = {"X-Dev-Role": "analyst"}
MANAGER = {"X-Dev-Role": "manager"}


def _drain_jobs() -> None:
    session = SessionLocal()
    try:
        run_pending_jobs(session)
    finally:
        session.close()


def test_create_returns_promptly_then_worker_resolves(client: TestClient) -> None:
    resp = client.post(
        "/investigations",
        json={"company_label": "Vantar - Castellan", "contact_label": "Jordan Rivera"},
        headers=ANALYST,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    # Request handler does NOT process the queue: identity is not resolved yet.
    assert body["intake_state"] == "SUFFICIENT_FOR_DISCOVERY"
    assert body["investigation_state"] == "NOT_STARTED"
    assert body["company_identity_status"] is None
    assert body["counterparty"] is None
    inv_id = body["investigation_id"]

    # The standalone worker processes discovery.
    _drain_jobs()

    got = client.get(f"/investigations/{inv_id}", headers=ANALYST).json()
    assert got["investigation_state"] == "PARTIAL_RESULTS"
    assert got["company_identity_status"] == "AMBIGUOUS"
    assert got["counterparty"] is None
    assert len(got["entity_candidates"]) == 1
    assert got["company_label"] == "Vantar - Castellan"

    resolved = client.post(
        f"/investigations/{inv_id}/resolve-entity",
        json={
            "candidate_id": got["entity_candidates"][0]["entity_candidate_id"],
            "rationale": "Registry number and jurisdiction checked",
        },
        headers=ANALYST,
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["investigation_state"] == "PARTIAL_RESULTS"
    _drain_jobs()
    assert resolved.json()["company_identity_status"] == "CONFIRMED"
    assert resolved.json()["counterparty"]["legal_name"] == "Vantar Energy Trading FZE"


def test_clarification_required_path(client: TestClient) -> None:
    body = client.post(
        "/investigations",
        json={"company_label": "TBD", "contact_label": "Amara"},
        headers=ANALYST,
    ).json()
    assert body["intake_state"] == "CLARIFICATION_REQUIRED"
    assert body["clarification_reason"]
    assert body["counterparty"] is None


def test_company_only_investigation_runs_without_person_workflow(client: TestClient) -> None:
    created = client.post(
        "/investigations",
        json={"company_label": "Meridian Energy Supplies Ltd"},
        headers=ANALYST,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["contact_label"] == ""
    assert body["intake_state"] == "SUFFICIENT_FOR_DISCOVERY"
    assert body["candidates"] == []
    inv_id = body["investigation_id"]

    _drain_jobs()
    discovered = client.get(f"/investigations/{inv_id}", headers=ANALYST).json()
    assert discovered["investigation_state"] == "PARTIAL_RESULTS"
    assert len(discovered["entity_candidates"]) == 1
    resolved = client.post(
        f"/investigations/{inv_id}/resolve-entity",
        json={
            "candidate_id": discovered["entity_candidates"][0]["entity_candidate_id"],
            "rationale": "Fictional registry identifier checked",
        },
        headers=ANALYST,
    )
    assert resolved.status_code == 200, resolved.text
    _drain_jobs()

    enriched = client.get(f"/investigations/{inv_id}", headers=ANALYST).json()
    assert enriched["investigation_state"] == "COMPLETED"
    assert enriched["company_identity_status"] == "CONFIRMED"
    assert enriched["candidates"] == []
    assert enriched["screening_state"] == "NO_MATERIAL_MATCH"
    screening_sources = [
        source
        for source in client.get(f"/investigations/{inv_id}/sources", headers=ANALYST).json()
        if source["source_class"] == "sanctions_pep_screening"
    ]
    assert [source["title"] for source in screening_sources] == [
        "Screening search: Meridian Energy Supplies Ltd"
    ]
    findings = client.get(f"/investigations/{inv_id}/findings", headers=ANALYST).json()
    assert all(
        finding["title"] != "Named contact relationship not established" for finding in findings
    )

    report = client.post(
        f"/investigations/{inv_id}/report",
        json={"confirm_finalise": True},
        headers=MANAGER,
    )
    assert report.status_code == 200, report.text
    assert report.content.startswith(b"%PDF")


def test_public_validation_aliases_and_unknown_demo_company(client: TestClient) -> None:
    for label in ("ARIE Finance", "ARIE Finance Ltd"):
        created = client.post("/investigations", json={"company_label": label}, headers=ANALYST)
        assert created.status_code == 201, created.text
        assert created.json()["case_type"] == "PUBLIC_VALIDATION_CASE"
        assert created.json()["candidates"] == []
        _drain_jobs()
        discovered = client.get(
            f"/investigations/{created.json()['investigation_id']}", headers=ANALYST
        ).json()
        assert len(discovered["entity_candidates"]) == 1
        candidate = discovered["entity_candidates"][0]
        assert candidate["legal_name"] == "ARIE Finance Ltd"
        assert candidate["jurisdiction"] == "MU"
        assert candidate["registry_id"] == "C221997"

    unknown = client.post(
        "/investigations",
        json={"company_label": "Unknown Example Holdings"},
        headers=ANALYST,
    ).json()
    _drain_jobs()
    unknown = client.get(f"/investigations/{unknown['investigation_id']}", headers=ANALYST).json()
    assert unknown["investigation_state"] == "SOURCE_UNAVAILABLE"
    assert unknown["company_identity_status"] is None
    assert "Not available in the management-demo dataset" in unknown["clarification_reason"]
    assert unknown["entity_candidates"] == []


def test_worklist_invalid_filter_is_422_not_silent_all(client: TestClient) -> None:
    resp = client.get("/worklist", params={"filter": "bogus"}, headers=ANALYST)
    assert resp.status_code == 422


def test_worklist_needs_action_surfaces_ambiguous(client: TestClient) -> None:
    client.post(
        "/investigations",
        json={"company_label": "Vantar Energy Trading", "contact_label": "Jordan Rivera"},
        headers=ANALYST,
    )
    _drain_jobs()
    items = client.get("/worklist", params={"filter": "needs_action"}, headers=ANALYST).json()
    assert len(items) == 1
    assert items[0]["needs_action"] is True
    assert items[0]["company_identity_status"] == "AMBIGUOUS"


def test_audit_endpoint_lists_events(client: TestClient) -> None:
    created = client.post(
        "/investigations",
        json={"company_label": "Vantar - Castellan", "contact_label": "Jordan Rivera"},
        headers=ANALYST,
    ).json()
    _drain_jobs()
    resp = client.get(f"/investigations/{created['investigation_id']}/audit", headers=ANALYST)
    assert resp.status_code == 200
    actions = [e["action"] for e in resp.json()]
    assert "INVESTIGATION_CREATED" in actions
    assert "STATE_CHANGE" in actions


def test_health(client: TestClient) -> None:
    assert client.get("/health").json()["database"] == "ok"


def test_management_demo_commodities_scenarios(client: TestClient) -> None:
    ambiguous = client.post(
        "/investigations",
        json={"company_label": "Orion Petro Trading", "contact_label": "Karim Mansour"},
        headers=ANALYST,
    ).json()
    _drain_jobs()
    ambiguous = client.get(
        f"/investigations/{ambiguous['investigation_id']}", headers=ANALYST
    ).json()
    assert ambiguous["company_identity_status"] == "AMBIGUOUS"
    assert len(ambiguous["entity_candidates"]) == 3

    scenarios = [
        ("Pacific Energy Procurement Ltd", "Daniel Kim", "VERIFIED", "NO_MATERIAL_MATCH"),
        ("Atlas Global Fuels", "Michael Grant", "UNVERIFIED", "NO_MATERIAL_MATCH"),
        ("Northstar Petroleum Trading", "Victor Lane", "UNVERIFIED", "POTENTIAL_MATCH"),
        ("Meridian Energy Supplies Ltd", "Amira Hassan", "UNVERIFIED", "NO_MATERIAL_MATCH"),
    ]
    verified_match_basis = ""
    for company, contact, expected_relationship, expected_screening in scenarios:
        created = client.post(
            "/investigations",
            json={"company_label": company, "contact_label": contact},
            headers=ANALYST,
        ).json()
        _drain_jobs()
        discovered = client.get(
            f"/investigations/{created['investigation_id']}", headers=ANALYST
        ).json()
        assert len(discovered["entity_candidates"]) == 1
        resolved = client.post(
            f"/investigations/{created['investigation_id']}/resolve-entity",
            json={
                "candidate_id": discovered["entity_candidates"][0]["entity_candidate_id"],
                "rationale": "Fictional management-demo registry identifier checked",
            },
            headers=ANALYST,
        )
        assert resolved.status_code == 200
        _drain_jobs()
        enriched = client.get(
            f"/investigations/{created['investigation_id']}", headers=ANALYST
        ).json()
        assert enriched["company_identity_status"] == "CONFIRMED"
        assert enriched["candidates"][0]["relationship_state"] == expected_relationship
        assert enriched["screening_state"] == expected_screening
        if expected_relationship == "VERIFIED":
            verified_match_basis = enriched["candidates"][0]["match_basis"]

    assert "physical identity" in verified_match_basis


def test_evidence_review_and_report_flow(client: TestClient) -> None:
    created = client.post(
        "/investigations",
        json={"company_label": "Vantar - Castellan", "contact_label": "Jordan Rivera"},
        headers=ANALYST,
    ).json()
    inv_id = created["investigation_id"]
    _drain_jobs()
    discovered = client.get(f"/investigations/{inv_id}", headers=ANALYST).json()
    candidate_id = discovered["entity_candidates"][0]["entity_candidate_id"]
    resolved = client.post(
        f"/investigations/{inv_id}/resolve-entity",
        json={"candidate_id": candidate_id, "rationale": "Registry identifier checked"},
        headers=ANALYST,
    )
    assert resolved.status_code == 200, resolved.text
    _drain_jobs()

    sources = client.get(f"/investigations/{inv_id}/sources", headers=ANALYST).json()
    assert sources
    assert all(source["retrieved_at"] for source in sources)

    screening = client.get(f"/investigations/{inv_id}/screening", headers=ANALYST).json()
    assert screening and screening[0]["state"] == "POTENTIAL_MATCH"
    reviewed = client.post(
        f"/screening-results/{screening[0]['screening_result_id']}/review",
        json={"disposition": "FALSE_POSITIVE", "rationale": "Identifiers do not match"},
        headers=ANALYST,
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["analyst_disposition"] == "FALSE_POSITIVE"

    findings = client.get(f"/investigations/{inv_id}/findings", headers=ANALYST).json()
    assert findings
    finding_review = client.post(
        f"/findings/{findings[0]['finding_id']}/review",
        json={"disposition": "CONFIRMED", "rationale": "Evidence gap remains"},
        headers=ANALYST,
    )
    assert finding_review.status_code == 200

    report = client.post(
        f"/investigations/{inv_id}/report",
        json={"confirm_finalise": True},
        headers=MANAGER,
    )
    assert report.status_code == 200, report.text
    assert report.headers["content-type"] == "application/pdf"
    assert report.content.startswith(b"%PDF")

    actions = [
        row["action"]
        for row in client.get(f"/investigations/{inv_id}/audit", headers=ANALYST).json()
    ]
    assert "RESOLVE_IDENTITY" in actions
    assert "REVIEW_SCREENING" in actions
    assert "REVIEW_FINDING" in actions
    assert "FINALISE_REPORT" in actions


def test_report_finalisation_requires_manager_confirmation_and_resolution(
    client: TestClient,
) -> None:
    created = client.post(
        "/investigations",
        json={"company_label": "Vantar - Castellan", "contact_label": "Jordan Rivera"},
        headers=ANALYST,
    ).json()
    inv_id = created["investigation_id"]

    unresolved = client.post(
        f"/investigations/{inv_id}/report",
        json={"confirm_finalise": True},
        headers=MANAGER,
    )
    assert unresolved.status_code == 409

    _drain_jobs()
    candidate_id = client.get(f"/investigations/{inv_id}", headers=ANALYST).json()[
        "entity_candidates"
    ][0]["entity_candidate_id"]
    client.post(
        f"/investigations/{inv_id}/resolve-entity",
        json={"candidate_id": candidate_id, "rationale": "Registry identifier checked"},
        headers=ANALYST,
    )

    analyst = client.post(
        f"/investigations/{inv_id}/report",
        json={"confirm_finalise": True},
        headers=ANALYST,
    )
    assert analyst.status_code == 403

    unconfirmed = client.post(
        f"/investigations/{inv_id}/report",
        json={"confirm_finalise": False},
        headers=MANAGER,
    )
    assert unconfirmed.status_code == 422
