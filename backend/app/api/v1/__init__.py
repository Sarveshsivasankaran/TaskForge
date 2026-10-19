"""API v1 router assembly."""

from fastapi import APIRouter
from app.api.v1.health import router as health_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)

# Also expose un-versioned /api/health as specified in requirements
api_root_router = APIRouter(prefix="/api")
api_root_router.include_router(health_router)
