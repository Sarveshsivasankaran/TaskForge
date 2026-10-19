"""Durable table-backed queue adapter."""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Union
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import AsyncSessionLocal
from app.models.queue_message import PersistentQueueMessage
from app.queue.base import BaseQueueClient, QueueMessage


class TableQueueClient(BaseQueueClient):
    """
    Durable queue implementation backed by database tables.
    Provides identical at-least-once visibility timeout semantics to pgmq,
    functioning seamlessly offline, in tests, and on PostgreSQL/SQLite.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] = AsyncSessionLocal):
        self.session_factory = session_factory

    async def initialize_queue(self, queue_name: str) -> None:
        """No DDL required; table is managed by database migrations."""
        pass

    async def send(
        self,
        queue_name: str,
        message: Dict[str, Any],
        delay_seconds: int = 0
    ) -> str:
        """Enqueues a message with visibility timestamp."""
        now = datetime.now(timezone.utc)
        visible_at = now + timedelta(seconds=delay_seconds)
        msg_id = uuid.uuid4()

        async with self.session_factory() as session:
            record = PersistentQueueMessage(
                id=msg_id,
                queue_name=queue_name,
                payload=message,
                read_count=0,
                visible_at=visible_at,
                enqueued_at=now
            )
            session.add(record)
            await session.commit()

        return str(msg_id)

    async def read(
        self,
        queue_name: str,
        visibility_timeout_seconds: int = 60,
        limit: int = 1
    ) -> List[QueueMessage]:
        """
        Fetches up to `limit` visible messages and locks them for `visibility_timeout_seconds`.
        """
        now = datetime.now(timezone.utc)
        new_visible_at = now + timedelta(seconds=visibility_timeout_seconds)
        messages: List[QueueMessage] = []

        async with self.session_factory() as session:
            # Select available visible messages
            query = (
                select(PersistentQueueMessage)
                .where(
                    and_(
                        PersistentQueueMessage.queue_name == queue_name,
                        PersistentQueueMessage.visible_at <= now
                    )
                )
                .order_by(PersistentQueueMessage.enqueued_at.asc())
                .limit(limit)
            )
            records = (await session.execute(query)).scalars().all()

            for rec in records:
                # Update lease / visibility timeout
                rec.visible_at = new_visible_at
                rec.read_count += 1
                messages.append(
                    QueueMessage(
                        msg_id=str(rec.id),
                        queue_name=rec.queue_name,
                        payload=rec.payload,
                        read_count=rec.read_count,
                        enqueued_at=rec.enqueued_at,
                        visible_at=new_visible_at
                    )
                )

            await session.commit()

        return messages

    async def ack(self, queue_name: str, msg_id: Union[str, int]) -> bool:
        """Removes the message from the queue upon successful completion."""
        try:
            target_uuid = uuid.UUID(str(msg_id))
        except ValueError:
            return False

        async with self.session_factory() as session:
            stmt = delete(PersistentQueueMessage).where(
                and_(
                    PersistentQueueMessage.id == target_uuid,
                    PersistentQueueMessage.queue_name == queue_name
                )
            )
            res = await session.execute(stmt)
            await session.commit()
            return res.rowcount > 0

    async def nack(
        self,
        queue_name: str,
        msg_id: Union[str, int],
        delay_seconds: int = 0
    ) -> bool:
        """Releases message back into visibility immediately or after delay."""
        try:
            target_uuid = uuid.UUID(str(msg_id))
        except ValueError:
            return False

        now = datetime.now(timezone.utc)
        visible_at = now + timedelta(seconds=delay_seconds)

        async with self.session_factory() as session:
            stmt = (
                update(PersistentQueueMessage)
                .where(
                    and_(
                        PersistentQueueMessage.id == target_uuid,
                        PersistentQueueMessage.queue_name == queue_name
                    )
                )
                .values(visible_at=visible_at)
            )
            res = await session.execute(stmt)
            await session.commit()
            return res.rowcount > 0

    async def get_depth(self, queue_name: str) -> int:
        """Counts pending visible messages in the queue."""
        now = datetime.now(timezone.utc)
        async with self.session_factory() as session:
            query = select(func.count(PersistentQueueMessage.id)).where(
                and_(
                    PersistentQueueMessage.queue_name == queue_name,
                    PersistentQueueMessage.visible_at <= now
                )
            )
            return (await session.execute(query)).scalar_one()
