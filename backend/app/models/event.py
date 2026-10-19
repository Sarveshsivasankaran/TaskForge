"""Job Lifecycle Event ORM model."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy import (
    Column,
    String,
    DateTime,
    JSON,
    Uuid,
    ForeignKey,
    Index,
    text
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class JobEvent(Base):
    """
    Append-only audit log for discrete job lifecycle transitions and operational actions.
    """
    __tablename__ = "job_events"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id = Column(Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    event_data = Column(JSON, nullable=False, default=dict)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
        index=True
    )

    # Relationships
    job = relationship("Job", back_populates="events")

    __table_args__ = (
        Index("ix_job_events_job_created", "job_id", "created_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Converts JobEvent instance to dictionary representation."""
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "event_type": self.event_type,
            "event_data": self.event_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
