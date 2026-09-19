"""Background worker: normal processing, and crash/stale-lock recovery."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from arie_sentinel.jobs import worker
from arie_sentinel.jobs.worker import (
    reclaim_stale_jobs,
    refresh_sanctions_if_due,
    run_pending_jobs,
)
from arie_sentinel.models.core import EntityCandidate, Identifier, Investigation
from arie_sentinel.models.enums import CompanyIdentityStatus, InvestigationState, JobStatus
from arie_sentinel.models.evidence import Evidence, Finding, ScreeningResult, Source
from arie_sentinel.models.ops import Job
from arie_sentinel.services.investigations import create_investigation, resolve_entity

ANALYST = "analyst@example.test"


def _job_for(db: Session, inv: Investigation, job_type: str = "discovery") -> Job:
    return db.scalar(
        select(Job).where(
            Job.investigation_id == inv.investigation_id,
            Job.job_type == job_type,
        )
    )


def test_worker_processes_discovery(db: Session) -> None:
    inv = create_investigation(
        db, company_label="Vantar - Castellan", contact_label="Jordan Rivera", actor=ANALYST
    )
    db.commit()
    processed = run_pending_jobs(db)
    assert processed == 1
    db.expire_all()
    inv = db.get(Investigation, inv.investigation_id)
    assert inv.company_identity_status is CompanyIdentityStatus.AMBIGUOUS
    assert inv.investigation_state is InvestigationState.PARTIAL_RESULTS
    assert _job_for(db, inv).status is JobStatus.SUCCEEDED


def test_stale_running_job_is_reclaimed_after_crash(db: Session) -> None:
    inv = create_investigation(
        db, company_label="Vantar - Castellan", contact_label="Jordan Rivera", actor=ANALYST
    )
    db.commit()
    # Simulate a worker that claimed the job then crashed: RUNNING, lease expired.
    job = _job_for(db, inv)
    job.status = JobStatus.RUNNING
    job.locked_at = datetime.now(UTC) - timedelta(minutes=30)
    job.locked_by = "dead-worker"
    db.commit()

    reclaimed = reclaim_stale_jobs(db)
    assert reclaimed == 1
    db.expire_all()
    assert _job_for(db, inv).status is JobStatus.PENDING

    # A healthy worker now completes it.
    assert run_pending_jobs(db) == 1
    db.expire_all()
    assert db.get(Investigation, inv.investigation_id).company_identity_status is (
        CompanyIdentityStatus.AMBIGUOUS
    )


def test_fresh_running_job_is_not_reclaimed(db: Session) -> None:
    inv = create_investigation(
        db, company_label="Vantar - Castellan", contact_label="Jordan Rivera", actor=ANALYST
    )
    db.commit()
    job = _job_for(db, inv)
    job.status = JobStatus.RUNNING
    job.locked_at = datetime.now(UTC)  # just claimed
    job.locked_by = "live-worker"
    db.commit()
    assert reclaim_stale_jobs(db) == 0


def _resolved_investigation(db: Session) -> Investigation:
    inv = create_investigation(
        db, company_label="Vantar - Castellan", contact_label="Jordan Rivera", actor=ANALYST
    )
    db.commit()
    assert run_pending_jobs(db) == 1
    db.refresh(inv)
    candidate = db.scalar(
        select(EntityCandidate).where(EntityCandidate.investigation_id == inv.investigation_id)
    )
    assert candidate is not None
    resolve_entity(db, inv, candidate, actor=ANALYST, rationale="Registry identifier checked")
    db.commit()
    return inv


def test_resolution_commits_and_enqueues_without_calling_providers(db: Session) -> None:
    inv = _resolved_investigation(db)
    db.refresh(inv)

    assert inv.company_identity_status is CompanyIdentityStatus.CONFIRMED
    assert inv.investigation_state is InvestigationState.PARTIAL_RESULTS
    assert _job_for(db, inv, "enrichment").status is JobStatus.PENDING


def test_enrichment_failure_does_not_undo_confirmed_resolution(db: Session, monkeypatch) -> None:
    inv = _resolved_investigation(db)

    def provider_failure(*args, **kwargs) -> None:
        raise RuntimeError("simulated external provider failure")

    monkeypatch.setattr(worker, "run_enrichment", provider_failure)
    assert run_pending_jobs(db) == 3
    db.expire_all()

    persisted = db.get(Investigation, inv.investigation_id)
    assert persisted is not None
    assert persisted.company_identity_status is CompanyIdentityStatus.CONFIRMED
    assert persisted.counterparty_id is not None
    failed_job = _job_for(db, persisted, "enrichment")
    assert failed_job.status is JobStatus.FAILED
    assert "simulated external provider failure" in (failed_job.last_error or "")


def test_enrichment_completes_and_retry_is_idempotent(db: Session) -> None:
    inv = _resolved_investigation(db)
    assert run_pending_jobs(db) == 1
    db.expire_all()
    persisted = db.get(Investigation, inv.investigation_id)
    assert persisted is not None
    assert persisted.investigation_state is InvestigationState.COMPLETED

    material_models = (EntityCandidate, Source, Evidence, ScreeningResult, Finding, Identifier)
    before = {
        model.__tablename__: db.scalar(select(func.count()).select_from(model))
        for model in material_models
    }
    enrichment_job = _job_for(db, persisted, "enrichment")
    enrichment_job.status = JobStatus.PENDING
    db.commit()

    assert run_pending_jobs(db) == 1
    after = {
        model.__tablename__: db.scalar(select(func.count()).select_from(model))
        for model in material_models
    }
    assert after == before


def test_sanctions_refresh_runs_at_most_once_per_interval(db: Session, monkeypatch) -> None:
    calls: list[int] = []

    def fake_refresh(session: Session):
        calls.append(1)
        return []

    monkeypatch.setattr(worker, "refresh_feeds", fake_refresh)
    monkeypatch.setattr(worker, "_last_sanctions_refresh_at", None)
    monkeypatch.setattr(
        worker,
        "get_settings",
        lambda: type("SettingsStub", (), {
            "sanctions_worker_auto_refresh": True,
            "sanctions_worker_refresh_interval_seconds": 86400,
        })(),
    )

    assert refresh_sanctions_if_due(db, now_monotonic=100.0) is True
    assert refresh_sanctions_if_due(db, now_monotonic=101.0) is False
    assert (
        refresh_sanctions_if_due(
            db, now_monotonic=86500.0
        )
        is True
    )
    assert len(calls) == 2


def test_sanctions_refresh_failure_does_not_raise_or_retry_tightly(
    db: Session, monkeypatch
) -> None:
    calls: list[int] = []

    def failing_refresh(session: Session):
        calls.append(1)
        raise RuntimeError("simulated refresh outage")

    monkeypatch.setattr(worker, "refresh_feeds", failing_refresh)
    monkeypatch.setattr(worker, "_last_sanctions_refresh_at", None)
    monkeypatch.setattr(
        worker,
        "get_settings",
        lambda: type("SettingsStub", (), {
            "sanctions_worker_auto_refresh": True,
            "sanctions_worker_refresh_interval_seconds": 86400,
        })(),
    )

    assert refresh_sanctions_if_due(db, now_monotonic=200.0) is True
    assert refresh_sanctions_if_due(db, now_monotonic=201.0) is False
    assert len(calls) == 1


def test_sanctions_refresh_is_disabled_by_default(db: Session, monkeypatch) -> None:
    calls: list[int] = []

    def fake_refresh(session: Session):
        calls.append(1)
        return []

    monkeypatch.setattr(worker, "refresh_feeds", fake_refresh)
    monkeypatch.setattr(worker, "_last_sanctions_refresh_at", None)
    monkeypatch.setattr(
        worker,
        "get_settings",
        lambda: type("SettingsStub", (), {
            "sanctions_worker_auto_refresh": False,
            "sanctions_worker_refresh_interval_seconds": 86400,
        })(),
    )

    assert refresh_sanctions_if_due(db, now_monotonic=1.0) is False
    assert calls == []
