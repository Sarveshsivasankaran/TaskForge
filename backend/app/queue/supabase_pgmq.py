"""Supabase PostgreSQL Queues (pgmq extension) client adapter."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Union
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.queue.base import BaseQueueClient, QueueMessage


class SupabasePGMQQueueClient(BaseQueueClient):
    """
    Queue client utilizing the Supabase / PostgreSQL `pgmq` extension.
    Executes native stored procedures for atomic message visibility and archiving.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] = AsyncSessionLocal):
        self.session_factory = session_factory

    async def initialize_queue(self, queue_name: str) -> None:
        """Ensures the pgmq extension and named queue exist."""
        async with self.session_factory() as session:
            try:
                await session.execute(text("CREATE EXTENSION IF NOT EXISTS pgmq CASCADE;"))
                await session.execute(text("SELECT pgmq.create(:queue_name);"), {"queue_name": queue_name})
                await session.commit()
                logger.info(f"Supabase pgmq queue '{queue_name}' initialized.")
            except Exception as e:
                await session.rollback()
                logger.warning(f"pgmq initialization notice (may already exist or unprivileged): {e}")

    async def send(
        self,
        queue_name: str,
        message: Dict[str, Any],
        delay_seconds: int = 0
    ) -> Union[str, int]:
        """Sends message to pgmq queue."""
        async with self.session_factory() as session:
            msg_json = json.dumps(message)
            stmt = text("SELECT pgmq.send(:queue_name, :msg_json::jsonb, :delay);")
            res = await session.execute(
                stmt,
                {"queue_name": queue_name, "msg_json": msg_json, "delay": delay_seconds}
            )
            msg_id = res.scalar_one()
            await session.commit()
            return msg_id

    async def read(
        self,
        queue_name: str,
        visibility_timeout_seconds: int = 60,
        limit: int = 1
    ) -> List[QueueMessage]:
        """Reads messages from pgmq with visibility timeout."""
        messages: List[QueueMessage] = []
        async with self.session_factory() as session:
            stmt = text("SELECT * FROM pgmq.read(:queue_name, :vt, :limit);")
            res = await session.execute(
                stmt,
                {"queue_name": queue_name, "vt": visibility_timeout_seconds, "limit": limit}
            )
            rows = res.mappings().all()
            for r in rows:
                payload = r["message"] if isinstance(r["message"], dict) else json.loads(r["message"])
                messages.append(
                    QueueMessage(
                        msg_id=r["msg_id"],
                        queue_name=queue_name,
                        payload=payload,
                        read_count=r.get("read_ct", 1),
                        enqueued_at=r.get("enqueued_at", datetime.now(timezone.utc)),
                        visible_at=r.get("vt")
                    )
                )
            await session.commit()
        return messages

    async def ack(self, queue_name: str, msg_id: Union[str, int]) -> bool:
        """Deletes/archives processed message from pgmq."""
        async with self.session_factory() as session:
            stmt = text("SELECT pgmq.archive(:queue_name, :msg_id);")
            res = await session.execute(stmt, {"queue_name": queue_name, "msg_id": int(msg_id)})
            success = bool(res.scalar_one())
            await session.commit()
            return success

    async def nack(
        self,
        queue_name: str,
        msg_id: Union[str, int],
        delay_seconds: int = 0
    ) -> bool:
        """Resets message visibility in pgmq."""
        async with self.session_factory() as session:
            stmt = text("SELECT pgmq.set_vt(:queue_name, :msg_id, :vt);")
            res = await session.execute(
                stmt,
                {"queue_name": queue_name, "msg_id": int(msg_id), "vt": delay_seconds}
            )
            await session.commit()
            return True

    async def get_depth(self, queue_name: str) -> int:
        """Returns message queue count in pgmq."""
        async with self.session_factory() as session:
            try:
                stmt = text("SELECT pgmq.metrics(:queue_name);")
                res = await session.execute(stmt, {"queue_name": queue_name})
                metrics = res.mappings().first()
                if metrics and "queue_length" in metrics:
                    return int(metrics["queue_length"])
            except Exception:
                pass
            return 0
