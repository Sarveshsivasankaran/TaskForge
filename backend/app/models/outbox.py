"""Transactional Outbox ORM model."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy import (
    Column,
    Boolean,
    Integer,
    DateTime,
    JSON,
    Uuid,
    ForeignKey,
    Index,
    text
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class JobOutbox(Base):
    """
    Transactional outbox table for atomic job dispatch.
    Inserted in the same database transaction as Job creation to guarantee zero-loss dispatch.
    """
    __tablename__ = "job_outbox"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id = Column(Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    dispatched = Column(Boolean, nullable=False, default=False, index=True)
    retry_count = Column(Integer, nullable=False, default=0)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
        index=True
    )
    dispatched_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    job = relationship("Job", back_populates="outbox_entries")

    __table_args__ = (
        Index("ix_job_outbox_pending", "dispatched", "created_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Converts JobOutbox instance to dictionary representation."""
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "payload": self.payload,
            "dispatched": self.dispatched,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "dispatched_at": self.dispatched_at.isoformat() if self.dispatched_at else None,
        }
