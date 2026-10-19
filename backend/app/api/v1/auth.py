"""Authentication and authorization verification endpoints."""

from fastapi import APIRouter, Depends, Request
from app.core.security import AuthenticatedUser, get_current_user, require_admin
from app.core.rate_limit import limiter
from app.schemas.auth import (
    UserProfileResponse,
    AdminActionResponse,
    DemoTokenRequest,
    DemoTokenResponse
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user profile",
    description="Validates the caller's JWT access token and returns user profile claims."
)
@limiter.limit("60/minute")
async def get_me(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> UserProfileResponse:
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        is_admin=current_user.is_admin
    )


@router.get(
    "/admin-only",
    response_model=AdminActionResponse,
    summary="Protected administrative endpoint",
    description="Requires service_role or admin privileges in token claims."
)
@limiter.limit("30/minute")
async def get_admin_data(
    request: Request,
    admin_user: AuthenticatedUser = Depends(require_admin)
) -> AdminActionResponse:
    return AdminActionResponse(
        status="success",
        message="Administrative action authorized.",
        caller_id=admin_user.id
    )


@router.post(
    "/demo-token",
    response_model=DemoTokenResponse,
    summary="Generate signed test JWT (Dev/Test only)",
    description="Generates a signed JWT access token for testing and dashboard evaluation."
)
async def generate_demo_token(
    payload: DemoTokenRequest
) -> DemoTokenResponse:
    import uuid
    from app.core.security import create_access_token_for_user
    user_id = payload.user_id or uuid.uuid4()
    token = create_access_token_for_user(
        user_id=user_id,
        email=payload.email,
        role=payload.role
    )
    return DemoTokenResponse(
        token=token,
        user_id=user_id,
        role=payload.role
    )
