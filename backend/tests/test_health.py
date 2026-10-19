"""Health check endpoint integration tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_root_endpoint(async_client: AsyncClient):
    """Verify /api/health returns 200 OK with expected fields."""
    response = await async_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app_name"] == "TaskForge"
    assert "timestamp" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_health_v1_endpoint(async_client: AsyncClient):
    """Verify /api/v1/health returns 200 OK with expected fields."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app_name"] == "TaskForge"


@pytest.mark.asyncio
async def test_liveness_endpoint(async_client: AsyncClient):
    """Verify /api/health/live returns alive status."""
    response = await async_client.get("/api/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


@pytest.mark.asyncio
async def test_readiness_endpoint(async_client: AsyncClient):
    """Verify /api/health/ready returns ready status and dependency map."""
    response = await async_client.get("/api/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "dependencies" in data
    assert "api" in data["dependencies"]
    assert data["dependencies"]["api"] == "healthy"


@pytest.mark.asyncio
async def test_standard_404_error_format(async_client: AsyncClient):
    """Verify that non-existent routes return standardized JSON error format."""
    response = await async_client.get("/api/non-existent-endpoint")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "HTTP_404"
    assert data["error"]["status_code"] == 404
