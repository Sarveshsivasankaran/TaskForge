"""Integration tests for Job management REST API endpoints."""

import uuid
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token_for_user
from app.models.enums import JobStatus
from app.models.job import Job
from app.core.database import AsyncSessionLocal


@pytest.mark.asyncio
async def test_submit_valid_job(async_client: AsyncClient):
    """Verify that an authenticated user can submit a registered job."""
    user_id = uuid.uuid4()
    token = create_access_token_for_user(user_id=user_id)

    response = await async_client.post(
        "/api/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "job_type": "report_generation",
            "payload": {"format": "csv", "filters": {"year": 2026}},
            "timeout_seconds": 120,
            "max_attempts": 3
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["job_type"] == "report_generation"
    assert data["status"] == "queued"
    assert data["attempt_count"] == 0
    assert data["max_attempts"] == 3


@pytest.mark.asyncio
async def test_submit_invalid_job_type_rejected(async_client: AsyncClient):
    """Verify that unregistered arbitrary job types are rejected with 422."""
    user_id = uuid.uuid4()
    token = create_access_token_for_user(user_id=user_id)

    response = await async_client.post(
        "/api/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "job_type": "arbitrary_eval_shell",
            "payload": {"code": "import os; os.system('echo')"}
        }
    )
    assert response.status_code == 422
    data = response.json()
    assert "Unknown job_type" in str(data)


@pytest.mark.asyncio
async def test_job_submission_idempotency(async_client: AsyncClient):
    """Verify that retrying a submission with the same idempotency_key returns the original job."""
    user_id = uuid.uuid4()
    token = create_access_token_for_user(user_id=user_id)
    idemp_key = "submit-key-abc-999"

    # First submission
    res1 = await async_client.post(
        "/api/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "job_type": "dataset_processing",
            "payload": {"dataset_id": "ds-100"},
            "idempotency_key": idemp_key
        }
    )
    assert res1.status_code == 201
    job1_id = res1.json()["id"]

    # Duplicate submission
    res2 = await async_client.post(
        "/api/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "job_type": "dataset_processing",
            "payload": {"dataset_id": "ds-100"},
            "idempotency_key": idemp_key
        }
    )
    assert res2.status_code == 200  # Idempotent response
    assert res2.json()["id"] == job1_id


@pytest.mark.asyncio
async def test_tenant_job_isolation(async_client: AsyncClient):
    """Verify that User A cannot view or manipulate User B's job."""
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    token_a = create_access_token_for_user(user_id=user_a)
    token_b = create_access_token_for_user(user_id=user_b)

    # User A creates a job
    res_a = await async_client.post(
        "/api/jobs",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"job_type": "notification_dispatch", "payload": {"recipient": "a@taskforge.dev"}}
    )
    job_a_id = res_a.json()["id"]

    # User B attempts to read User A's job -> 404
    get_res = await async_client.get(
        f"/api/jobs/{job_a_id}",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert get_res.status_code == 404

    # User B attempts to cancel User A's job -> 404
    cancel_res = await async_client.post(
        f"/api/jobs/{job_a_id}/cancel",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert cancel_res.status_code == 404


@pytest.mark.asyncio
async def test_cancel_queued_job(async_client: AsyncClient):
    """Verify that an owner can cancel their queued job."""
    user_id = uuid.uuid4()
    token = create_access_token_for_user(user_id=user_id)

    res = await async_client.post(
        "/api/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={"job_type": "data_pipeline", "payload": {"step": 1}}
    )
    job_id = res.json()["id"]

    cancel_res = await async_client.post(
        f"/api/jobs/{job_id}/cancel",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["current_status"] == "cancelled"

    # Verify state in database
    detail_res = await async_client.get(
        f"/api/jobs/{job_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert detail_res.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_list_jobs_filtering_and_events(async_client: AsyncClient):
    """Verify listing with query parameters and retrieving lifecycle events."""
    user_id = uuid.uuid4()
    token = create_access_token_for_user(user_id=user_id)

    # Create 2 jobs
    await async_client.post(
        "/api/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={"job_type": "report_generation", "payload": {}}
    )
    res2 = await async_client.post(
        "/api/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={"job_type": "notification_dispatch", "payload": {}}
    )
    job2_id = res2.json()["id"]

    # List filtered by job_type
    list_res = await async_client.get(
        "/api/jobs?job_type=notification_dispatch",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert all(item["job_type"] == "notification_dispatch" for item in list_data["items"])

    # Retrieve events
    events_res = await async_client.get(
        f"/api/jobs/{job2_id}/events",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert events_res.status_code == 200
    events = events_res.json()
    assert len(events) >= 1
    assert events[0]["event_type"] == "JOB_CREATED"
