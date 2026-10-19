"""Cluster Administration and Control Plane Endpoints.
Restricted exclusively to users with 'admin' or 'service_role' claims.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
from app.core.security import AuthenticatedUser, require_admin
from app.models.job import Job
from app.models.outbox import JobOutbox
from app.models.enums import JobStatus
from app.workers.recovery import AbandonedJobRecoveryService
from app.services.outbox_dispatcher import OutboxDispatcher

router = APIRouter(prefix="/admin", tags=["Cluster Administration"])


@router.get(
    "/cluster-status",
    summary="Cluster control plane diagnostics",
    description="Returns aggregate cluster infrastructure telemetry across all tenants."
)
async def get_cluster_status(
    admin: AuthenticatedUser = Depends(require_admin),
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    # 1. Total jobs and distinct tenants
    res_tenants = await session.execute(
        select(func.count(Job.id), func.count(func.distinct(Job.owner_id)))
    )
    total_jobs, distinct_tenants = res_tenants.first() or (0, 0)

    # 2. Outbox pending count
    res_outbox = await session.execute(
        select(func.count(JobOutbox.id)).where(JobOutbox.dispatched == False)  # noqa: E712
    )
    pending_outbox = res_outbox.scalar() or 0

    # 3. Status breakdown
    res_statuses = await session.execute(
        select(Job.status, func.count(Job.id)).group_by(Job.status)
    )
    status_map = {row[0]: row[1] for row in res_statuses.all()}

    return {
        "status": "operational",
        "cluster_mode": "multi_tenant",
        "authorized_admin": admin.email,
        "caller_id": str(admin.id),
        "total_jobs": total_jobs,
        "distinct_tenants": distinct_tenants,
        "pending_outbox": pending_outbox,
        "dead_letter_jobs": status_map.get(JobStatus.DEAD_LETTER.value, 0),
        "running_jobs": status_map.get(JobStatus.RUNNING.value, 0),
        "queued_jobs": status_map.get(JobStatus.QUEUED.value, 0),
        "succeeded_jobs": status_map.get(JobStatus.SUCCEEDED.value, 0),
        "status_distribution": status_map
    }


@router.post(
    "/recover-leases",
    summary="Trigger abandoned lease recovery scan",
    description="Scans running jobs with expired heartbeats, fences crashed workers, and re-enqueues jobs."
)
async def trigger_recover_leases(
    admin: AuthenticatedUser = Depends(require_admin)
) -> Dict[str, Any]:
    recovery_service = AbandonedJobRecoveryService()
    recovered_count = await recovery_service.recover_abandoned_jobs()
    return {
        "status": "success",
        "action": "recover_abandoned_leases",
        "recovered_count": recovered_count,
        "message": f"Cluster scan completed: {recovered_count} expired worker lease(s) recovered.",
        "triggered_by": admin.email
    }


@router.post(
    "/sweep-outbox",
    summary="Trigger transactional outbox sweep",
    description="Sweeps pending transactional outbox records and publishes them to the queue broker."
)
async def trigger_sweep_outbox(
    admin: AuthenticatedUser = Depends(require_admin)
) -> Dict[str, Any]:
    dispatcher = OutboxDispatcher()
    dispatched_count = await dispatcher.sweep_and_dispatch(batch_size=50)
    return {
        "status": "success",
        "action": "sweep_outbox",
        "dispatched_count": dispatched_count,
        "message": f"Outbox sweep completed: {dispatched_count} pending message(s) dispatched to queue.",
        "triggered_by": admin.email
    }
