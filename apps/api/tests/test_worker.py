"""Background worker: normal processing, and crash/stale-lock recovery."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from arie_sentinel.jobs.worker import reclaim_stale_jobs, run_pending_jobs
from arie_sentinel.models.core import Investigation
from arie_sentinel.models.enums import CompanyIdentityStatus, JobStatus
from arie_sentinel.models.ops import Job
from arie_sentinel.services.investigations import create_investigation

ANALYST = "analyst@example.test"


def _job_for(db: Session, inv: Investigation) -> Job:
    return db.scalar(select(Job).where(Job.investigation_id == inv.investigation_id))


def test_worker_processes_discovery(db: Session) -> None:
    inv = create_investigation(
        db, company_label="Vantar - Castellan", contact_label="Jordan Rivera", actor=ANALYST
    )
    db.commit()
    processed = run_pending_jobs(db)
    assert processed == 1
    db.expire_all()
    inv = db.get(Investigation, inv.investigation_id)
    assert inv.company_identity_status is CompanyIdentityStatus.CONFIRMED
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
        CompanyIdentityStatus.CONFIRMED
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
