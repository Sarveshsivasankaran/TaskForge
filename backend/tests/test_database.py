"""Automated tests for database models, repositories, and state machine constraints."""

import uuid
from datetime import datetime, timezone, timedelta
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.database import Base
from app.models.enums import (
    JobStatus,
    AttemptStatus,
    InvalidStateTransitionError,
    validate_job_state_transition,
)
from app.models.job import Job
from app.models.attempt import JobAttempt
from app.models.event import JobEvent
from app.models.outbox import JobOutbox
from app.services.job_repository import JobRepository


# Use an in-memory SQLite database with aiosqlite for deterministic test isolation
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_session():
    """Provides a fresh isolated database schema and session for each test."""
    test_engine = create_async_engine(
        TEST_DB_URL,
        echo=False,
        connect_args={"check_same_thread": False}
    )
    async_session = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_create_job_with_atomic_outbox(test_session: AsyncSession):
    """Verify that creating a job atomically produces an outbox and audit event record."""
    owner_id = uuid.uuid4()
    job, created = await JobRepository.create_job_with_outbox(
        session=test_session,
        owner_id=owner_id,
        job_type="report_generation",
        payload={"format": "pdf", "rows": 1000},
        idempotency_key="idemp-1"
    )
    await test_session.commit()

    assert created is True
    assert job.status == JobStatus.QUEUED.value
    assert job.version == 1
    assert job.attempt_count == 0
    assert job.job_type == "report_generation"

    # Verify outbox entry
    outbox_entries = (await JobRepository.get_by_id(test_session, job.id, load_relations=True)).outbox_entries
    assert len(outbox_entries) == 1
    assert outbox_entries[0].job_id == job.id
    assert outbox_entries[0].dispatched is False

    # Verify audit event
    events = (await JobRepository.get_by_id(test_session, job.id, load_relations=True)).events
    assert len(events) == 1
    assert events[0].event_type == "JOB_CREATED"


@pytest.mark.asyncio
async def test_owner_scoped_idempotency(test_session: AsyncSession):
    """Verify that idempotency keys prevent duplicates per owner but allow independent tenants."""
    owner_a = uuid.uuid4()
    owner_b = uuid.uuid4()
    idemp_key = "unique-transaction-123"

    # Owner A first submission
    job_a1, created_a1 = await JobRepository.create_job_with_outbox(
        session=test_session,
        owner_id=owner_a,
        job_type="email_send",
        payload={"to": "user@example.com"},
        idempotency_key=idemp_key
    )
    await test_session.commit()
    assert created_a1 is True

    # Owner A duplicate submission with same key
    job_a2, created_a2 = await JobRepository.create_job_with_outbox(
        session=test_session,
        owner_id=owner_a,
        job_type="email_send",
        payload={"to": "user@example.com"},
        idempotency_key=idemp_key
    )
    assert created_a2 is False
    assert job_a2.id == job_a1.id  # Returns original job

    # Owner B submission with identical key should be permitted (scoped to tenant)
    job_b, created_b = await JobRepository.create_job_with_outbox(
        session=test_session,
        owner_id=owner_b,
        job_type="email_send",
        payload={"to": "other@example.com"},
        idempotency_key=idemp_key
    )
    await test_session.commit()
    assert created_b is True
    assert job_b.id != job_a1.id


@pytest.mark.asyncio
async def test_state_transition_validation():
    """Verify state transition rules enforce valid paths and reject illegal jumps."""
    # Valid normal transitions
    validate_job_state_transition(JobStatus.QUEUED, JobStatus.RUNNING)
    validate_job_state_transition(JobStatus.RUNNING, JobStatus.SUCCEEDED)
    validate_job_state_transition(JobStatus.RUNNING, JobStatus.RETRY_WAIT)
    validate_job_state_transition(JobStatus.RETRY_WAIT, JobStatus.QUEUED)
    validate_job_state_transition(JobStatus.RUNNING, JobStatus.DEAD_LETTER)
    validate_job_state_transition(JobStatus.QUEUED, JobStatus.CANCELLED)

    # Invalid: Terminal succeeded state cannot transition
    with pytest.raises(InvalidStateTransitionError):
        validate_job_state_transition(JobStatus.SUCCEEDED, JobStatus.RUNNING)

    with pytest.raises(InvalidStateTransitionError):
        validate_job_state_transition(JobStatus.SUCCEEDED, JobStatus.QUEUED)

    # Invalid: Cannot jump from queued directly to succeeded
    with pytest.raises(InvalidStateTransitionError):
        validate_job_state_transition(JobStatus.QUEUED, JobStatus.SUCCEEDED)

    # Invalid: Failed cannot transition directly without manual retry flag
    with pytest.raises(InvalidStateTransitionError):
        validate_job_state_transition(JobStatus.FAILED, JobStatus.QUEUED, is_manual_retry=False)

    # Valid: Manual retry allows failed -> queued
    validate_job_state_transition(JobStatus.FAILED, JobStatus.QUEUED, is_manual_retry=True)


