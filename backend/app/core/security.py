"""Security, JWT verification, and authentication dependencies."""

import uuid
from typing import Any, Dict, Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import logger

security_bearer = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    """Authenticated user context extracted from validated JWT claims."""
    id: uuid.UUID = Field(..., description="User unique UUID (sub claim)")
    email: Optional[str] = Field(default=None, description="User email address")
    role: str = Field(default="authenticated", description="User role (e.g. authenticated, service_role)")
    raw_claims: Dict[str, Any] = Field(default_factory=dict, description="Raw claims")

    @property
    def is_service_role(self) -> bool:
        return self.role == "service_role" or self.raw_claims.get("role") == "service_role"

    @property
    def is_admin(self) -> bool:
        app_metadata = self.raw_claims.get("app_metadata", {})
        return (
            self.is_service_role
            or app_metadata.get("role") == "admin"
            or app_metadata.get("claims_admin") is True
        )


def verify_jwt_token(token: str) -> Dict[str, Any]:
    """
    Cryptographically verifies the JWT signature and required claims.
    Rejects expired tokens, invalid signatures, or missing subject claims.
    """
    try:
        # Verify using configured secret with HS256
        # When using asymmetric keys in production Supabase, settings can provide JWKS / RS256
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience=["authenticated", "anon", "service_role"],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "require": ["exp", "sub"]
            }
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"Token expired\""}
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token signature or claims.",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""}
        )


def create_access_token_for_user(
    user_id: uuid.UUID,
    email: str = "user@taskforge.dev",
    role: str = "authenticated",
    expires_in_seconds: int = 3600,
    custom_claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    Helper utility for tests and internal token generation matching Supabase Auth JWT schema.
    """
    import time
    now = int(time.time())
    claims = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "aud": "authenticated",
        "iat": now,
        "exp": now + expires_in_seconds,
        "app_metadata": {"provider": "email", "role": role},
        "user_metadata": {}
    }
    if custom_claims:
        claims.update(custom_claims)

    return jwt.encode(claims, settings.supabase_jwt_secret, algorithm="HS256")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
) -> AuthenticatedUser:
    """
    FastAPI dependency requiring a valid Bearer token.
    Raises HTTP 401 if token is missing, expired, or invalid.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    claims = verify_jwt_token(credentials.credentials)

    sub = claims.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject identifier."
        )

    try:
        user_uuid = uuid.UUID(sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid subject UUID in token."
        )

    return AuthenticatedUser(
        id=user_uuid,
        email=claims.get("email"),
        role=claims.get("role", "authenticated"),
        raw_claims=claims
    )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
) -> Optional[AuthenticatedUser]:
    """FastAPI dependency for endpoints with optional authentication."""
    if not credentials or not credentials.credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


async def require_admin(
    user: AuthenticatedUser = Depends(get_current_user)
) -> AuthenticatedUser:
    """Dependency verifying the caller has administrative or service_role privileges."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires administrative privileges."
        )
    return user
