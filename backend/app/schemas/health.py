"""Health check response schemas."""

from datetime import datetime, timezone
from typing import Dict, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Basic health check status."""
    status: str = Field(default="ok", description="Overall system status")
    app_name: str = Field(default="TaskForge", description="Application name")
    environment: str = Field(default="development", description="Current environment")
    version: str = Field(default="0.1.0", description="Application version")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC check timestamp"
    )


class ReadinessResponse(HealthResponse):
    """Readiness probe response including subsystem statuses."""
    dependencies: Dict[str, str] = Field(
        default_factory=dict,
        description="Dependency status mapping (e.g. database, queue, cache)"
    )
    details: Optional[Dict[str, str]] = None