@pytest.mark.asyncio
async def test_lease_fencing_and_concurrency(test_session: AsyncSession):
    """Verify optimistic concurrency and lease token validation prevent double execution."""
    owner_id = uuid.uuid4()
    job, _ = await JobRepository.create_job_with_outbox(
        session=test_session,
        owner_id=owner_id,
        job_type="data_processing",
        payload={"batch_size": 500}
    )
    await test_session.commit()

    # Worker 1 acquires lease
    claim_result = await JobRepository.claim_job_lease(
        session=test_session,
        job_id=job.id,
        worker_id="worker-node-1",
        lease_duration_seconds=30
    )
    await test_session.commit()
    assert claim_result is not None
    claimed_job, lease_token = claim_result

    assert claimed_job.status == JobStatus.RUNNING.value
    assert claimed_job.version == 2
    assert claimed_job.attempt_count == 1
    assert claimed_job.lease_owner == "worker-node-1"

    # Worker 2 attempts to claim the same running job -> must fail
    second_claim = await JobRepository.claim_job_lease(
        session=test_session,
        job_id=job.id,
        worker_id="worker-node-2",
        lease_duration_seconds=30
    )
    assert second_claim is None

    # Stale attempt completion with wrong lease token -> must fail
    fake_token = uuid.uuid4()
    bad_complete = await JobRepository.complete_job(
        session=test_session,
        job_id=job.id,
        lease_token=fake_token,
        result_data={"records_processed": 500}
    )
    assert bad_complete is False

    # Authoritative worker completion with valid lease token -> must succeed
    good_complete = await JobRepository.complete_job(
        session=test_session,
        job_id=job.id,
        lease_token=lease_token,
        result_data={"records_processed": 500}
    )
    await test_session.commit()
    assert good_complete is True

    # Check finalized state
    final_job = await JobRepository.get_by_id(test_session, job.id)
    assert final_job.status == JobStatus.SUCCEEDED.value
    assert final_job.lease_owner is None
    assert final_job.version == 3


@pytest.mark.asyncio
async def test_expired_lease_detection(test_session: AsyncSession):
    """Verify that abandoned jobs with expired leases are detected by the recovery scanner."""
    owner_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(minutes=5)

    job = Job(
        id=uuid.uuid4(),
        owner_id=owner_id,
        job_type="compute_task",
        payload={},
        status=JobStatus.RUNNING.value,
        attempt_count=1,
        max_attempts=3,
        timeout_seconds=60,
        lease_owner="crashed-worker",
        lease_token=uuid.uuid4(),
        lease_expires_at=expired_time,
        version=2,
        created_at=now - timedelta(minutes=10)
    )
    test_session.add(job)
    await test_session.commit()

    # Query expired leases
    expired_jobs = await JobRepository.find_expired_leases(test_session, as_of=now)
    assert len(expired_jobs) == 1
    assert expired_jobs[0].id == job.id
    assert expired_jobs[0].lease_owner == "crashed-worker"


@pytest.mark.asyncio
async def test_job_listing_and_ownership_filtering(test_session: AsyncSession):
    """Verify job listing correctly isolates tenant data and supports pagination."""
    owner_x = uuid.uuid4()
    owner_y = uuid.uuid4()

    # Create 3 jobs for owner X
    for i in range(3):
        await JobRepository.create_job_with_outbox(
            session=test_session,
            owner_id=owner_x,
            job_type="type_x",
            payload={"index": i}
        )

    # Create 2 jobs for owner Y
    for j in range(2):
        await JobRepository.create_job_with_outbox(
            session=test_session,
            owner_id=owner_y,
            job_type="type_y",
            payload={"index": j}
        )
    await test_session.commit()

    # Owner X listing
    jobs_x, total_x = await JobRepository.list_jobs(test_session, owner_id=owner_x)
    assert total_x == 3
    assert len(jobs_x) == 3
    assert all(j.owner_id == owner_x for j in jobs_x)

    # Owner Y listing
    jobs_y, total_y = await JobRepository.list_jobs(test_session, owner_id=owner_y)
    assert total_y == 2
    assert len(jobs_y) == 2
    assert all(j.owner_id == owner_y for j in jobs_y)

    # Pagination test
    paged_jobs, paged_total = await JobRepository.list_jobs(
        test_session,
        owner_id=owner_x,
        limit=2,
        offset=0
    )
    assert paged_total == 3
    assert len(paged_jobs) == 2
