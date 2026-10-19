"""Job management REST endpoints."""

import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import AuthenticatedUser, get_current_user, get_optional_user
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

DEFAULT_OPERATOR_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


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
    current_user: Optional[AuthenticatedUser] = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db)
) -> JobResponse:
    owner_id = current_user.id if current_user else DEFAULT_OPERATOR_USER_ID
    job, created = await JobRepository.create_job_with_outbox(
        session=session,
        owner_id=owner_id,
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
    current_user: Optional[AuthenticatedUser] = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db)
) -> JobListResponse:
    # Service role or unauthenticated operator views all jobs; authenticated standard user views their own
    owner_filter = None if (not current_user or current_user.is_service_role or current_user.is_admin) else current_user.id

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
    current_user: Optional[AuthenticatedUser] = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db)
) -> JobResponse:
    owner_filter = None if (not current_user or current_user.is_service_role or current_user.is_admin) else current_user.id
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
    current_user: Optional[AuthenticatedUser] = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db)
) -> List[JobAttemptResponse]:
    owner_filter = None if (not current_user or current_user.is_service_role or current_user.is_admin) else current_user.id
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
    current_user: Optional[AuthenticatedUser] = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db)
) -> List[JobEventResponse]:
    owner_filter = None if (not current_user or current_user.is_service_role or current_user.is_admin) else current_user.id
    job = await JobRepository.get_by_id(session, job_id, owner_id=owner_filter)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found."
        )

    query = select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.created_at.asc())
    events = (await session.execute(query)).scalars().all()
    return [JobEventResponse(**e.to_dict()) for e in events]


@router.get(
    "/{job_id}/logs",
    summary="Search execution logs in Elasticsearch",
    description="Queries correlated structured logs for a job from Elasticsearch or bounded buffer."
)
async def get_job_logs(
    job_id: uuid.UUID,
    attempt_id: Optional[str] = Query(None, description="Optional attempt ID filter"),
    level: Optional[str] = Query(None, description="Optional log level filter (INFO, WARN, ERROR)"),
    limit: int = Query(50, ge=1, le=200, description="Max logs to return"),
    current_user: Optional[AuthenticatedUser] = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db)
) -> List[dict]:
    owner_filter = None if (not current_user or current_user.is_service_role or current_user.is_admin) else current_user.id
    job = await JobRepository.get_by_id(session, job_id, owner_id=owner_filter)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found."
        )

    from app.observability.client import es_observability
    logs = await es_observability.search_logs(
        job_id=str(job_id),
        attempt_id=attempt_id,
        level=level,
        limit=limit
    )
    return logs


@router.get(
    "/{job_id}/timeline",
    summary="Get unified execution timeline",
    description="Returns a consolidated, chronological timeline combining lifecycle events, worker attempts, and observability logs."
)
async def get_job_timeline(
    job_id: uuid.UUID,
    current_user: Optional[AuthenticatedUser] = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db)
) -> List[dict]:
    owner_filter = None if (not current_user or current_user.is_service_role or current_user.is_admin) else current_user.id
    job = await JobRepository.get_by_id(session, job_id, owner_id=owner_filter)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found."
        )

    timeline = []
    # 1. Job submission
    if job.created_at:
        timeline.append({
            "timestamp": job.created_at.isoformat(),
            "type": "lifecycle",
            "category": "JOB_SUBMITTED",
            "title": f"Job submitted ({job.job_type})",
            "details": {"status": "queued", "max_attempts": job.max_attempts}
        })

    # 2. Database events
    query_events = select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.created_at.asc())
    events = (await session.execute(query_events)).scalars().all()
    for ev in events:
        timeline.append({
            "timestamp": ev.created_at.isoformat() if ev.created_at else None,
            "type": "event",
            "category": ev.event_type,
            "title": f"Event: {ev.event_type}",
            "details": ev.event_data or {}
        })

    # 3. Execution attempts
    query_att = select(JobAttempt).where(JobAttempt.job_id == job_id).order_by(JobAttempt.attempt_number.asc())
    attempts = (await session.execute(query_att)).scalars().all()
    for att in attempts:
        timeline.append({
            "timestamp": att.started_at.isoformat() if att.started_at else None,
            "type": "attempt",
            "category": f"ATTEMPT_{att.status.upper()}",
            "title": f"Attempt #{att.attempt_number} ({att.status}) on {att.worker_id}",
            "details": {
                "duration_ms": att.duration_ms,
                "error_type": att.error_type,
                "error_message": att.error_message,
                "finished_at": att.finished_at.isoformat() if att.finished_at else None
            }
        })

    timeline.sort(key=lambda x: x.get("timestamp") or "")
    return timeline


@router.post(
    "/{job_id}/cancel",
    response_model=JobActionResponse,
    summary="Cancel a queued or retry-wait job",
    description="Cancels an eligible job to prevent worker execution."
)
async def cancel_job(
    job_id: uuid.UUID,
    current_user: Optional[AuthenticatedUser] = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db)
) -> JobActionResponse:
    owner_filter = None if (not current_user or current_user.is_service_role or current_user.is_admin) else current_user.id
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
        event_data={"cancelled_by": str(current_user.id if current_user else "operator")},
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
    current_user: Optional[AuthenticatedUser] = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db)
) -> JobActionResponse:
    owner_filter = None if (not current_user or current_user.is_service_role or current_user.is_admin) else current_user.id
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


@router.post(
    "/{job_id}/investigate",
    summary="Request AI-assisted failure investigation",
    description="Triggers read-only root-cause analysis based on execution attempts and structured logs."
)
async def investigate_job(
    job_id: uuid.UUID,
    current_user: Optional[AuthenticatedUser] = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db)
) -> dict:
    owner_filter = None if (not current_user or current_user.is_service_role or current_user.is_admin) else current_user.id
    job = await JobRepository.get_by_id(session, job_id, owner_id=owner_filter, load_relations=True)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found."
        )

    from app.observability.client import es_observability
    from app.ai.investigator import FailureInvestigatorService

    logs = await es_observability.search_logs(job_id=str(job_id))
    investigation = await FailureInvestigatorService.investigate_job(
        session=session,
        job=job,
        attempts=job.attempts or [],
        logs=logs
    )

    return investigation.to_dict()


@router.get(
    "/{job_id}/investigations",
    summary="List investigation reports for a job",
    description="Returns persisted AI investigation reports."
)
async def get_job_investigations(
    job_id: uuid.UUID,
    current_user: Optional[AuthenticatedUser] = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db)
) -> List[dict]:
    owner_filter = None if (not current_user or current_user.is_service_role or current_user.is_admin) else current_user.id
    job = await JobRepository.get_by_id(session, job_id, owner_id=owner_filter)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found."
        )

    from app.models.investigation import JobInvestigation
    query = select(JobInvestigation).where(JobInvestigation.job_id == job_id).order_by(JobInvestigation.created_at.desc())
    reports = (await session.execute(query)).scalars().all()
    return [r.to_dict() for r in reports]
