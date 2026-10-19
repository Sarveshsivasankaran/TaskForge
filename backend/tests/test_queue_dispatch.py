"""Automated tests for Queue adapters and Transactional Outbox dispatch."""

import uuid
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.database import Base
from app.models.outbox import JobOutbox
from app.queue.table_queue import TableQueueClient
from app.services.job_repository import JobRepository
from app.services.outbox_dispatcher import OutboxDispatcher

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def queue_session_factory():
    """Provides an isolated in-memory database engine and session factory."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    return engine, session_factory


@pytest.mark.asyncio
async def test_table_queue_lifecycle(queue_session_factory):
    """Test send, visibility timeout, read count, and acknowledgement in TableQueueClient."""
    engine, session_factory = queue_session_factory
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    queue = TableQueueClient(session_factory=session_factory)
    queue_name = "test_queue"

    # 1. Verify initially empty
    depth = await queue.get_depth(queue_name)
    assert depth == 0

    # 2. Send message
    job_payload = {"job_id": str(uuid.uuid4()), "job_type": "report_generation"}
    msg_id = await queue.send(queue_name, job_payload)
    assert msg_id is not None

    depth = await queue.get_depth(queue_name)
    assert depth == 1

    # 3. Read message with 60s visibility timeout
    messages = await queue.read(queue_name, visibility_timeout_seconds=60, limit=1)
    assert len(messages) == 1
    msg = messages[0]
    assert msg.msg_id == msg_id
    assert msg.payload["job_type"] == "report_generation"
    assert msg.read_count == 1

    # 4. Immediate second read should find 0 messages due to visibility timeout
    second_read = await queue.read(queue_name, visibility_timeout_seconds=60, limit=1)
    assert len(second_read) == 0

    # 5. Acknowledge (delete) message
    acked = await queue.ack(queue_name, msg.msg_id)
    assert acked is True

    # 6. Verify queue is now empty
    final_depth = await queue.get_depth(queue_name)
    assert final_depth == 0

    await engine.dispose()


@pytest.mark.asyncio
async def test_table_queue_nack_requeue(queue_session_factory):
    """Test that nack releases the message back into visibility."""
    engine, session_factory = queue_session_factory
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    queue = TableQueueClient(session_factory=session_factory)
    queue_name = "retry_queue"

    msg_id = await queue.send(queue_name, {"attempt": 1})
    messages = await queue.read(queue_name, visibility_timeout_seconds=60, limit=1)
    assert len(messages) == 1

    # Negative acknowledge without delay
    nacked = await queue.nack(queue_name, msg_id, delay_seconds=0)
    assert nacked is True

    # Should be immediately readable again
    retry_messages = await queue.read(queue_name, visibility_timeout_seconds=60, limit=1)
    assert len(retry_messages) == 1
    assert retry_messages[0].read_count == 2

    await engine.dispose()


@pytest.mark.asyncio
async def test_outbox_dispatcher_sweep(queue_session_factory):
    """Verify that OutboxDispatcher dispatches pending outbox records to the queue broker."""
    engine, session_factory = queue_session_factory
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    queue = TableQueueClient(session_factory=session_factory)
    dispatcher = OutboxDispatcher(
        session_factory=session_factory,
        queue_client=queue,
        queue_name="dispatch_test_queue"
    )

    # Insert 3 jobs using repository (creating 3 pending outbox entries)
    owner_id = uuid.uuid4()
    async with session_factory() as session:
        for i in range(3):
            await JobRepository.create_job_with_outbox(
                session=session,
                owner_id=owner_id,
                job_type="dataset_processing",
                payload={"index": i}
            )
        await session.commit()

    # 1. Sweep and dispatch
    dispatched = await dispatcher.sweep_and_dispatch()
    assert dispatched == 3

    # 2. Verify messages are in queue
    depth = await queue.get_depth("dispatch_test_queue")
    assert depth == 3

    # 3. Second sweep should find 0 pending records
    second_sweep = await dispatcher.sweep_and_dispatch()
    assert second_sweep == 0

    await engine.dispose()
