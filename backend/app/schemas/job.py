"""Pydantic schemas for Job management, attempts, and audit events."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


# Approved registered job types
REGISTERED_JOB_TYPES = {
    "report_generation",
    "dataset_processing",
    "notification_dispatch",
    "data_pipeline",
    "chaos_flaky_task",
    "chaos_poison_pill",
    "chaos_slow_worker"
}


class JobCreateRequest(BaseModel):
    """Schema for submitting a background job."""
    job_type: str = Field(..., description="Registered job type")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Job payload parameters")
    idempotency_key: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Optional client deduplication idempotency key"
    )
    max_attempts: Optional[int] = Field(default=5, ge=1, le=20, description="Maximum retry attempts")
    timeout_seconds: Optional[int] = Field(default=300, ge=5, le=3600, description="Execution deadline in seconds")
    scheduled_at: Optional[datetime] = Field(default=None, description="Optional deferred execution timestamp")

    @field_validator("job_type")
    @classmethod
    def validate_job_type(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in REGISTERED_JOB_TYPES:
            raise ValueError(
                f"Unknown job_type '{clean}'. Must be one of: {sorted(list(REGISTERED_JOB_TYPES))}"
            )
        return clean


class JobResponse(BaseModel):
    """Authoritative Job details response model."""
    id: uuid.UUID
    owner_id: uuid.UUID
    job_type: str
    payload: Dict[str, Any]
    status: str
    attempt_count: int
    max_attempts: int
    timeout_seconds: int
    idempotency_key: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    last_error: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    lease_owner: Optional[str] = None
    version: int


class JobListResponse(BaseModel):
    """Paginated list of jobs."""
    items: List[JobResponse]
    total: int
    limit: int
    offset: int


class JobAttemptResponse(BaseModel):
    """Execution attempt record response."""
    id: uuid.UUID
    job_id: uuid.UUID
    attempt_number: int
    worker_id: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class JobEventResponse(BaseModel):
    """Lifecycle event response."""
    id: uuid.UUID
    job_id: uuid.UUID
    event_type: str
    event_data: Dict[str, Any]
    created_at: datetime


class JobActionResponse(BaseModel):
    """Standardized action response for cancellation or manual retry."""
    status: str
    message: str
    job_id: uuid.UUID
    current_status: str
