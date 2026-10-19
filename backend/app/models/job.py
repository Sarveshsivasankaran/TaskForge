"""Authoritative Job ORM model."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    JSON,
    Uuid,
    Index,
    UniqueConstraint,
    text
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.enums import JobStatus


class Job(Base):
    """
    Authoritative state for an asynchronous job.
    Includes optimistic locking version and lease tokens for worker concurrency.
    """
    __tablename__ = "jobs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id = Column(Uuid, nullable=False, index=True)
    job_type = Column(String(100), nullable=False, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    status = Column(String(50), nullable=False, default=JobStatus.QUEUED.value, index=True)

    # Retry and execution limits
    attempt_count = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=5)
    timeout_seconds = Column(Integer, nullable=False, default=300)

    # Deduplication & Idempotency
    idempotency_key = Column(String(255), nullable=True, index=True)

    # Execution outcome
    result = Column(JSON, nullable=True)
    last_error = Column(JSON, nullable=True)

    # Timestamps (always UTC)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
        index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP")
    )
    next_run_at = Column(DateTime(timezone=True), nullable=True, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Concurrency control & Lease fencing
    lease_owner = Column(String(100), nullable=True)
    lease_token = Column(Uuid, nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    version = Column(Integer, nullable=False, default=1)

    # Relationships
    attempts = relationship(
        "JobAttempt",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="JobAttempt.attempt_number"
    )
    events = relationship(
        "JobEvent",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="JobEvent.created_at"
    )
    outbox_entries = relationship(
        "JobOutbox",
        back_populates="job",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Ensure an idempotency key is uniquely scoped to the submitting user/tenant
        UniqueConstraint("owner_id", "idempotency_key", name="uq_owner_idempotency_key"),
        # Compound index for dispatcher/recovery polling: finding runnable/expired jobs
        Index("ix_jobs_status_next_run", "status", "next_run_at"),
        Index("ix_jobs_lease_recovery", "status", "lease_expires_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Converts Job instance to dictionary representation."""
        return {
            "id": str(self.id),
            "owner_id": str(self.owner_id),
            "job_type": self.job_type,
            "payload": self.payload,
            "status": self.status,
            "attempt_count": self.attempt_count,
            "max_attempts": self.max_attempts,
            "timeout_seconds": self.timeout_seconds,
            "idempotency_key": self.idempotency_key,
            "result": self.result,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "lease_owner": self.lease_owner,
            "lease_token": str(self.lease_token) if self.lease_token else None,
            "lease_expires_at": self.lease_expires_at.isoformat() if self.lease_expires_at else None,
            "version": self.version,
        }
