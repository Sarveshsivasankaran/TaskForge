"""Queue message persistence model for table-backed queue."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, JSON, Uuid, Index, text
from app.core.database import Base


class PersistentQueueMessage(Base):
    """
    Durable table-backed queue message entity.
    Provides identical semantics to Supabase pgmq (visibility timeouts, read counts, ack/nack).
    """
    __tablename__ = "queue_messages"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    queue_name = Column(String(100), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    read_count = Column(Integer, nullable=False, default=0)
    visible_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
        index=True
    )
    enqueued_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP")
    )

    __table_args__ = (
        Index("ix_queue_messages_poll", "queue_name", "visible_at"),
    )
