"""FastAPI main application entry point."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from src.api.routes import api_router
from src.core.config import settings
from src.core.exceptions import TLDRException
from src.core.logging import api_logger, setup_logging
from src.core.middleware import (
    CORSMiddleware,
    GlobalExceptionHandler,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan events."""
    # Startup
    api_logger.info("Starting TLDR API application")

    # Setup logging
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_format = os.getenv("LOG_FORMAT", "json")
    setup_logging(log_level=log_level, log_format=log_format)

    api_logger.info("Application startup complete")

    yield

    # Shutdown
    api_logger.info("Shutting down TLDR API application")


app = FastAPI(
    title="TLDR - AI Meeting Summarization Tool",
    description="""
    Transform meeting transcripts into actionable summaries with AI.

    ## Features

    * **Upload Transcripts**: Support for text and audio file uploads
    * **AI Processing**: Extract action items, decisions, and key topics
    * **Multiple Formats**: Export summaries as JSON, Markdown, or PDF
    * **Real-time Status**: Track processing progress
    * **Bulk Operations**: Process multiple meetings at once

    ## Quick Start

    1. Upload a transcript using `/api/v1/transcripts/upload`
    2. Start processing with `/api/v1/transcripts/process`
    3. Check status with `/api/v1/transcripts/{meeting_id}/status`
    4. Retrieve summary with `/api/v1/summaries/{meeting_id}`
    5. Export in your preferred format with `/api/v1/summaries/export`
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add middleware in the correct order (LIFO - Last In, First Out)

# 1. Security headers (applied last, closest to response)
app.add_middleware(SecurityHeadersMiddleware)

# 2. Custom CORS middleware (replaces FastAPI's built-in)
app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, "allowed_origins", ["*"]),
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "Accept",
        "Origin",
        "User-Agent",
    ],
    expose_headers=["X-Request-ID"],
    allow_credentials=False,
    max_age=600,
)

# 3. Request logging (applied first, closest to request)
app.add_middleware(RequestLoggingMiddleware)

# Exception handlers
global_exception_handler = GlobalExceptionHandler()

# Register exception handlers
app.add_exception_handler(TLDRException, global_exception_handler)
app.add_exception_handler(RequestValidationError, global_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint providing API information."""
    return {
        "message": "TLDR - AI Meeting Summarization Tool",
        "version": "1.0.0",
        "status": "operational",
        "documentation": {"swagger_ui": "/docs", "redoc": "/redoc"},
        "api": {
            "base_url": "/api/v1",
            "health_check": "/api/v1/health",
            "endpoints": {
                "transcripts": "/api/v1/transcripts",
                "summaries": "/api/v1/summaries",
            },
        },
    }


@app.get("/health")
async def health_check():
    """Basic health check endpoint (legacy)."""
    return {
        "status": "healthy",
        "service": "tldr-api",
        "message": "Use /api/v1/health for detailed health information",
    }


if __name__ == "__main__":
    import uvicorn

    # Development server configuration
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        reload_dirs=["src"],
    )
