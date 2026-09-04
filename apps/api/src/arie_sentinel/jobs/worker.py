"""PostgreSQL-backed job worker (SELECT ... FOR UPDATE SKIP LOCKED).

TECHNICAL CHALLENGE (recorded, resolved): the frozen stack named `procrastinate`.
For Stage 1 the only job is fixture discovery. A small SKIP-LOCKED worker with an
explicit **lease** (stale-lock recovery) and bounded retries is simpler and
dependency-free, and the `Job` table stays queue-agnostic so procrastinate can
replace it later without touching callers. Correctness requirements met here:
- the worker is independently runnable (`python -m arie_sentinel.jobs.worker`);
- a job left RUNNING by a crashed worker is reclaimed after the lease expires;
- failures retry up to max_attempts, then land in FAILED (never lost, never
  stuck RUNNING forever);
- request handlers NEVER process the queue.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models.enums import JobStatus
from ..models.ops import Job
from ..services.investigations import run_discovery

logger = logging.getLogger("arie_sentinel.worker")

WORKER_ID = f"worker-{uuid.uuid4().hex[:8]}"
# A claimed job must complete within the lease; otherwise it is presumed the
# worker crashed and the job is reclaimed for another worker.
LEASE = timedelta(minutes=5)


def reclaim_stale_jobs(session: Session) -> int:
    """Return stuck RUNNING jobs (lease expired) to PENDING so they are retried."""
    cutoff = datetime.now(UTC) - LEASE
    stale_ids = list(
        session.scalars(
            select(Job.job_id).where(Job.status == JobStatus.RUNNING, Job.locked_at < cutoff)
        )
    )
    if stale_ids:
        session.execute(
            update(Job)
            .where(Job.job_id.in_(stale_ids))
            .values(status=JobStatus.PENDING, locked_at=None, locked_by=None)
        )
        session.commit()
    return len(stale_ids)


def claim_one_job(session: Session) -> Job | None:
    """Atomically claim the oldest runnable pending job; None if the queue is empty."""
    stmt = (
        select(Job)
        .where(Job.status == JobStatus.PENDING, Job.run_after <= datetime.now(UTC))
        .order_by(Job.run_after.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    job = session.scalar(stmt)
    if job is None:
        return None
    job.status = JobStatus.RUNNING
    job.locked_at = datetime.now(UTC)
    job.locked_by = WORKER_ID
    job.attempts += 1
    session.flush()
    return job


def _dispatch(session: Session, job: Job) -> None:
    if job.job_type == "discovery":
        payload = job.payload or {}
        run_discovery(session, uuid.UUID(str(payload["investigation_id"])))
    else:
        raise ValueError(f"unknown job_type: {job.job_type}")


def run_pending_jobs(session: Session, *, max_jobs: int = 100) -> int:
    """Process up to ``max_jobs`` runnable jobs. Returns the number processed.

    Reclaims stale jobs first. Each job runs in its own committed transaction so
    one failure cannot roll back another job's work. NOT for use in a request
    handler — call from the standalone worker (or tests).
    """
    reclaim_stale_jobs(session)
    processed = 0
    for _ in range(max_jobs):
        job = claim_one_job(session)
        if job is None:
            break
        job_id = job.job_id
        session.commit()  # persist the claim before doing the work
        try:
            _dispatch(session, job)
            job.status = JobStatus.SUCCEEDED
            job.last_error = None
            job.locked_at = None
            job.locked_by = None
            session.commit()
        except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
            session.rollback()
            reloaded = session.get(Job, job_id)
            if reloaded is not None:
                reloaded.last_error = f"{type(exc).__name__}: {exc}"
                reloaded.status = (
                    JobStatus.FAILED
                    if reloaded.attempts >= reloaded.max_attempts
                    else JobStatus.PENDING
                )
                reloaded.locked_at = None
                reloaded.locked_by = None
                session.commit()
            logger.warning("job %s failed: %s", job_id, exc)
        processed += 1
    return processed


def run_worker(poll_interval: float = 2.0, *, run_once: bool = False) -> None:
    """Long-running worker loop. Safe to run as multiple concurrent processes."""
    logger.info("worker %s starting (lease=%s)", WORKER_ID, LEASE)
    while True:
        session = SessionLocal()
        try:
            processed = run_pending_jobs(session)
        finally:
            session.close()
        if run_once:
            return
        if processed == 0:
            time.sleep(poll_interval)


if __name__ == "__main__":  # pragma: no cover - operational entrypoint
    logging.basicConfig(level=logging.INFO)
    run_worker()
