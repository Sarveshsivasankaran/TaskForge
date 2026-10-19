"""Investigation report ORM model."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy import Column, String, DateTime, JSON, Uuid, ForeignKey, Index, text
from sqlalchemy.orm import relationship
from app.core.database import Base


class JobInvestigation(Base):
    """
    Persisted AI investigation report associated with a failed or dead-letter job.
    """
    __tablename__ = "job_investigations"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id = Column(Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    report = Column(JSON, nullable=False)
    provider = Column(String(50), nullable=False, default="mock")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
        index=True
    )

    # Relationships
    job = relationship("Job", backref="investigations")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "report": self.report,
            "provider": self.provider,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
