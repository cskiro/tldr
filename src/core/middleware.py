"""Middleware for request logging, exception handling, and request tracing."""

import time
import traceback
from collections.abc import Callable

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.exceptions import TLDRException
from src.core.logging import (
    api_logger,
    clear_request_id,
    get_request_id,
    set_request_id,
)
from src.models.base import APIResponse


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests and responses with timing information."""

    def __init__(self, app, _logger_name: str = "tldr.api"):
        super().__init__(app)
        self.logger = api_logger

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        start_time = time.time()

        # Set request ID for tracing
        request_id = request.headers.get("X-Request-ID") or set_request_id()

        # Log request start
        self.logger.info(
            f"Request started: {request.method} {request.url.path}",
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            user_agent=request.headers.get("User-Agent"),
            remote_addr=request.client.host if request.client else None,
            request_id=request_id,
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            self.logger.log_api_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                request_id=request_id,
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as exc:
            # Calculate duration for failed requests
            duration_ms = (time.time() - start_time) * 1000

            # Log error
            self.logger.error(
                f"Request failed: {request.method} {request.url.path}",
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
                error=str(exc),
                error_type=type(exc).__name__,
                request_id=request_id,
            )

            # Re-raise to be handled by exception handler
            raise exc

        finally:
            # Clean up context
            clear_request_id()


class GlobalExceptionHandler:
    """Global exception handler for converting exceptions to API responses."""

    def __init__(self):
        self.logger = api_logger

    async def __call__(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle exceptions and return structured error responses."""
        request_id = get_request_id()

        if isinstance(exc, TLDRException):
            # Handle custom TLDR exceptions
            self.logger.error(
                f"Application error: {exc.error_code}",
                error_code=exc.error_code,
                error_message=exc.message,
                details=exc.details,
                request_id=request_id,
                path=request.url.path,
                method=request.method,
            )

            error_response = APIResponse.error_response(
                errors=[exc.message], message=exc.message
            )

            # Add error-specific fields
            response_data = error_response.model_dump()
            response_data.update(
                {
                    "error_code": exc.error_code,
                    "details": exc.details,
                    "request_id": request_id,
                }
            )

            return JSONResponse(
                status_code=exc.status_code,
                content=response_data,
                headers={"X-Request-ID": request_id} if request_id else {},
            )

        elif isinstance(exc, HTTPException):
            # Handle FastAPI HTTP exceptions
            self.logger.error(
                f"HTTP error: {exc.status_code}",
                status_code=exc.status_code,
                detail=exc.detail,
                request_id=request_id,
                path=request.url.path,
                method=request.method,
            )

            error_response = APIResponse.error_response(
                errors=[str(exc.detail)], message="Request failed"
            )

            response_data = error_response.model_dump()
            response_data.update({"error_code": "HTTP_ERROR", "request_id": request_id})

            return JSONResponse(
                status_code=exc.status_code,
                content=response_data,
                headers={"X-Request-ID": request_id} if request_id else {},
            )

        else:
            # Handle unexpected system exceptions
            error_traceback = traceback.format_exc()

            self.logger.critical(
                f"Unhandled exception: {type(exc).__name__}",
                error_type=type(exc).__name__,
                error_message=str(exc),
                traceback=error_traceback,
                request_id=request_id,
                path=request.url.path,
                method=request.method,
            )

            # Don't expose internal error details to clients
            error_response = APIResponse.error_response(
                errors=["An unexpected error occurred"], message="Internal server error"
            )

            response_data = error_response.model_dump()
            response_data.update(
                {"error_code": "INTERNAL_SERVER_ERROR", "request_id": request_id}
            )

            return JSONResponse(
                status_code=500,
                content=response_data,
                headers={"X-Request-ID": request_id} if request_id else {},
            )


class CORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware with security considerations."""

    def __init__(
        self,
        app,
        allow_origins: list = None,
        allow_methods: list = None,
        allow_headers: list = None,
        expose_headers: list = None,
        allow_credentials: bool = False,
        max_age: int = 600,
    ):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or [
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "OPTIONS",
        ]
        self.allow_headers = allow_headers or [
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "Accept",
            "Origin",
            "User-Agent",
        ]
        self.expose_headers = expose_headers or ["X-Request-ID"]
        self.allow_credentials = allow_credentials
        self.max_age = max_age

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle CORS headers."""
        origin = request.headers.get("Origin")

        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
            self._add_cors_headers(response, origin)
            return response

        # Process actual request
        response = await call_next(request)
        self._add_cors_headers(response, origin)

        return response

    def _add_cors_headers(self, response: Response, origin: str = None):
        """Add CORS headers to response."""
        # Set allowed origin
        if origin and (origin in self.allow_origins or "*" in self.allow_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
        elif "*" in self.allow_origins:
            response.headers["Access-Control-Allow-Origin"] = "*"

        # Set other CORS headers
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
        response.headers["Access-Control-Expose-Headers"] = ", ".join(
            self.expose_headers
        )
        response.headers["Access-Control-Max-Age"] = str(self.max_age)

        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Security headers
        response.headers.update(
            {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Content-Security-Policy": (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline'; "
                    "style-src 'self' 'unsafe-inline'; "
                    "img-src 'self' data:; "
                    "font-src 'self';"
                ),
            }
        )

        return response
