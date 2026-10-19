"""Abandoned Job Recovery and Retry Scheduling Service."""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.models.enums import JobStatus
from app.models.event import JobEvent
from app.models.job import Job
from app.models.outbox import JobOutbox
from app.services.job_repository import JobRepository


class AbandonedJobRecoveryService:
    """
    Identifies jobs abandoned due to crashed workers or network partitions,
    safely recovering eligible jobs or moving retry-exhausted jobs to dead_letter.
    Also re-enqueues retry_wait jobs whose backoff time has arrived.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] = AsyncSessionLocal
    ):
        self.session_factory = session_factory
        self._running = False

    async def recover_abandoned_jobs(self) -> int:
        """
        Scans for running jobs whose lease has expired.
        Guarantees stale crashed workers cannot overwrite newer state.
        """
        recovered_count = 0
        now = datetime.now(timezone.utc)

        async with self.session_factory() as session:
            expired_jobs = await JobRepository.find_expired_leases(session, as_of=now)
            if not expired_jobs:
                return 0

            for job in expired_jobs:
                logger.warning(
                    f"Detected abandoned job {job.id} (leased by '{job.lease_owner}' until {job.lease_expires_at})"
                )

                if job.attempt_count < job.max_attempts:
                    # Reschedule for recovery
                    job.status = JobStatus.QUEUED.value
                    job.lease_owner = None
                    job.lease_token = None
                    job.lease_expires_at = None
                    job.version += 1
                    job.updated_at = now

                    # Re-dispatch outbox entry
                    outbox = JobOutbox(
                        id=uuid.uuid4(),
                        job_id=job.id,
                        payload={"job_id": str(job.id), "job_type": job.job_type, "owner_id": str(job.owner_id)},
                        dispatched=False,
                        created_at=now
                    )
                    session.add(outbox)

                    event = JobEvent(
                        id=uuid.uuid4(),
                        job_id=job.id,
                        event_type="JOB_ABANDONED_RECOVERED",
                        event_data={"previous_worker": job.lease_owner, "attempt": job.attempt_count},
                        created_at=now
                    )
                    session.add(event)
                    recovered_count += 1
                else:
                    # Exhausted attempts -> Dead Letter
                    job.status = JobStatus.DEAD_LETTER.value
                    job.last_error = {
                        "error_type": "AbandonedWorkerError",
                        "message": f"Worker '{job.lease_owner}' lease expired; max attempts ({job.max_attempts}) reached.",
                        "timestamp": now.isoformat()
                    }
                    job.lease_owner = None
                    job.lease_token = None
                    job.lease_expires_at = None
                    job.version += 1
                    job.updated_at = now

                    event = JobEvent(
                        id=uuid.uuid4(),
                        job_id=job.id,
                        event_type="JOB_DEAD_LETTER_ABANDONED",
                        event_data={"reason": "Lease expired with max attempts exhausted"},
                        created_at=now
                    )
                    session.add(event)
                    recovered_count += 1

            await session.commit()

        if recovered_count > 0:
            logger.info(f"Abandoned job recovery processed {recovered_count} stalled jobs.")

        return recovered_count

    async def poll_retry_wait_jobs(self) -> int:
        """
        Polls jobs in retry_wait status whose next_run_at backoff deadline has passed,
        transitioning them back to queued and generating an outbox dispatch entry.
        """
        requeued_count = 0
        now = datetime.now(timezone.utc)

        async with self.session_factory() as session:
            query = (
                select(Job)
                .where(
                    and_(
                        Job.status == JobStatus.RETRY_WAIT.value,
                        Job.next_run_at <= now
                    )
                )
                .limit(50)
            )
            jobs = (await session.execute(query)).scalars().all()
            if not jobs:
                return 0

            for job in jobs:
                job.status = JobStatus.QUEUED.value
                job.version += 1
                job.updated_at = now

                outbox = JobOutbox(
                    id=uuid.uuid4(),
                    job_id=job.id,
                    payload={"job_id": str(job.id), "job_type": job.job_type, "owner_id": str(job.owner_id)},
                    dispatched=False,
                    created_at=now
                )
                session.add(outbox)

                event = JobEvent(
                    id=uuid.uuid4(),
                    job_id=job.id,
                    event_type="JOB_RETRY_ENQUEUED",
                    event_data={"attempt": job.attempt_count + 1},
                    created_at=now
                )
                session.add(event)
                requeued_count += 1

            await session.commit()

        if requeued_count > 0:
            logger.info(f"Re-enqueued {requeued_count} retry_wait jobs whose backoff timer arrived.")

        return requeued_count

    async def run_recovery_loop(self, scan_interval_seconds: float = 5.0) -> None:
        """Continuous background loop for lease recovery and backoff scheduling."""
        self._running = True
        logger.info("Abandoned job recovery service started.")
        while self._running:
            try:
                await self.recover_abandoned_jobs()
                await self.poll_retry_wait_jobs()
                await asyncio.sleep(scan_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in recovery loop: {e}", exc_info=True)
                await asyncio.sleep(scan_interval_seconds)
        logger.info("Abandoned job recovery service stopped.")

    def stop(self) -> None:
        self._running = False
