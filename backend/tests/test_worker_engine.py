"""Comprehensive automated tests for Worker Engine, Retries, Timeouts, and Abandoned Recovery."""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.database import Base
from app.models.enums import AttemptStatus, JobStatus
from app.models.job import Job
from app.queue.base import QueueMessage
from app.queue.table_queue import TableQueueClient
from app.services.job_repository import JobRepository
from app.services.outbox_dispatcher import OutboxDispatcher
from app.workers.engine import WorkerEngine
from app.workers.recovery import AbandonedJobRecoveryService

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def worker_test_env():
    """Provides isolated database engine, queue client, and services."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    queue = TableQueueClient(session_factory=session_factory)
    worker = WorkerEngine(
        worker_id="test-worker-1",
        concurrency=2,
        queue_client=queue,
        queue_name="test_jobs_queue",
        session_factory=session_factory
    )
    dispatcher = OutboxDispatcher(
        session_factory=session_factory,
        queue_client=queue,
        queue_name="test_jobs_queue"
    )
    recovery = AbandonedJobRecoveryService(session_factory=session_factory)
    return engine, session_factory, queue, worker, dispatcher, recovery


@pytest.mark.asyncio
async def test_worker_successful_execution(worker_test_env):
    """Verify that a worker processes a valid job to completion and persists attempts and results."""
    engine, session_factory, queue, worker, dispatcher, _ = worker_test_env
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    owner_id = uuid.uuid4()
    async with session_factory() as session:
        job, _ = await JobRepository.create_job_with_outbox(
            session=session,
            owner_id=owner_id,
            job_type="report_generation",
            payload={"format": "pdf", "rows": 500}
        )
        await session.commit()
        job_id = job.id

    # 1. Dispatch from outbox to queue
    await dispatcher.sweep_and_dispatch()

    # 2. Worker reads and processes message
    messages = await queue.read("test_jobs_queue", limit=1)
    assert len(messages) == 1

    processed = await worker.process_message(messages[0])
    assert processed is True

    # 3. Verify final job state
    async with session_factory() as session:
        completed_job = await JobRepository.get_by_id(session, job_id, load_relations=True)
        assert completed_job.status == JobStatus.SUCCEEDED.value
        assert completed_job.result["format"] == "pdf"
        assert completed_job.result["rows_processed"] == 500
        assert completed_job.completed_at is not None

        # Verify attempt record
        assert len(completed_job.attempts) == 1
        att = completed_job.attempts[0]
        assert att.status == AttemptStatus.SUCCEEDED.value
        assert att.attempt_number == 1
        assert att.duration_ms is not None

    # 4. Verify message was acked and removed from queue
    depth = await queue.get_depth("test_jobs_queue")
    assert depth == 0

    await engine.dispose()


@pytest.mark.asyncio
async def test_transient_failure_and_backoff_retry(worker_test_env):
    """Verify that transient failures trigger backoff retry and eventually succeed."""
    engine, session_factory, queue, worker, dispatcher, recovery = worker_test_env
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    owner_id = uuid.uuid4()
    async with session_factory() as session:
        job, _ = await JobRepository.create_job_with_outbox(
            session=session,
            owner_id=owner_id,
            job_type="chaos_flaky_task",
            payload={"fail_until_attempt": 1},  # Fails on attempt 1, succeeds on attempt 2
            max_attempts=3
        )
        await session.commit()
        job_id = job.id

    await dispatcher.sweep_and_dispatch()

    # Attempt 1: Worker executes and encounters transient error
    messages = await queue.read("test_jobs_queue", limit=1)
    assert len(messages) == 1
    processed = await worker.process_message(messages[0])
    assert processed is False

    # Verify job moved to retry_wait
    async with session_factory() as session:
        retrying_job = await JobRepository.get_by_id(session, job_id, load_relations=True)
        assert retrying_job.status == JobStatus.RETRY_WAIT.value
        assert retrying_job.attempt_count == 1
        assert retrying_job.next_run_at is not None
        assert len(retrying_job.attempts) == 1
        assert retrying_job.attempts[0].status == AttemptStatus.FAILED.value

        # Manually fast-forward next_run_at to past so recovery service picks it up
        retrying_job.next_run_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await session.commit()

    # Recovery service re-enqueues the job
    requeued = await recovery.poll_retry_wait_jobs()
    assert requeued == 1

    # Dispatch to queue
    await dispatcher.sweep_and_dispatch()

    # Attempt 2: Worker executes and succeeds
    retry_messages = await queue.read("test_jobs_queue", limit=1)
    assert len(retry_messages) == 1
    success_processed = await worker.process_message(retry_messages[0])
    assert success_processed is True

    # Final state: succeeded after 2 attempts
    async with session_factory() as session:
        final_job = await JobRepository.get_by_id(session, job_id, load_relations=True)
        assert final_job.status == JobStatus.SUCCEEDED.value
        assert final_job.attempt_count == 2
        assert len(final_job.attempts) == 2

    await engine.dispose()


@pytest.mark.asyncio
async def test_permanent_failure_dead_letter_routing(worker_test_env):
    """Verify that permanent errors immediately route to dead-letter without wasteful retries."""
    engine, session_factory, queue, worker, dispatcher, _ = worker_test_env
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    owner_id = uuid.uuid4()
    async with session_factory() as session:
        job, _ = await JobRepository.create_job_with_outbox(
            session=session,
            owner_id=owner_id,
            job_type="chaos_poison_pill",
            payload={"error_message": "Unrecoverable malformed syntax"},
            max_attempts=5
        )
        await session.commit()
        job_id = job.id

    await dispatcher.sweep_and_dispatch()
    messages = await queue.read("test_jobs_queue", limit=1)

    # Process poison pill
    await worker.process_message(messages[0])

    # Should be in DEAD_LETTER immediately on attempt 1
    async with session_factory() as session:
        dead_letter_job = await JobRepository.get_by_id(session, job_id, load_relations=True)
        assert dead_letter_job.status == JobStatus.DEAD_LETTER.value
        assert dead_letter_job.attempt_count == 1
        assert "PermanentExecutionError" in dead_letter_job.last_error["error_type"]

    await engine.dispose()


@pytest.mark.asyncio
async def test_execution_timeout_enforcement(worker_test_env):
    """Verify that jobs exceeding their timeout deadline are terminated and failed."""
    engine, session_factory, queue, worker, dispatcher, _ = worker_test_env
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    owner_id = uuid.uuid4()
    async with session_factory() as session:
        # Job with 1-second timeout executing a 5-second task
        job, _ = await JobRepository.create_job_with_outbox(
            session=session,
            owner_id=owner_id,
            job_type="chaos_slow_worker",
            payload={"sleep_seconds": 5.0},
            timeout_seconds=1,
            max_attempts=1
        )
        await session.commit()
        job_id = job.id

    await dispatcher.sweep_and_dispatch()
    messages = await queue.read("test_jobs_queue", limit=1)

    # Worker executes and hits 1s timeout
    await worker.process_message(messages[0])

    async with session_factory() as session:
        timed_out_job = await JobRepository.get_by_id(session, job_id)
        assert timed_out_job.status == JobStatus.DEAD_LETTER.value
        assert timed_out_job.last_error["error_type"] == "TimeoutError"

    await engine.dispose()


@pytest.mark.asyncio
async def test_abandoned_job_lease_recovery(worker_test_env):
    """Verify that crashed workers with expired leases are detected and safely recovered."""
    engine, session_factory, queue, _, dispatcher, recovery = worker_test_env
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    owner_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(minutes=10)

    async with session_factory() as session:
        # Simulate a job left 'running' by a crashed worker whose lease expired
        crashed_job = Job(
            id=uuid.uuid4(),
            owner_id=owner_id,
            job_type="report_generation",
            payload={"format": "csv"},
            status=JobStatus.RUNNING.value,
            attempt_count=1,
            max_attempts=3,
            timeout_seconds=60,
            lease_owner="crashed-worker-pid-999",
            lease_token=uuid.uuid4(),
            lease_expires_at=expired_time,
            version=2,
            created_at=now - timedelta(minutes=15)
        )
        session.add(crashed_job)
        await session.commit()
        crashed_id = crashed_job.id

    # Run abandoned recovery scanner
    recovered = await recovery.recover_abandoned_jobs()
    assert recovered == 1

    # Verify job was reset to QUEUED and outbox was created
    async with session_factory() as session:
        recovered_job = await JobRepository.get_by_id(session, crashed_id, load_relations=True)
        assert recovered_job.status == JobStatus.QUEUED.value
        assert recovered_job.lease_owner is None
        assert recovered_job.version == 3

        events = recovered_job.events
        assert any(e.event_type == "JOB_ABANDONED_RECOVERED" for e in events)

    # Dispatch outbox entry
    dispatched = await dispatcher.sweep_and_dispatch()
    assert dispatched == 1

    await engine.dispose()
