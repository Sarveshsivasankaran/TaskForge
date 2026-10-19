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


@pytest.mark.asyncio
async def test_observability_secret_redaction():
    """Verify that sensitive secrets and tokens are redacted before buffering or indexing."""
    from app.observability.client import es_observability
    test_job_id = str(uuid.uuid4())
    event = es_observability.record_event(
        level="WARN",
        message="Failed auth with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9 and password=secret123",
        job_id=test_job_id,
        extra={"api_key": "sk-1234567890abcdef", "safe_param": 42}
    )
    assert "[REDACTED" in event["message"]
    assert "secret123" not in event["message"]
    assert event["data"]["api_key"] == "[REDACTED]"
    assert event["data"]["safe_param"] == 42


@pytest.mark.asyncio
async def test_failure_patterns_endpoint(async_client: AsyncClient):
    """Verify that failure patterns and aggregations are retrievable via GET /api/metrics/failure-patterns."""
    from app.observability.client import es_observability
    test_id = str(uuid.uuid4())
    es_observability.record_event(
        level="ERROR",
        message="Simulated connection timeout",
        job_id=test_id,
        error_type="TimeoutError",
        event_type="JOB_ATTEMPT_RETRYING",
        duration_ms=450
    )

    res = await async_client.get("/api/metrics/failure-patterns")
    assert res.status_code == 200
    data = res.json()
    assert "top_error_patterns" in data
    assert "total_retries_observed" in data
    assert "duration_metrics" in data
    assert data["total_retries_observed"] >= 1


@pytest.mark.asyncio
async def test_job_timeline_endpoint(async_client: AsyncClient):
    """Verify that a unified chronological timeline is retrievable via GET /api/jobs/{job_id}/timeline."""
    user_id = uuid.uuid4()
    token = create_access_token_for_user(user_id=user_id)

    # Submit job
    res = await async_client.post(
        "/api/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={"job_type": "report_generation", "payload": {"rows": 50}}
    )
    job_id = res.json()["id"]

    timeline_res = await async_client.get(
        f"/api/jobs/{job_id}/timeline",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert timeline_res.status_code == 200
    timeline = timeline_res.json()
    assert len(timeline) >= 1
    assert timeline[0]["category"] == "JOB_SUBMITTED"
    assert "timestamp" in timeline[0]


@pytest.mark.asyncio
async def test_crewai_investigator_insufficient_evidence():
    """Verify that CrewAIFailureInvestigator reports insufficient evidence when telemetry is missing."""
    from app.ai.crewai_investigator import CrewAIFailureInvestigator
    from app.models.job import Job

    dummy_job = Job(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        job_type="unknown_task",
        payload={},
        status="failed",
        max_attempts=3,
        attempt_count=0,
        last_error=None
    )

    report = CrewAIFailureInvestigator.generate_grounded_investigation(
        job=dummy_job,
        attempts=[],
        clean_logs=[]
    )
    assert report.confidence_level == "insufficient_evidence"
    assert "unavailable" in report.probable_root_cause.lower()

