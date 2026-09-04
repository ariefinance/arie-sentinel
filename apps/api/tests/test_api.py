"""API: async vertical path, validation (no silent filter fallback), worklist, audit."""

from __future__ import annotations

from fastapi.testclient import TestClient

from arie_sentinel.db import SessionLocal
from arie_sentinel.jobs.worker import run_pending_jobs

ANALYST = {"X-Dev-Role": "analyst"}


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
    assert got["investigation_state"] == "COMPLETED"
    assert got["company_identity_status"] == "CONFIRMED"
    assert got["counterparty"]["legal_name"] == "Vantar Energy Trading FZE"
    assert got["company_label"] == "Vantar - Castellan"


def test_clarification_required_path(client: TestClient) -> None:
    body = client.post(
        "/investigations",
        json={"company_label": "TBD", "contact_label": "Amara"},
        headers=ANALYST,
    ).json()
    assert body["intake_state"] == "CLARIFICATION_REQUIRED"
    assert body["clarification_reason"]
    assert body["counterparty"] is None


def test_validation_rejects_missing_field(client: TestClient) -> None:
    resp = client.post(
        "/investigations", json={"company_label": "Vantar - Castellan"}, headers=ANALYST
    )
    assert resp.status_code == 422


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
    assert "LINK_COUNTERPARTY" in actions


def test_health(client: TestClient) -> None:
    assert client.get("/health").json()["database"] == "ok"
