"""Schemas for aggregate platform metrics."""

from typing import Dict
from pydantic import BaseModel, Field


class MetricsSummaryResponse(BaseModel):
    """Aggregate platform metrics computed from authoritative database records."""
    total_jobs: int = Field(default=0, description="Total submitted jobs")
    queued_jobs: int = Field(default=0, description="Jobs currently waiting in queue")
    running_jobs: int = Field(default=0, description="Jobs currently actively running")
    succeeded_jobs: int = Field(default=0, description="Jobs completed successfully")
    failed_jobs: int = Field(default=0, description="Jobs in failed status")
    dead_letter_jobs: int = Field(default=0, description="Jobs in dead letter status")
    retry_wait_jobs: int = Field(default=0, description="Jobs in backoff retry wait")
    cancelled_jobs: int = Field(default=0, description="Jobs cancelled by user")
    total_attempts: int = Field(default=0, description="Total execution attempts recorded")
    avg_duration_ms: float = Field(default=0.0, description="Average execution duration in milliseconds")
    failure_rate_percent: float = Field(default=0.0, description="Percentage of finalized jobs that failed")
    by_job_type: Dict[str, int] = Field(default_factory=dict, description="Job counts broken down by type")
