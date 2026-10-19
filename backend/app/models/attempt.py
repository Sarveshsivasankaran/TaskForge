"""Execution Attempt ORM model."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy import (
    Column,
    String,
    Integer,
    BigInteger,
    DateTime,
    JSON,
    Text,
    Uuid,
    ForeignKey,
    Index,
    text
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.enums import AttemptStatus


class JobAttempt(Base):
    """
    Immutable audit record for a single execution attempt of a job.
    """
    __tablename__ = "job_attempts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id = Column(Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_number = Column(Integer, nullable=False)
    worker_id = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, default=AttemptStatus.RUNNING.value)

    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP")
    )
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(BigInteger, nullable=True)

    error_type = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    result = Column(JSON, nullable=True)
    lease_token = Column(Uuid, nullable=True)

    # Relationships
    job = relationship("Job", back_populates="attempts")

    __table_args__ = (
        Index("ix_job_attempts_job_number", "job_id", "attempt_number"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Converts JobAttempt instance to dictionary representation."""
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "attempt_number": self.attempt_number,
            "worker_id": self.worker_id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "result": self.result,
            "lease_token": str(self.lease_token) if self.lease_token else None,
        }
