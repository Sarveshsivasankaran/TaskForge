"""Automated test suite for Supabase JWT verification, authentication dependencies, and RBAC."""

import uuid
import time
import pytest
from httpx import AsyncClient
import jwt

from app.core.config import settings
from app.core.security import create_access_token_for_user


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(async_client: AsyncClient):
    """Verify that requests without an Authorization header are rejected with 401."""
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data or "error" in data


@pytest.mark.asyncio
async def test_tampered_token_rejected(async_client: AsyncClient):
    """Verify that a tampered or invalid signature is rejected with 401."""
    user_id = uuid.uuid4()
    # Sign with a completely different secret key
    fake_token = jwt.encode(
        {"sub": str(user_id), "exp": int(time.time()) + 3600, "role": "authenticated"},
        "wrong-secret-key-attacker-32-chars-long",
        algorithm="HS256"
    )

    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {fake_token}"}
    )
    assert response.status_code == 401
    data = response.json()
    assert "Invalid authentication token" in str(data)


@pytest.mark.asyncio
async def test_expired_token_rejected(async_client: AsyncClient):
    """Verify that an expired token is rejected with 401."""
    user_id = uuid.uuid4()
    # Create token expired 1 hour ago
    expired_token = create_access_token_for_user(
        user_id=user_id,
        email="expired@taskforge.dev",
        expires_in_seconds=-3600
    )

    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401
    data = response.json()
    assert "expired" in str(data).lower()


@pytest.mark.asyncio
async def test_valid_token_authenticated_profile(async_client: AsyncClient):
    """Verify that a validly signed token is accepted and claims are parsed."""
    user_id = uuid.uuid4()
    token = create_access_token_for_user(
        user_id=user_id,
        email="operator@taskforge.dev",
        role="authenticated"
    )

    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user_id)
    assert data["email"] == "operator@taskforge.dev"
    assert data["role"] == "authenticated"
    assert data["is_admin"] is False


@pytest.mark.asyncio
async def test_regular_user_forbidden_from_admin_endpoint(async_client: AsyncClient):
    """Verify that standard authenticated users are denied access to admin endpoints."""
    user_id = uuid.uuid4()
    token = create_access_token_for_user(
        user_id=user_id,
        email="normal_user@taskforge.dev",
        role="authenticated"
    )

    response = await async_client.get(
        "/api/v1/auth/admin-only",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    data = response.json()
    assert "administrative privileges" in str(data)


@pytest.mark.asyncio
async def test_admin_user_permitted_on_admin_endpoint(async_client: AsyncClient):
    """Verify that users with admin claims or service_role can access administrative endpoints."""
    admin_id = uuid.uuid4()
    # 1. Test service_role
    service_token = create_access_token_for_user(
        user_id=admin_id,
        email="service@taskforge.dev",
        role="service_role"
    )
    res_svc = await async_client.get(
        "/api/v1/auth/admin-only",
        headers={"Authorization": f"Bearer {service_token}"}
    )
    assert res_svc.status_code == 200
    assert res_svc.json()["status"] == "success"

    # 2. Test app_metadata admin claim
    admin_token = create_access_token_for_user(
        user_id=admin_id,
        email="admin@taskforge.dev",
        role="authenticated",
        custom_claims={"app_metadata": {"role": "admin"}}
    )
    res_admin = await async_client.get(
        "/api/v1/auth/admin-only",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_admin.status_code == 200
    assert res_admin.json()["caller_id"] == str(admin_id)


@pytest.mark.asyncio
async def test_demo_token_endpoint(async_client: AsyncClient):
    """Verify that the dev demo token endpoint returns a functional signed token."""
    requested_id = uuid.uuid4()
    response = await async_client.post(
        "/api/v1/auth/demo-token",
        json={"user_id": str(requested_id), "email": "test@taskforge.dev", "role": "authenticated"}
    )
    assert response.status_code == 200
    token_data = response.json()
    assert "token" in token_data
    token = token_data["token"]

    # Use the generated token to call /me
    me_res = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_res.status_code == 200
    assert me_res.json()["id"] == str(requested_id)
    assert me_res.json()["email"] == "test@taskforge.dev"
