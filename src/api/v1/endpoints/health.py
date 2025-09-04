"""Health check endpoints for monitoring and Kubernetes probes."""

import time
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.models.base import APIResponse

router = APIRouter()

# Application startup time for uptime calculation
_startup_time = time.time()


class HealthCheckResponse(BaseModel):
    """Health check response model."""

    status: str
    timestamp: str
    version: str
    uptime: float
    checks: dict[str, str]


class ReadinessResponse(BaseModel):
    """Readiness probe response model."""

    status: str
    timestamp: str


class LivenessResponse(BaseModel):
    """Liveness probe response model."""

    status: str


async def check_database_connection() -> bool:
    """Check database connectivity.

    TODO: Implement actual database connection check.
    For now, this is a placeholder that returns True.
    """
    # Placeholder - will be implemented with actual database
    return True


async def is_application_initialized() -> bool:
    """Check if application is fully initialized.

    TODO: Implement actual initialization check.
    For now, this is a placeholder that returns True.
    """
    # Placeholder - will check if all services are ready
    return True


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """
    Comprehensive health check endpoint.

    Returns detailed health information including:
    - Overall system status
    - Individual component checks
    - System uptime and version info
    - Timestamp for debugging

    Returns 200 for healthy, 503 for degraded/unhealthy.
    """
    current_time = datetime.now(UTC)
    uptime = time.time() - _startup_time

    # Check individual components
    checks = {}
    overall_healthy = True

    # API check (always healthy if we can respond)
    checks["api"] = "healthy"

    # Database check
    try:
        db_healthy = await check_database_connection()
        checks["database"] = "healthy" if db_healthy else "unhealthy"
        if not db_healthy:
            overall_healthy = False
    except Exception:
        checks["database"] = "unhealthy"
        overall_healthy = False

    # Determine overall status
    status = "healthy" if overall_healthy else "degraded"
    status_code = 200 if overall_healthy else 503

    response_data = HealthCheckResponse(
        status=status,
        timestamp=current_time.isoformat(),
        version="1.0.0",
        uptime=round(uptime, 2),
        checks=checks,
    )

    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=response_data.model_dump())

    return response_data


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_probe() -> ReadinessResponse:
    """
    Kubernetes readiness probe endpoint.

    Checks if the application is ready to receive traffic.
    Returns 200 when ready, 503 when not ready.

    This is used by Kubernetes to determine when to start
    routing traffic to the pod.
    """
    current_time = datetime.now(UTC)

    try:
        # Check if application is fully initialized
        is_ready = await is_application_initialized()

        if is_ready:
            return ReadinessResponse(status="ready", timestamp=current_time.isoformat())
        else:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "not_ready",
                    "timestamp": current_time.isoformat(),
                    "message": "Application is still initializing",
                },
            )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "timestamp": current_time.isoformat(),
                "message": f"Readiness check failed: {str(e)}",
            },
        ) from e


@router.get("/alive", response_model=LivenessResponse)
async def liveness_probe() -> LivenessResponse:
    """
    Kubernetes liveness probe endpoint.

    Lightweight endpoint that simply confirms the application
    process is running and responsive.

    This should be as fast and lightweight as possible.
    Used by Kubernetes to determine if the pod should be restarted.
    """
    return LivenessResponse(status="alive")


@router.get("/")
async def health_root() -> APIResponse:
    """
    Root health endpoint that redirects to main health check.

    Provides a simple way to check if the health endpoints are working.
    """
    return APIResponse.success_response(
        message="Health endpoints are operational",
        data={
            "endpoints": {
                "health": "/health - Comprehensive health check",
                "ready": "/ready - Kubernetes readiness probe",
                "alive": "/alive - Kubernetes liveness probe",
            }
        },
    )
