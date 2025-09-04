"""Action item model for meeting tasks and assignments."""

from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import Field, field_validator

from .base import BaseModelWithConfig, TimestampedModel


class ActionItemStatus(str, Enum):
    """Status of an action item."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class ActionItemPriority(str, Enum):
    """Priority level of an action item."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ActionItem(TimestampedModel):
    """Action item extracted from meeting transcripts."""

    id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for the action item"
    )

    task: Annotated[
        str,
        Field(
            min_length=5,
            max_length=500,
            description="Description of the task to be completed",
            json_schema_extra={
                "example": "Prepare quarterly budget review presentation"
            },
        ),
    ]

    assignee: Annotated[
        str,
        Field(
            min_length=1,
            max_length=100,
            description="Person assigned to complete the task",
            json_schema_extra={"example": "Alice Johnson"},
        ),
    ]

    due_date: datetime | None = Field(
        default=None,
        description="When the task should be completed",
        json_schema_extra={"example": "2025-01-20T17:00:00Z"},
    )

    priority: ActionItemPriority = Field(
        default=ActionItemPriority.MEDIUM,
        description="Priority level of the action item",
    )

    status: ActionItemStatus = Field(
        default=ActionItemStatus.PENDING,
        description="Current status of the action item",
    )

    context: Annotated[
        str,
        Field(
            max_length=1000,
            description="Additional context or background for the task",
            json_schema_extra={
                "example": "Discussed during budget planning session. Include Q4 actuals vs forecast."
            },
        ),
    ] = ""

    tags: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Tags for categorizing the action item",
        json_schema_extra={"example": ["budget", "quarterly", "finance"]},
    )

    estimated_hours: Annotated[
        float | None,
        Field(
            None,
            ge=0.1,
            le=200.0,  # Max ~5 weeks
            description="Estimated hours to complete the task",
            json_schema_extra={"example": 4.5},
        ),
    ] = None

    completed_at: datetime | None = Field(
        default=None, description="Timestamp when the task was completed"
    )

    completion_notes: str = Field(
        default="",
        max_length=1000,
        description="Notes added when marking the task as complete",
    )

    @field_validator("assignee")
    @classmethod
    def validate_assignee(cls, v: str) -> str:
        """Validate and clean assignee name."""
        v = v.strip()
        if not v:
            raise ValueError("Assignee cannot be empty")

        # Basic name validation - no special characters except spaces, hyphens, apostrophes
        import re

        if not re.match(r"^[a-zA-Z\s\-'\.]+$", v):
            raise ValueError("Assignee name contains invalid characters")

        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Validate and clean tags."""
        cleaned_tags = []
        for tag in v:
            tag = tag.strip().lower()
            if tag and len(tag) >= 2 and tag not in cleaned_tags:
                cleaned_tags.append(tag)
        return cleaned_tags

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: datetime | None) -> datetime | None:
        """Ensure due date is not in the past."""
        if v is not None and v < datetime.now(UTC) - timedelta(seconds=1):
            raise ValueError("Due date cannot be in the past")
        return v

    def mark_completed(self, notes: str = "") -> None:
        """Mark the action item as completed."""
        self.status = ActionItemStatus.COMPLETED
        self.completed_at = datetime.now(UTC)
        self.completion_notes = notes
        self.mark_updated()

    def mark_in_progress(self) -> None:
        """Mark the action item as in progress."""
        self.status = ActionItemStatus.IN_PROGRESS
        self.mark_updated()

    def mark_blocked(self) -> None:
        """Mark the action item as blocked."""
        self.status = ActionItemStatus.BLOCKED
        self.mark_updated()

    def is_overdue(self) -> bool:
        """Check if the action item is overdue."""
        if self.due_date is None or self.status == ActionItemStatus.COMPLETED:
            return False
        return datetime.now(UTC) > self.due_date

    def days_until_due(self) -> int | None:
        """Calculate days until due date (negative if overdue)."""
        if self.due_date is None:
            return None

        delta = self.due_date - datetime.now(UTC)
        return delta.days


class ActionItemUpdate(BaseModelWithConfig):
    """Model for updating action item fields."""

    task: Annotated[
        str | None,
        Field(
            None, min_length=5, max_length=500, description="Updated task description"
        ),
    ] = None

    assignee: Annotated[
        str | None,
        Field(None, min_length=1, max_length=100, description="Updated assignee"),
    ] = None

    due_date: datetime | None = None
    priority: ActionItemPriority | None = None
    status: ActionItemStatus | None = None
    context: Annotated[str | None, Field(None, max_length=1000)] = None
    tags: list[str] | None = None
    estimated_hours: Annotated[float | None, Field(None, ge=0.1, le=200.0)] = None
    completion_notes: Annotated[str | None, Field(None, max_length=1000)] = None
