"""Authentication Pydantic schemas."""

import uuid
from typing import Optional
from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    """User profile response model."""
    id: uuid.UUID = Field(..., description="User unique identifier")
    email: Optional[str] = Field(default=None, description="User email address")
    role: str = Field(default="authenticated", description="Assigned role")
    is_admin: bool = Field(default=False, description="Administrative status")


class AdminActionResponse(BaseModel):
    """Admin endpoint response."""
    status: str = Field(default="success")
    message: str = Field(default="Admin action authorized.")
    caller_id: uuid.UUID


class DemoTokenRequest(BaseModel):
    """Request schema for dev demo token."""
    user_id: Optional[uuid.UUID] = None
    email: str = "demo@taskforge.dev"
    role: str = "authenticated"


class DemoTokenResponse(BaseModel):
    """Response containing signed JWT access token."""
    token: str
    token_type: str = "bearer"
    user_id: uuid.UUID
    role: str
