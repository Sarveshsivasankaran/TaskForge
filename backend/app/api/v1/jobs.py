"""Job management REST endpoints."""

import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import AuthenticatedUser, get_current_user
from app.core.rate_limit import limiter
from app.models.enums import JobStatus, validate_job_state_transition, InvalidStateTransitionError
from app.models.job import Job
from app.models.attempt import JobAttempt
from app.models.event import JobEvent
from app.services.job_repository import JobRepository
from app.schemas.job import (
    JobCreateRequest,
    JobResponse,
    JobListResponse,
    JobAttemptResponse,
    JobEventResponse,
    JobActionResponse
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new background job",
    description="Submits and persists an asynchronous job with transactional outbox dispatch."
)
@limiter.limit("60/minute")
async def submit_job(
    request: Request,
    response: Response,
    body: JobCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
) -> JobResponse:
    job, created = await JobRepository.create_job_with_outbox(
        session=session,
        owner_id=current_user.id,
        job_type=body.job_type,
        payload=body.payload,
        idempotency_key=body.idempotency_key,
        max_attempts=body.max_attempts or 5,
        timeout_seconds=body.timeout_seconds or 300,
        next_run_at=body.scheduled_at
    )

    if not created:
        # Idempotency hit: return existing job with 200 OK instead of 201
        response.status_code = status.HTTP_200_OK

    return JobResponse(**job.to_dict())


@router.get(
    "",
    response_model=JobListResponse,
    summary="List background jobs",
    description="Lists jobs visible to the caller with optional filtering and pagination."
)
@limiter.limit("120/minute")
async def list_jobs(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status (e.g. queued, running, succeeded, failed)"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
) -> JobListResponse:
    # Standard users only see their own jobs; service_role can view all
    owner_filter = None if current_user.is_service_role else current_user.id

    items, total = await JobRepository.list_jobs(
        session=session,
        owner_id=owner_filter,
        status=status,
        job_type=job_type,
        limit=limit,
        offset=offset
    )

    return JobListResponse(
        items=[JobResponse(**j.to_dict()) for j in items],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job details",
    description="Retrieves authoritative state, attempt counts, outcome, and error details for a job."
)
async def get_job_detail(
    job_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
) -> JobResponse:
    owner_filter = None if current_user.is_service_role else current_user.id
    job = await JobRepository.get_by_id(session, job_id, owner_id=owner_filter)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found."
        )

    return JobResponse(**job.to_dict())


@router.get(
    "/{job_id}/attempts",
    response_model=List[JobAttemptResponse],
    summary="Get execution attempts",
    description="Retrieves chronological execution attempts and failure diagnostic traces for a job."
)
async def get_job_attempts(
    job_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
) -> List[JobAttemptResponse]:
    owner_filter = None if current_user.is_service_role else current_user.id
    job = await JobRepository.get_by_id(session, job_id, owner_id=owner_filter)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found."
        )

    query = select(JobAttempt).where(JobAttempt.job_id == job_id).order_by(JobAttempt.attempt_number.asc())
    attempts = (await session.execute(query)).scalars().all()
    return [JobAttemptResponse(**a.to_dict()) for a in attempts]


@router.get(
    "/{job_id}/events",
    response_model=List[JobEventResponse],
    summary="Get job audit events",
    description="Retrieves the append-only lifecycle event trail for a job."
)
async def get_job_events(
    job_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
) -> List[JobEventResponse]:
    owner_filter = None if current_user.is_service_role else current_user.id
    job = await JobRepository.get_by_id(session, job_id, owner_id=owner_filter)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found."
        )

    query = select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.created_at.asc())
    events = (await session.execute(query)).scalars().all()
    return [JobEventResponse(**e.to_dict()) for e in events]


@router.post(
    "/{job_id}/cancel",
    response_model=JobActionResponse,
    summary="Cancel a queued or retry-wait job",
    description="Cancels an eligible job to prevent worker execution."
)
async def cancel_job(
    job_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
) -> JobActionResponse:
    owner_filter = None if current_user.is_service_role else current_user.id
    job = await JobRepository.get_by_id(session, job_id, owner_id=owner_filter)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found."
        )

    try:
        validate_job_state_transition(job.status, JobStatus.CANCELLED)
    except InvalidStateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job in '{job.status}' status. {str(e)}"
        )

    now = datetime.now(timezone.utc)
    job.status = JobStatus.CANCELLED.value
    job.completed_at = now
    job.version += 1
    job.updated_at = now

    event = JobEvent(
        id=uuid.uuid4(),
        job_id=job.id,
        event_type="JOB_CANCELLED",
        event_data={"cancelled_by": str(current_user.id)},
        created_at=now
    )
    session.add(event)
    await session.commit()

    return JobActionResponse(
        status="cancelled",
        message=f"Job {job_id} successfully cancelled.",
        job_id=job_id,
        current_status=JobStatus.CANCELLED.value
    )


@router.post(
    "/{job_id}/retry",
    response_model=JobActionResponse,
    summary="Manual retry for failed or dead-letter job",
    description="Authorized manual retry creating an outbox dispatch record and lifecycle event."
)
async def manual_retry_job(
    job_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
) -> JobActionResponse:
    owner_filter = None if current_user.is_service_role else current_user.id
    job = await JobRepository.get_by_id(session, job_id, owner_id=owner_filter)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found."
        )

    try:
        retried_job = await JobRepository.manual_retry(session, job_id, owner_id=owner_filter)
        await session.commit()
    except InvalidStateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job cannot be manually retried: {str(e)}"
        )

    return JobActionResponse(
        status="queued",
        message=f"Job {job_id} has been re-queued for execution.",
        job_id=job_id,
        current_status=JobStatus.QUEUED.value
    )
