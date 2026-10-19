"""Platform Metrics aggregation API."""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import AuthenticatedUser, get_current_user
from app.models.enums import JobStatus, AttemptStatus
from app.models.job import Job
from app.models.attempt import JobAttempt
from app.schemas.metrics import MetricsSummaryResponse

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get(
    "/summary",
    response_model=MetricsSummaryResponse,
    summary="Get aggregate platform metrics",
    description="Calculates real-time aggregate execution metrics from authoritative database records."
)
async def get_metrics_summary(
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
) -> MetricsSummaryResponse:
    # Service role views global metrics; individual users view their tenant metrics
    where_clause = True if current_user.is_service_role else (Job.owner_id == current_user.id)

    # 1. Status counts
    status_query = (
        select(Job.status, func.count(Job.id))
        .where(where_clause)
        .group_by(Job.status)
    )
    status_rows = (await session.execute(status_query)).all()
    counts = {r[0]: r[1] for r in status_rows}

    total_jobs = sum(counts.values())
    queued = counts.get(JobStatus.QUEUED.value, 0)
    running = counts.get(JobStatus.RUNNING.value, 0)
    succeeded = counts.get(JobStatus.SUCCEEDED.value, 0)
    failed = counts.get(JobStatus.FAILED.value, 0)
    dead_letter = counts.get(JobStatus.DEAD_LETTER.value, 0)
    retry_wait = counts.get(JobStatus.RETRY_WAIT.value, 0)
    cancelled = counts.get(JobStatus.CANCELLED.value, 0)

    # 2. Type counts
    type_query = (
        select(Job.job_type, func.count(Job.id))
        .where(where_clause)
        .group_by(Job.job_type)
    )
    type_rows = (await session.execute(type_query)).all()
    by_type = {r[0]: r[1] for r in type_rows}

    # 3. Attempt stats and average duration
    attempt_where = True
    if not current_user.is_service_role:
        # Join to filter by owner_id
        attempt_query = (
            select(
                func.count(JobAttempt.id),
                func.avg(JobAttempt.duration_ms)
            )
            .join(Job, Job.id == JobAttempt.job_id)
            .where(Job.owner_id == current_user.id)
        )
    else:
        attempt_query = select(
            func.count(JobAttempt.id),
            func.avg(JobAttempt.duration_ms)
        )

    att_res = (await session.execute(attempt_query)).first()
    total_attempts = att_res[0] or 0
    avg_duration = round(float(att_res[1] or 0.0), 2)

    # 4. Failure rate
    finalized = succeeded + failed + dead_letter
    failure_rate = round(((failed + dead_letter) / finalized * 100.0), 2) if finalized > 0 else 0.0

    return MetricsSummaryResponse(
        total_jobs=total_jobs,
        queued_jobs=queued,
        running_jobs=running,
        succeeded_jobs=succeeded,
        failed_jobs=failed,
        dead_letter_jobs=dead_letter,
        retry_wait_jobs=retry_wait,
        cancelled_jobs=cancelled,
        total_attempts=total_attempts,
        avg_duration_ms=avg_duration,
        failure_rate_percent=failure_rate,
        by_job_type=by_type
    )
