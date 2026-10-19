"""Automated tests for Cluster Administration control plane endpoints."""

import uuid
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token_for_user


@pytest.mark.asyncio
async def test_admin_endpoints_require_admin_privileges(async_client: AsyncClient):
    """Verify that regular authenticated users receive 403 Forbidden on admin endpoints."""
    user_id = uuid.uuid4()
    user_token = create_access_token_for_user(
        user_id=user_id,
        email="operator@taskforge.dev",
        role="authenticated"
    )

    # 1. Test cluster status
    res = await async_client.get(
        "/api/v1/admin/cluster-status",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert res.status_code == 403
    assert "Operation requires administrative privileges" in res.json()["error"]["message"]

    # 2. Test recover leases
    res = await async_client.post(
        "/api/v1/admin/recover-leases",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert res.status_code == 403

    # 3. Test sweep outbox
    res = await async_client.post(
        "/api/v1/admin/sweep-outbox",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_admin_endpoints_permitted_for_service_role(async_client: AsyncClient):
    """Verify that admin / service_role callers can invoke admin maintenance endpoints."""
    admin_id = uuid.uuid4()
    admin_token = create_access_token_for_user(
        user_id=admin_id,
        email="admin@taskforge.dev",
        role="service_role"
    )

    # 1. Test cluster status
    res = await async_client.get(
        "/api/v1/admin/cluster-status",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "operational"
    assert "total_jobs" in data
    assert "distinct_tenants" in data

    # 2. Test recover leases
    res = await async_client.post(
        "/api/v1/admin/recover-leases",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "success"
    assert "recovered_count" in res.json()

    # 3. Test sweep outbox
    res = await async_client.post(
        "/api/v1/admin/sweep-outbox",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "success"
    assert "dispatched_count" in res.json()
