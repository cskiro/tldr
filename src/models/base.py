"""Base models with shared configuration and utilities."""

from datetime import datetime, timezone
from typing import Any, Dict
from pydantic import BaseModel, ConfigDict, Field


class BaseModelWithConfig(BaseModel):
    """Base model with common configuration for all TLDR models."""
    
    model_config = ConfigDict(
        # Enable validation on assignment
        validate_assignment=True,
        # Strip whitespace from strings
        str_strip_whitespace=True,
        # Use enum values instead of enum objects in JSON
        use_enum_values=True,
        # Validate default values
        validate_default=True,
        # Extra fields are forbidden (strict mode)
        extra="forbid",
        # Enable JSON schema generation
        json_schema_mode_override="serialization",
    )


class TimestampedModel(BaseModelWithConfig):
    """Base model with automatic timestamp tracking."""
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the record was created",
        json_schema_extra={"example": "2025-01-15T10:30:00Z"}
    )
    
    updated_at: datetime | None = Field(
        default=None,
        description="Timestamp when the record was last updated",
        json_schema_extra={"example": "2025-01-15T14:45:00Z"}
    )
    
    def mark_updated(self) -> None:
        """Mark the record as updated with current timestamp."""
        self.updated_at = datetime.now(timezone.utc)


class APIResponse(BaseModelWithConfig):
    """Standard API response wrapper."""
    
    success: bool = Field(description="Whether the request was successful")
    message: str = Field(description="Human-readable message")
    data: Any | None = Field(default=None, description="Response data")
    errors: list[str] | None = Field(default=None, description="List of error messages")
    
    @classmethod
    def success_response(
        cls, 
        data: Any = None, 
        message: str = "Request successful"
    ) -> "APIResponse":
        """Create a success response."""
        return cls(success=True, message=message, data=data)
    
    @classmethod
    def error_response(
        cls, 
        errors: list[str] | str, 
        message: str = "Request failed"
    ) -> "APIResponse":
        """Create an error response."""
        error_list = [errors] if isinstance(errors, str) else errors
        return cls(success=False, message=message, errors=error_list)


class PaginatedResponse(BaseModelWithConfig):
    """Paginated response wrapper."""
    
    items: list[Any] = Field(description="List of items")
    total: int = Field(ge=0, description="Total number of items")
    page: int = Field(ge=1, description="Current page number")
    size: int = Field(ge=1, le=100, description="Items per page")
    pages: int = Field(ge=1, description="Total number of pages")
    
    @classmethod
    def create(
        cls,
        items: list[Any],
        total: int,
        page: int = 1,
        size: int = 20
    ) -> "PaginatedResponse":
        """Create a paginated response."""
        pages = max(1, (total + size - 1) // size)  # Always at least 1 page
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages
        )