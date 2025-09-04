"""Structured logging configuration for the TLDR application."""

import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from pythonjsonlogger import jsonlogger

# Context variable to store request ID across async operations
request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    """Filter to add request ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add request ID to log record if available."""
        record.request_id = request_id_context.get() or "no-request-id"
        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        """Add custom fields to the log record."""
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO format
        log_record["timestamp"] = datetime.now(UTC).isoformat()

        # Add application info
        log_record["application"] = "tldr"
        log_record["version"] = "1.0.0"

        # Add level name
        log_record["level"] = record.levelname

        # Add request ID if available
        log_record["request_id"] = getattr(record, "request_id", "no-request-id")

        # Add module and function info
        log_record["module"] = record.module
        log_record["function"] = record.funcName

        # Ensure message is always present
        if "message" not in log_record:
            log_record["message"] = record.getMessage()


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> logging.Logger:
    """
    Set up structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log format ("json" or "text")

    Returns:
        Configured logger instance
    """
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers to avoid duplication
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)

    # Set up formatter based on format preference
    if log_format.lower() == "json":
        formatter = CustomJsonFormatter(
            fmt="%(timestamp)s %(level)s %(name)s %(message)s"
        )
    else:
        # Text format for development
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(request_id)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)

    # Add request ID filter
    console_handler.addFilter(RequestIdFilter())

    # Add handler to logger
    logger.addHandler(console_handler)

    # Set specific log levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def set_request_id(request_id: str | None = None) -> str:
    """
    Set request ID in context for request tracing.

    Args:
        request_id: Custom request ID or None to generate one

    Returns:
        The request ID that was set
    """
    if request_id is None:
        request_id = str(uuid.uuid4())

    request_id_context.set(request_id)
    return request_id


def get_request_id() -> str | None:
    """
    Get current request ID from context.

    Returns:
        Current request ID or None if not set
    """
    return request_id_context.get()


def clear_request_id() -> None:
    """Clear request ID from context."""
    request_id_context.set(None)


class StructuredLogger:
    """Wrapper for structured logging with additional context."""

    def __init__(self, name: str):
        self.logger = get_logger(name)

    def _log_with_context(self, level: int, message: str, **kwargs: Any) -> None:
        """Log message with additional context."""
        extra = {"extra_data": kwargs} if kwargs else {}

        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._log_with_context(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._log_with_context(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._log_with_context(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self._log_with_context(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message."""
        self._log_with_context(logging.CRITICAL, message, **kwargs)

    def log_api_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        **kwargs: Any,
    ) -> None:
        """Log API request with structured data."""
        self.info(
            f"{method} {path} - {status_code}",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
            **kwargs,
        )

    def log_processing_start(
        self, meeting_id: str, processing_type: str, **kwargs: Any
    ) -> None:
        """Log processing start."""
        self.info(
            f"Processing started: {processing_type} for meeting {meeting_id}",
            event_type="processing_start",
            meeting_id=meeting_id,
            processing_type=processing_type,
            **kwargs,
        )

    def log_processing_complete(
        self,
        meeting_id: str,
        processing_type: str,
        duration_seconds: float,
        **kwargs: Any,
    ) -> None:
        """Log processing completion."""
        self.info(
            f"Processing completed: {processing_type} for meeting {meeting_id}",
            event_type="processing_complete",
            meeting_id=meeting_id,
            processing_type=processing_type,
            duration_seconds=round(duration_seconds, 2),
            **kwargs,
        )

    def log_processing_error(
        self, meeting_id: str, processing_type: str, error: str, **kwargs: Any
    ) -> None:
        """Log processing error."""
        self.error(
            f"Processing failed: {processing_type} for meeting {meeting_id} - {error}",
            event_type="processing_error",
            meeting_id=meeting_id,
            processing_type=processing_type,
            error=error,
            **kwargs,
        )

    def log_external_service_call(
        self,
        service_name: str,
        operation: str,
        duration_ms: float,
        success: bool,
        **kwargs: Any,
    ) -> None:
        """Log external service call."""
        level = logging.INFO if success else logging.ERROR
        status = "success" if success else "failure"

        self.logger.log(
            level,
            f"External service call: {service_name}.{operation} - {status}",
            extra={
                "extra_data": {
                    "event_type": "external_service_call",
                    "service_name": service_name,
                    "operation": operation,
                    "duration_ms": round(duration_ms, 2),
                    "success": success,
                    **kwargs,
                }
            },
        )


# Pre-configured logger instances for common use cases
api_logger = StructuredLogger("tldr.api")
processing_logger = StructuredLogger("tldr.processing")
service_logger = StructuredLogger("tldr.service")
db_logger = StructuredLogger("tldr.database")
