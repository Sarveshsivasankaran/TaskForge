"""Automated tests for Elasticsearch logs, CrewAI failure investigation, and real-time metrics."""

import uuid
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token_for_user
from app.queue.table_queue import TableQueueClient
from app.services.outbox_dispatcher import OutboxDispatcher
from app.workers.engine import WorkerEngine


@pytest.mark.asyncio
async def test_job_logs_endpoint(async_client: AsyncClient):
    """Verify that execution logs are captured and retrievable via GET /api/jobs/{job_id}/logs."""
    user_id = uuid.uuid4()
    token = create_access_token_for_user(user_id=user_id)

    # 1. Submit job
    res = await async_client.post(
        "/api/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={"job_type": "report_generation", "payload": {"rows": 100}}
    )
    job_id = res.json()["id"]

    # 2. Dispatch and execute
    dispatcher = OutboxDispatcher()
    await dispatcher.sweep_and_dispatch()

    worker = WorkerEngine(worker_id="test-log-worker")
    queue = TableQueueClient()
    
    # Process messages in queue until target job is executed
    for _ in range(5):
        messages = await queue.read(worker.queue_name, limit=10)
        if not messages:
            break
        for msg in messages:
            await worker.process_message(msg)

    # 3. Retrieve logs
    logs_res = await async_client.get(
        f"/api/jobs/{job_id}/logs",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) >= 2  # Started and Succeeded
    event_types = [l.get("event_type") for l in logs]
    assert "JOB_ATTEMPT_STARTED" in event_types
    assert "JOB_ATTEMPT_SUCCEEDED" in event_types


@pytest.mark.asyncio
async def test_ai_failure_investigation_workflow(async_client: AsyncClient):
    """Verify that users can request evidence-grounded AI investigations on failed jobs."""
    user_id = uuid.uuid4()
    token = create_access_token_for_user(user_id=user_id)

    # 1. Submit a poison pill job guaranteed to fail
    res = await async_client.post(
        "/api/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={"job_type": "chaos_poison_pill", "payload": {"error_message": "Invalid JSON syntax"}}
    )
    job_id = res.json()["id"]

    # 2. Dispatch and execute with worker
    dispatcher = OutboxDispatcher()
    await dispatcher.sweep_and_dispatch()

    worker = WorkerEngine(worker_id="test-inv-worker")
    queue = TableQueueClient()
    for _ in range(5):
        messages = await queue.read(worker.queue_name, limit=10)
        if not messages:
            break
        for msg in messages:
            await worker.process_message(msg)

    # 3. Request AI investigation
    inv_res = await async_client.post(
        f"/api/jobs/{job_id}/investigate",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert inv_res.status_code == 200
    inv_data = inv_res.json()
    assert "report" in inv_data
    report = inv_data["report"]
    assert "probable_root_cause" in report
    assert "Poison Pill" in report["probable_root_cause"] or "validation" in report["probable_root_cause"].lower()
    assert len(report["supporting_evidence"]) >= 1
    assert len(report["recommended_next_steps"]) >= 1

    # 4. List investigations
    list_res = await async_client.get(
        f"/api/jobs/{job_id}/investigations",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1


@pytest.mark.asyncio
async def test_metrics_summary_endpoint(async_client: AsyncClient):
    """Verify that aggregate metrics reflect real database execution records."""
    user_id = uuid.uuid4()
    token = create_access_token_for_user(user_id=user_id)

    # Submit 2 jobs
    await async_client.post(
        "/api/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={"job_type": "report_generation", "payload": {}}
    )
    await async_client.post(
        "/api/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={"job_type": "notification_dispatch", "payload": {}}
    )

    # Fetch metrics
    metrics_res = await async_client.get(
        "/api/metrics/summary",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()
    assert metrics["total_jobs"] >= 2
    assert "by_job_type" in metrics
    assert "report_generation" in metrics["by_job_type"]
    assert "notification_dispatch" in metrics["by_job_type"]
