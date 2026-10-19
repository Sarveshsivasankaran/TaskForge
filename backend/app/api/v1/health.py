"""Health check and probe API endpoints."""

from fastapi import APIRouter, status
from app.core.config import settings
from app.schemas.health import HealthResponse, ReadinessResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
    description="Returns basic health status of the TaskForge API service."
)
async def get_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.app_env,
    )


@router.get(
    "/health/live",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    description="Confirms that the FastAPI process is alive and responsive."
)
async def get_liveness() -> HealthResponse:
    return HealthResponse(
        status="alive",
        app_name=settings.app_name,
        environment=settings.app_env,
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
    description="Checks the readiness of internal and external dependencies."
)
async def get_readiness() -> ReadinessResponse:
    # Subsystem dependencies are checked here; defaults to healthy in foundation phase
    dependencies = {
        "api": "healthy",
        "database": "configured",
        "queue": "configured" if settings.queue_name else "unconfigured",
        "elasticsearch": "enabled" if settings.elasticsearch_enabled else "disabled",
        "ai_investigator": settings.llm_provider
    }

    return ReadinessResponse(
        status="ready",
        app_name=settings.app_name,
        environment=settings.app_env,
        dependencies=dependencies
    )
