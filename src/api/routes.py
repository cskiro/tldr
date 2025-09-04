"""API route definitions."""

from fastapi import APIRouter

# Create main API router
api_router = APIRouter()

# Import and include sub-routers (will be created later)
# from src.transcription.routes import router as transcription_router
# from src.summarization.routes import router as summarization_router

# api_router.include_router(transcription_router, prefix="/transcripts", tags=["transcription"])
# api_router.include_router(summarization_router, prefix="/summaries", tags=["summarization"])

@api_router.get("/")
async def api_root():
    """API root endpoint."""
    return {"message": "TLDR API v1"}