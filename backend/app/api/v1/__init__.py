"""API v1 router assembly."""

from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.admin import router as admin_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(metrics_router)
api_v1_router.include_router(admin_router)

# Also expose un-versioned /api routes
api_root_router = APIRouter(prefix="/api")
api_root_router.include_router(health_router)
api_root_router.include_router(auth_router)
api_root_router.include_router(jobs_router)
api_root_router.include_router(metrics_router)
api_root_router.include_router(admin_router)

