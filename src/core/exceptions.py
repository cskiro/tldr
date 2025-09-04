"""Custom exceptions for the TLDR application."""

from typing import Any

from fastapi import HTTPException


class TLDRException(Exception):
    """Base exception class for TLDR application."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class MeetingNotFoundError(TLDRException):
    """Exception raised when a meeting is not found."""

    def __init__(self, meeting_id: str):
        self.meeting_id = meeting_id
        message = f"Meeting '{meeting_id}' not found"
        super().__init__(
            message=message,
            status_code=404,
            error_code="MEETING_NOT_FOUND",
            details={"meeting_id": meeting_id},
        )


class DuplicateMeetingError(TLDRException):
    """Exception raised when attempting to create a duplicate meeting."""

    def __init__(self, meeting_id: str):
        self.meeting_id = meeting_id
        message = f"Meeting '{meeting_id}' already exists"
        super().__init__(
            message=message,
            status_code=409,
            error_code="DUPLICATE_MEETING",
            details={"meeting_id": meeting_id},
        )


class ProcessingError(TLDRException):
    """Exception raised during transcript processing."""

    def __init__(
        self,
        meeting_id: str,
        stage: str,
        details: str,
        original_error: Exception | None = None,
    ):
        self.meeting_id = meeting_id
        self.stage = stage
        self.processing_details = details
        self.original_error = original_error

        message = f"Processing failed for meeting '{meeting_id}' at stage '{stage}': {details}"
        super().__init__(
            message=message,
            status_code=500,
            error_code="PROCESSING_ERROR",
            details={
                "meeting_id": meeting_id,
                "stage": stage,
                "details": details,
                "original_error": str(original_error) if original_error else None,
            },
        )


class ValidationError(TLDRException):
    """Exception raised for validation errors."""

    def __init__(self, field_errors: dict[str, str], message: str | None = None):
        self.field_errors = field_errors

        if message is None:
            error_details = ", ".join(
                [f"{field}: {error}" for field, error in field_errors.items()]
            )
            message = f"Validation failed: {error_details}"

        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details={"field_errors": field_errors},
        )


class FileTooLargeError(TLDRException):
    """Exception raised when uploaded file exceeds size limits."""

    def __init__(self, actual_size: int, max_size: int):
        self.actual_size = actual_size
        self.max_size = max_size

        def format_size(size_bytes: int) -> str:
            """Format size in bytes to human readable format."""
            for unit in ["B", "KB", "MB", "GB"]:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.1f}{unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.1f}TB"

        message = (
            f"File size {format_size(actual_size)} exceeds maximum allowed size "
            f"of {format_size(max_size)}"
        )

        super().__init__(
            message=message,
            status_code=413,
            error_code="FILE_TOO_LARGE",
            details={
                "actual_size": actual_size,
                "max_size": max_size,
                "actual_size_formatted": format_size(actual_size),
                "max_size_formatted": format_size(max_size),
            },
        )


class UnsupportedFormatError(TLDRException):
    """Exception raised when file format is not supported."""

    def __init__(self, format_type: str, supported_formats: list[str]):
        self.format_type = format_type
        self.supported_formats = supported_formats

        message = (
            f"Unsupported format '{format_type}'. "
            f"Supported formats: {', '.join(supported_formats)}"
        )

        super().__init__(
            message=message,
            status_code=422,
            error_code="UNSUPPORTED_FORMAT",
            details={
                "format_type": format_type,
                "supported_formats": supported_formats,
            },
        )


class ExternalServiceError(TLDRException):
    """Exception raised when external service calls fail."""

    def __init__(self, service_name: str, service_error: str, status_code: int = 502):
        self.service_name = service_name
        self.service_error = service_error

        message = f"External service '{service_name}' error: {service_error}"

        super().__init__(
            message=message,
            status_code=status_code,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service_name": service_name, "service_error": service_error},
        )


class DatabaseError(TLDRException):
    """Exception raised for database operation failures."""

    def __init__(
        self, operation: str, details: str, original_error: Exception | None = None
    ):
        self.operation = operation
        self.db_details = details
        self.original_error = original_error

        message = f"Database operation '{operation}' failed: {details}"

        super().__init__(
            message=message,
            status_code=500,
            error_code="DATABASE_ERROR",
            details={
                "operation": operation,
                "details": details,
                "original_error": str(original_error) if original_error else None,
            },
        )


class RateLimitError(TLDRException):
    """Exception raised when rate limits are exceeded."""

    def __init__(self, limit: int, window_seconds: int, retry_after: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self.retry_after = retry_after

        message = (
            f"Rate limit exceeded: {limit} requests per {window_seconds} seconds. "
            f"Try again in {retry_after} seconds."
        )

        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details={
                "limit": limit,
                "window_seconds": window_seconds,
                "retry_after": retry_after,
            },
        )


class AuthenticationError(TLDRException):
    """Exception raised for authentication failures."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message, status_code=401, error_code="AUTHENTICATION_ERROR"
        )


class AuthorizationError(TLDRException):
    """Exception raised for authorization failures."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message, status_code=403, error_code="AUTHORIZATION_ERROR"
        )


def to_http_exception(tldr_exception: TLDRException) -> HTTPException:
    """Convert TLDRException to FastAPI HTTPException."""
    return HTTPException(
        status_code=tldr_exception.status_code,
        detail={
            "success": False,
            "error_code": tldr_exception.error_code,
            "message": tldr_exception.message,
            "details": tldr_exception.details,
        },
    )
