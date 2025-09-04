"""API route definitions."""

from fastapi import APIRouter

from src.api.v1.endpoints import health, summaries, transcripts

# Create main API router
api_router = APIRouter()

# Include v1 endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(
    transcripts.router, prefix="/transcripts", tags=["transcripts"]
)
api_router.include_router(summaries.router, prefix="/summaries", tags=["summaries"])


@api_router.get("/")
async def api_root():
    """API root endpoint."""
    return {
        "message": "TLDR API v1",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/v1/health",
            "transcripts": "/api/v1/transcripts",
            "summaries": "/api/v1/summaries",
        },
    }
