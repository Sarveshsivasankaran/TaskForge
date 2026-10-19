"""Transactional Outbox Dispatcher service."""

import asyncio
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.models.outbox import JobOutbox
from app.queue.base import BaseQueueClient
from app.queue.factory import get_queue_client


class OutboxDispatcher:
    """
    Tails the `job_outbox` table and guarantees reliable dispatch of new jobs
    to the message broker. Solves the dual-write problem by decoupling database commit from queue publish.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] = AsyncSessionLocal,
        queue_client: Optional[BaseQueueClient] = None,
        queue_name: str = settings.queue_name
    ):
        self.session_factory = session_factory
        self.queue_client = queue_client or get_queue_client()
        self.queue_name = queue_name
        self._running = False

    async def sweep_and_dispatch(self, batch_size: int = 50) -> int:
        """
        Polls pending outbox records, publishes them to the queue broker,
        and marks them as dispatched atomically. Returns the count of dispatched jobs.
        """
        dispatched_count = 0
        async with self.session_factory() as session:
            # Query pending outbox entries
            query = (
                select(JobOutbox)
                .where(JobOutbox.dispatched == False)  # noqa: E712
                .order_by(JobOutbox.created_at.asc())
                .limit(batch_size)
            )
            entries = (await session.execute(query)).scalars().all()
            if not entries:
                return 0

            for entry in entries:
                try:
                    # Publish message to queue broker
                    await self.queue_client.send(
                        queue_name=self.queue_name,
                        message=entry.payload
                    )
                    now = datetime.now(timezone.utc)
                    entry.dispatched = True
                    entry.dispatched_at = now
                    dispatched_count += 1
                except Exception as exc:
                    entry.retry_count += 1
                    logger.error(
                        f"Outbox dispatch error for job {entry.job_id} (attempt {entry.retry_count}): {exc}"
                    )

            await session.commit()

        if dispatched_count > 0:
            logger.info(f"Outbox dispatcher successfully published {dispatched_count} job messages.")

        return dispatched_count

    async def run_loop(self, poll_interval_seconds: float = 1.0) -> None:
        """Runs the continuous outbox polling loop until stopped."""
        self._running = True
        logger.info("Outbox dispatcher loop started.")
        while self._running:
            try:
                count = await self.sweep_and_dispatch()
                if count == 0:
                    await asyncio.sleep(poll_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in outbox loop: {e}", exc_info=True)
                await asyncio.sleep(poll_interval_seconds)
        logger.info("Outbox dispatcher loop stopped.")

    def stop(self) -> None:
        """Signals the dispatcher loop to gracefully stop."""
        self._running = False
