"""PostgreSQL-backed job worker (SELECT ... FOR UPDATE SKIP LOCKED).

TECHNICAL CHALLENGE (recorded, resolved): the frozen stack named `procrastinate`.
Phase 1 discovery and enrichment use a small SKIP-LOCKED worker with an
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

from ..audit import record_audit
from ..config import get_settings
from ..db import SessionLocal
from ..models.core import Investigation
from ..models.enums import AuditAction, InvestigationState, JobStatus
from ..models.ops import Job
from ..services.investigations import run_discovery, run_enrichment
from ..services.sanctions_cache import refresh_feeds

logger = logging.getLogger("arie_sentinel.worker")

WORKER_ID = f"worker-{uuid.uuid4().hex[:8]}"
# A claimed job must complete within the lease; otherwise it is presumed the
# worker crashed and the job is reclaimed for another worker.
LEASE = timedelta(minutes=5)

# Railway's demo plan cannot provision a separate cron service. Reuse the already-running
# worker process to refresh the free official sanctions cache once every 24 hours. A failed
# refresh is logged and never stops queue processing; refresh_feeds itself retains prior
# cached records and fails closed on required-feed errors.
_last_sanctions_refresh_at: float | None = None


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
    elif job.job_type == "enrichment":
        payload = job.payload or {}
        run_enrichment(
            session,
            uuid.UUID(str(payload["investigation_id"])),
            uuid.UUID(str(payload["candidate_id"])),
        )
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
            terminal = False
            if reloaded is not None:
                reloaded.last_error = f"{type(exc).__name__}: {exc}"
                terminal = reloaded.attempts >= reloaded.max_attempts
                reloaded.status = JobStatus.FAILED if terminal else JobStatus.PENDING
                reloaded.locked_at = None
                reloaded.locked_by = None
                session.commit()
            if terminal and reloaded is not None:
                _mark_investigation_failed(session, reloaded, exc)
            logger.warning("job %s failed: %s", job_id, exc)
        processed += 1
    return processed


def _mark_investigation_failed(session: Session, job: Job, exc: Exception) -> None:
    """On terminal job failure, surface it on the investigation and audit it.

    A terminally failed discovery/enrichment job must not leave the investigation
    stuck in a non-terminal state (NOT_STARTED/RUNNING/PARTIAL_RESULTS) with no
    explanation. The confirmed legal entity, if any, is preserved; only the
    lifecycle state moves to FAILED.
    """
    payload = job.payload or {}
    raw_id = payload.get("investigation_id")
    if not raw_id:
        return
    try:
        investigation_id = uuid.UUID(str(raw_id))
    except (ValueError, TypeError):
        return
    investigation = session.get(Investigation, investigation_id)
    if investigation is None or investigation.investigation_state is InvestigationState.FAILED:
        return
    investigation.investigation_state = InvestigationState.FAILED
    record_audit(
        session,
        actor="worker",
        action=AuditAction.STATE_CHANGE,
        object_type="investigation",
        investigation_id=investigation_id,
        rationale=f"{job.job_type} job failed after {job.attempts} attempt(s): {exc}",
        payload={"investigation_state": InvestigationState.FAILED.value, "job_type": job.job_type},
    )
    session.commit()


def refresh_sanctions_if_due(session: Session, *, now_monotonic: float | None = None) -> bool:
    """Refresh official sanctions feeds at most once per 24 hours per worker process.

    Returns True when a refresh attempt ran. The timestamp is advanced before network
    work begins so an upstream outage cannot create a tight retry loop. Provider/feed
    failures are recorded by refresh_feeds and do not kill the investigation worker.
    """
    global _last_sanctions_refresh_at

    settings = get_settings()
    if not settings.sanctions_worker_auto_refresh:
        return False

    interval = max(300, settings.sanctions_worker_refresh_interval_seconds)
    now = time.monotonic() if now_monotonic is None else now_monotonic
    if _last_sanctions_refresh_at is not None and now - _last_sanctions_refresh_at < interval:
        return False
    _last_sanctions_refresh_at = now

    try:
        results = refresh_feeds(session)
        session.commit()
    except Exception as exc:  # noqa: BLE001 - refresh must never kill worker
        session.rollback()
        logger.warning("sanctions refresh failed unexpectedly; worker continues: %s", exc)
        return True

    failures = 0
    for result in results:
        if result.status == "ok":
            logger.info("sanctions feed %s: %d entities", result.feed, result.entity_count)
        else:
            failures += 1
            logger.warning("sanctions feed %s failed: %s", result.feed, result.detail)
    logger.info("sanctions refresh complete: %d feed(s), %d failure(s)", len(results), failures)
    return True


def run_worker(
    poll_interval: float = 2.0,
    *,
    run_once: bool = False,
    max_cycles: int | None = None,
    error_backoff: float = 5.0,
) -> None:
    """Long-running worker loop. Safe to run as multiple concurrent processes.

    A transient error in polling/claim/reclaim (a DB blip outside a single job's
    dispatch) must not kill the worker: the cycle is logged, the session rolled
    back, and the loop continues after a bounded backoff. ``max_cycles`` bounds
    the loop for tests; ``None`` runs indefinitely.
    """
    logger.info("worker %s starting (lease=%s)", WORKER_ID, LEASE)
    cycles = 0
    while True:
        processed = 0
        errored = False
        session = SessionLocal()
        try:
            processed = run_pending_jobs(session)
            refresh_sanctions_if_due(session)
        except Exception as exc:  # noqa: BLE001 - logged, not swallowed; worker survives
            errored = True
            try:
                session.rollback()
            except Exception:  # noqa: BLE001 - best-effort cleanup
                logger.exception("worker %s failed to roll back after cycle error", WORKER_ID)
            logger.warning("worker %s cycle failed, continuing: %s", WORKER_ID, exc)
        finally:
            session.close()
        cycles += 1
        if run_once or (max_cycles is not None and cycles >= max_cycles):
            return
        if errored:
            if error_backoff:
                time.sleep(error_backoff)
        elif processed == 0:
            time.sleep(poll_interval)


if __name__ == "__main__":  # pragma: no cover - operational entrypoint
    logging.basicConfig(level=logging.INFO)
    run_worker()
