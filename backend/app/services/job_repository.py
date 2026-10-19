"""Job repository for transactional persistence, state updates, and optimistic locking."""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import (
    JobStatus,
    AttemptStatus,
    validate_job_state_transition,
    InvalidStateTransitionError
)
from app.models.job import Job
from app.models.attempt import JobAttempt
from app.models.event import JobEvent
from app.models.outbox import JobOutbox


class JobRepository:
    """Async repository providing authoritative operations on jobs and related tables."""

    @staticmethod
    async def get_by_id(
        session: AsyncSession,
        job_id: uuid.UUID,
        owner_id: Optional[uuid.UUID] = None,
        load_relations: bool = False
    ) -> Optional[Job]:
        """Fetches a job by ID, optionally enforcing ownership and loading attempts."""
        query = select(Job).where(Job.id == job_id)
        if owner_id is not None:
            query = query.where(Job.owner_id == owner_id)
        if load_relations:
            query = query.options(
                selectinload(Job.attempts),
                selectinload(Job.events),
                selectinload(Job.outbox_entries)
            )

        result = await session.execute(query)
        return result.scalars().first()

    @staticmethod
    async def get_by_idempotency_key(
        session: AsyncSession,
        owner_id: uuid.UUID,
        idempotency_key: str
    ) -> Optional[Job]:
        """Finds existing job by owner-scoped idempotency key."""
        query = select(Job).where(
            and_(Job.owner_id == owner_id, Job.idempotency_key == idempotency_key)
        )
        result = await session.execute(query)
        return result.scalars().first()

    @staticmethod
    async def create_job_with_outbox(
        session: AsyncSession,
        owner_id: uuid.UUID,
        job_type: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        max_attempts: int = 5,
        timeout_seconds: int = 300,
        next_run_at: Optional[datetime] = None
    ) -> Tuple[Job, bool]:
        """
        Atomically creates a Job and its Transactional Outbox record within the current transaction.
        If an idempotency key matches an existing job for this owner, returns (existing_job, False).
        Otherwise creates and returns (new_job, True).
        """
        if idempotency_key:
            existing = await JobRepository.get_by_idempotency_key(session, owner_id, idempotency_key)
            if existing:
                return existing, False

        job_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        scheduled_run = next_run_at or now

        job = Job(
            id=job_id,
            owner_id=owner_id,
            job_type=job_type,
            payload=payload,
            status=JobStatus.QUEUED.value,
            attempt_count=0,
            max_attempts=max_attempts,
            timeout_seconds=timeout_seconds,
            idempotency_key=idempotency_key,
            created_at=now,
            updated_at=now,
            next_run_at=scheduled_run,
            version=1
        )
        session.add(job)

        # Atomic Outbox record
        outbox = JobOutbox(
            id=uuid.uuid4(),
            job_id=job_id,
            payload={"job_id": str(job_id), "job_type": job_type, "owner_id": str(owner_id)},
            dispatched=False,
            created_at=now
        )
        session.add(outbox)

        # Audit Event
        event = JobEvent(
            id=uuid.uuid4(),
            job_id=job_id,
            event_type="JOB_CREATED",
            event_data={"job_type": job_type, "owner_id": str(owner_id), "scheduled_for": scheduled_run.isoformat()},
            created_at=now
        )
        session.add(event)

        await session.flush()
        return job, True

    @staticmethod
    async def list_jobs(
        session: AsyncSession,
        owner_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Job], int]:
        """Lists jobs with filtering, pagination, and total count."""
        conditions = []
        if owner_id is not None:
            conditions.append(Job.owner_id == owner_id)
        if status:
            conditions.append(Job.status == status)
        if job_type:
            conditions.append(Job.job_type == job_type)

        where_clause = and_(*conditions) if conditions else True

        # Total count query
        count_query = select(func.count(Job.id)).where(where_clause)
        total_count = (await session.execute(count_query)).scalar_one()

        # Paginated items query
        items_query = (
            select(Job)
            .where(where_clause)
            .order_by(Job.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = (await session.execute(items_query)).scalars().all()

        return list(items), total_count

    @staticmethod
    async def claim_job_lease(
        session: AsyncSession,
        job_id: uuid.UUID,
        worker_id: str,
        lease_duration_seconds: int = 60
    ) -> Optional[Tuple[Job, uuid.UUID]]:
        """
        Attempts to acquire a lease on a job using optimistic concurrency.
        Guarantees only one worker can successfully claim the execution lease.
        """
        job = await JobRepository.get_by_id(session, job_id)
        if not job:
            return None

        # Validate transition from current to running
        validate_job_state_transition(job.status, JobStatus.RUNNING)

        now = datetime.now(timezone.utc)
        lease_expires = now + timedelta(seconds=lease_duration_seconds)
        lease_token = uuid.uuid4()
        expected_version = job.version

        # Conditional update to fence out concurrent claims
        stmt = (
            update(Job)
            .where(
                and_(
                    Job.id == job_id,
                    Job.version == expected_version,
                    Job.status.in_([JobStatus.QUEUED.value, JobStatus.RETRY_WAIT.value])
                )
            )
            .values(
                status=JobStatus.RUNNING.value,
                lease_owner=worker_id,
                lease_token=lease_token,
                lease_expires_at=lease_expires,
                started_at=now,
                attempt_count=job.attempt_count + 1,
                version=expected_version + 1,
                updated_at=now
            )
        )
        res = await session.execute(stmt)
        if res.rowcount == 0:
            # Another worker updated or claimed the job in the meantime
            return None

        # Audit event
        event = JobEvent(
            id=uuid.uuid4(),
            job_id=job_id,
            event_type="JOB_CLAIMED",
            event_data={
                "worker_id": worker_id,
                "attempt_number": job.attempt_count + 1,
                "lease_token": str(lease_token),
                "lease_expires_at": lease_expires.isoformat()
            },
            created_at=now
        )
        session.add(event)
        await session.flush()

        # Reload updated job
        await session.refresh(job)
        return job, lease_token

    @staticmethod
    async def record_attempt(
        session: AsyncSession,
        job_id: uuid.UUID,
        attempt_number: int,
        worker_id: str,
        lease_token: uuid.UUID,
        status: AttemptStatus,
        started_at: datetime,
        finished_at: Optional[datetime] = None,
        duration_ms: Optional[int] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None
    ) -> JobAttempt:
        """Records an execution attempt for a job."""
        attempt = JobAttempt(
            id=uuid.uuid4(),
            job_id=job_id,
            attempt_number=attempt_number,
            worker_id=worker_id,
            status=status.value,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            error_type=error_type,
            error_message=error_message,
            result=result,
            lease_token=lease_token
        )
        session.add(attempt)
        await session.flush()
        return attempt

    @staticmethod
    async def update_attempt(
        session: AsyncSession,
        attempt_id: uuid.UUID,
        status: AttemptStatus,
        finished_at: datetime,
        duration_ms: int,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Updates the status and outcome of an existing execution attempt."""
        stmt = (
            update(JobAttempt)
            .where(JobAttempt.id == attempt_id)
            .values(
                status=status.value,
                finished_at=finished_at,
                duration_ms=duration_ms,
                error_type=error_type,
                error_message=error_message,
                result=result
            )
        )
        res = await session.execute(stmt)
        return res.rowcount > 0

    @staticmethod
    async def complete_job(
        session: AsyncSession,
        job_id: uuid.UUID,
        lease_token: uuid.UUID,
        result_data: Dict[str, Any]
    ) -> bool:
        """
        Marks job as succeeded with optimistic lease token verification.
        Fails if lease_token does not match current authoritative owner.
        """
        job = await JobRepository.get_by_id(session, job_id)
        if not job or job.lease_token != lease_token:
            return False

        validate_job_state_transition(job.status, JobStatus.SUCCEEDED)

        now = datetime.now(timezone.utc)
        stmt = (
            update(Job)
            .where(
                and_(
                    Job.id == job_id,
                    Job.lease_token == lease_token,
                    Job.version == job.version
                )
            )
            .values(
                status=JobStatus.SUCCEEDED.value,
                result=result_data,
                completed_at=now,
                lease_owner=None,
                lease_token=None,
                lease_expires_at=None,
                version=job.version + 1,
                updated_at=now
            )
        )
        res = await session.execute(stmt)
        if res.rowcount == 0:
            return False

        event = JobEvent(
            id=uuid.uuid4(),
            job_id=job_id,
            event_type="JOB_SUCCEEDED",
            event_data={"result_keys": list(result_data.keys()) if isinstance(result_data, dict) else []},
            created_at=now
        )
        session.add(event)
        await session.flush()
        return True

    @staticmethod
    async def fail_job_attempt(
        session: AsyncSession,
        job_id: uuid.UUID,
        lease_token: uuid.UUID,
        error_info: Dict[str, Any],
        next_run_at: Optional[datetime] = None,
        is_dead_letter: bool = False
    ) -> bool:
        """
        Transitions job to retry_wait or dead_letter/failed on execution failure.
        """
        job = await JobRepository.get_by_id(session, job_id)
        if not job or job.lease_token != lease_token:
            return False

        target_status = (
            JobStatus.DEAD_LETTER if is_dead_letter else
            (JobStatus.RETRY_WAIT if next_run_at else JobStatus.FAILED)
        )
        validate_job_state_transition(job.status, target_status)

        now = datetime.now(timezone.utc)
        stmt = (
            update(Job)
            .where(
                and_(
                    Job.id == job_id,
                    Job.lease_token == lease_token,
                    Job.version == job.version
                )
            )
            .values(
                status=target_status.value,
                last_error=error_info,
                next_run_at=next_run_at,
                lease_owner=None,
                lease_token=None,
                lease_expires_at=None,
                version=job.version + 1,
                updated_at=now
            )
        )
        res = await session.execute(stmt)
        if res.rowcount == 0:
            return False

        event = JobEvent(
            id=uuid.uuid4(),
            job_id=job_id,
            event_type=f"JOB_{target_status.value.upper()}",
            event_data={
                "error": error_info,
                "next_run_at": next_run_at.isoformat() if next_run_at else None
            },
            created_at=now
        )
        session.add(event)
        await session.flush()
        return True

    @staticmethod
    async def find_expired_leases(
        session: AsyncSession,
        as_of: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Job]:
        """Finds running jobs whose lease has expired for abandoned worker recovery."""
        check_time = as_of or datetime.now(timezone.utc)
        query = (
            select(Job)
            .where(
                and_(
                    Job.status == JobStatus.RUNNING.value,
                    Job.lease_expires_at < check_time
                )
            )
            .order_by(Job.lease_expires_at.asc())
            .limit(limit)
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def manual_retry(
        session: AsyncSession,
        job_id: uuid.UUID,
        owner_id: Optional[uuid.UUID] = None
    ) -> Optional[Job]:
        """
        Manually retries a failed, dead_letter, or cancelled job.
        Creates an audit event and a new outbox entry for re-dispatch.
        """
        job = await JobRepository.get_by_id(session, job_id, owner_id)
        if not job:
            return None

        validate_job_state_transition(job.status, JobStatus.QUEUED, is_manual_retry=True)

        now = datetime.now(timezone.utc)
        job.status = JobStatus.QUEUED.value
        job.next_run_at = now
        job.lease_owner = None
        job.lease_token = None
        job.lease_expires_at = None
        job.version = job.version + 1
        job.updated_at = now

        # Add new outbox entry for re-dispatch
        outbox = JobOutbox(
            id=uuid.uuid4(),
            job_id=job.id,
            payload={"job_id": str(job.id), "job_type": job.job_type, "owner_id": str(job.owner_id)},
            dispatched=False,
            created_at=now
        )
        session.add(outbox)

        # Audit event
        event = JobEvent(
            id=uuid.uuid4(),
            job_id=job.id,
            event_type="JOB_MANUAL_RETRY_TRIGGERED",
            event_data={"triggered_at": now.isoformat()},
            created_at=now
        )
        session.add(event)
        await session.flush()
        return job
