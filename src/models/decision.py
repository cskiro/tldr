"""Decision model for meeting decisions and outcomes."""

from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import Field, field_validator

from .base import BaseModelWithConfig, TimestampedModel


class DecisionStatus(str, Enum):
    """Status of a decision."""
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    IMPLEMENTED = "implemented"


class DecisionImpact(str, Enum):
    """Impact level of a decision."""
    LOW = "low"          # Minor operational changes
    MEDIUM = "medium"    # Affects team or department
    HIGH = "high"        # Affects multiple teams
    CRITICAL = "critical" # Company-wide impact


class Decision(TimestampedModel):
    """Decision made during a meeting."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the decision"
    )

    decision: Annotated[str, Field(
        min_length=5,
        max_length=1000,
        description="The decision that was made",
        json_schema_extra={"example": "Adopt React for the new frontend project"}
    )]

    made_by: Annotated[str, Field(
        min_length=1,
        max_length=100,
        description="Person who made or announced the decision",
        json_schema_extra={"example": "Sarah Chen (CTO)"}
    )]

    rationale: Annotated[str, Field(
        min_length=5,
        max_length=2000,
        description="Reasoning behind the decision",
        json_schema_extra={"example": "React has better team expertise and component reusability"}
    )]

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the decision was made during the meeting",
        json_schema_extra={"example": "2025-01-15T10:30:00Z"}
    )

    status: DecisionStatus = Field(
        default=DecisionStatus.APPROVED,
        description="Current status of the decision"
    )

    impact: DecisionImpact = Field(
        default=DecisionImpact.MEDIUM,
        description="Expected impact level of the decision"
    )

    affected_teams: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Teams or departments affected by this decision",
        json_schema_extra={"example": ["Frontend Team", "Product Team", "QA Team"]}
    )

    alternatives_considered: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Alternative options that were discussed",
        json_schema_extra={"example": ["Vue.js", "Angular", "Svelte"]}
    )

    implementation_date: datetime | None = Field(
        default=None,
        description="Target date for implementing the decision",
        json_schema_extra={"example": "2025-02-01T00:00:00Z"}
    )

    review_date: datetime | None = Field(
        default=None,
        description="Date to review the effectiveness of the decision",
        json_schema_extra={"example": "2025-04-01T00:00:00Z"}
    )

    context: str = Field(
        default="",
        max_length=1500,
        description="Additional context or background for the decision"
    )

    tags: list[str] = Field(
        default_factory=list,
        max_length=15,
        description="Tags for categorizing the decision",
        json_schema_extra={"example": ["technology", "frontend", "architecture"]}
    )

    confidence_level: Annotated[float, Field(
        ge=0.0,
        le=1.0,
        description="Confidence level in the decision (0.0 to 1.0)",
        json_schema_extra={"example": 0.8}
    )] = 0.5

    dependencies: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Dependencies or prerequisites for implementing the decision",
        json_schema_extra={"example": ["Team training", "Library evaluation", "Migration plan"]}
    )

    @field_validator("made_by")
    @classmethod
    def validate_made_by(cls, v: str) -> str:
        """Validate and clean decision maker name."""
        v = v.strip()
        if not v:
            raise ValueError("Decision maker cannot be empty")

        # Allow names with titles/roles in parentheses
        import re
        if not re.match(r"^[a-zA-Z\s\-'\.()]+$", v):
            raise ValueError("Decision maker name contains invalid characters")

        return v

    @field_validator("affected_teams", "alternatives_considered", "tags", "dependencies")
    @classmethod
    def validate_string_lists(cls, v: list[str]) -> list[str]:
        """Validate and clean string lists."""
        cleaned_items = []
        seen = set()
        for item in v:
            item = item.strip()
            if item and len(item) >= 2:
                # Case-insensitive deduplication
                item_lower = item.lower()
                if item_lower not in seen:
                    seen.add(item_lower)
                    cleaned_items.append(item)
        return cleaned_items

    @field_validator("implementation_date", "review_date")
    @classmethod
    def validate_future_dates(cls, v: datetime | None) -> datetime | None:
        """Ensure dates are not in the past."""
        if v is not None and v < datetime.now(UTC) - timedelta(seconds=1):
            raise ValueError("Implementation and review dates cannot be in the past")
        return v

    def mark_implemented(self) -> None:
        """Mark the decision as implemented."""
        self.status = DecisionStatus.IMPLEMENTED
        if self.implementation_date is None:
            self.implementation_date = datetime.now(UTC)
        self.mark_updated()

    def mark_deferred(self, new_review_date: datetime | None = None) -> None:
        """Mark the decision as deferred."""
        self.status = DecisionStatus.DEFERRED
        if new_review_date:
            self.review_date = new_review_date
        self.mark_updated()

    def is_due_for_review(self) -> bool:
        """Check if the decision is due for review."""
        if self.review_date is None:
            return False
        return datetime.now(UTC) >= self.review_date

    def days_until_implementation(self) -> int | None:
        """Calculate days until implementation date."""
        if self.implementation_date is None:
            return None

        delta = self.implementation_date - datetime.now(UTC)
        return delta.days


class DecisionUpdate(BaseModelWithConfig):
    """Model for updating decision fields."""

    decision: Annotated[str | None, Field(
        None,
        min_length=5,
        max_length=1000,
        description="Updated decision text"
    )] = None

    rationale: Annotated[str | None, Field(
        None,
        min_length=5,
        max_length=2000,
        description="Updated rationale"
    )] = None

    status: DecisionStatus | None = None
    impact: DecisionImpact | None = None
    affected_teams: list[str] | None = None
    alternatives_considered: list[str] | None = None
    implementation_date: datetime | None = None
    review_date: datetime | None = None
    context: Annotated[str | None, Field(None, max_length=1500)] = None
    tags: list[str] | None = None
    confidence_level: Annotated[float | None, Field(None, ge=0.0, le=1.0)] = None
    dependencies: list[str] | None = None
