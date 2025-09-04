"""Transcript and meeting models."""

from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Annotated, Any
from uuid import UUID, uuid4

from pydantic import Field, computed_field, field_validator

from .action_item import ActionItem
from .base import BaseModelWithConfig, TimestampedModel
from .decision import Decision


class TranscriptStatus(str, Enum):
    """Status of transcript processing."""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MeetingType(str, Enum):
    """Type of meeting."""
    STANDUP = "standup"
    PLANNING = "planning"
    RETROSPECTIVE = "retrospective"
    ONE_ON_ONE = "one_on_one"
    ALL_HANDS = "all_hands"
    CLIENT_CALL = "client_call"
    INTERVIEW = "interview"
    OTHER = "other"


class TranscriptInput(BaseModelWithConfig):
    """Input model for meeting transcript data."""

    meeting_id: Annotated[str, Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Unique identifier for the meeting",
        json_schema_extra={"example": "standup_2025_01_15_team_alpha"}
    )]

    raw_text: Annotated[str | None, Field(
        None,
        min_length=10,
        max_length=100000,
        description="Raw transcript text content",
        json_schema_extra={"example": "John: Good morning everyone. Let's start..."}
    )]

    audio_url: Annotated[str | None, Field(
        None,
        pattern=r"^https?://.*\.(mp3|mp4|wav|m4a)$",
        description="URL to audio/video file for transcription",
        json_schema_extra={"example": "https://example.com/meeting.mp3"}
    )]

    participants: Annotated[list[str], Field(
        min_length=1,
        max_length=50,
        description="List of meeting participants",
        json_schema_extra={"example": ["Alice Smith", "Bob Johnson", "Carol Lee"]}
    )]

    duration_minutes: Annotated[int, Field(
        gt=0,
        le=480,  # Max 8 hours
        description="Meeting duration in minutes",
        json_schema_extra={"example": 60}
    )]

    meeting_date: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Date and time when the meeting occurred",
        json_schema_extra={"example": "2025-01-15T10:00:00Z"}
    )

    meeting_type: MeetingType = Field(
        default=MeetingType.OTHER,
        description="Type/category of the meeting"
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the meeting",
        json_schema_extra={"example": {"platform": "zoom", "recording_id": "123456"}}
    )

    @field_validator("participants")
    @classmethod
    def validate_participants(cls, v: list[str]) -> list[str]:
        """Validate participant names."""
        if not v:
            raise ValueError("At least one participant is required")

        # Remove duplicates while preserving order
        seen = set()
        unique_participants = []
        for participant in v:
            participant = participant.strip()
            if participant and participant.lower() not in seen:
                seen.add(participant.lower())
                unique_participants.append(participant)

        if not unique_participants:
            raise ValueError("At least one valid participant is required")

        return unique_participants

    @field_validator("raw_text")
    @classmethod
    def validate_content_source(cls, v: str | None, info) -> str | None:
        """Ensure at least one content source is provided."""
        # Only validate when both fields are processed
        if hasattr(info, 'data') and 'audio_url' in info.data:
            if v is None and info.data.get("audio_url") is None:
                raise ValueError("Either raw_text or audio_url must be provided")
        return v


class MeetingSummary(TimestampedModel):
    """Complete meeting summary with extracted information."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the summary"
    )

    meeting_id: str = Field(
        description="Reference to the original meeting"
    )

    summary: Annotated[str, Field(
        min_length=10,
        max_length=5000,
        description="Executive summary of the meeting",
        json_schema_extra={"example": "Team discussed Q1 objectives and project timelines..."}
    )]

    key_topics: Annotated[list[str], Field(
        min_length=1,
        max_length=20,
        description="Main topics discussed in the meeting",
        json_schema_extra={"example": ["Q1 Planning", "Budget Review", "Team Capacity"]}
    )]

    decisions: list[Decision] = Field(
        default_factory=list,
        description="Decisions made during the meeting"
    )

    action_items: list[ActionItem] = Field(
        default_factory=list,
        description="Action items extracted from the meeting"
    )

    participants: list[str] = Field(
        description="Meeting participants"
    )

    sentiment: Annotated[str, Field(
        pattern=r"^(positive|neutral|negative)$",
        description="Overall sentiment of the meeting",
        json_schema_extra={"example": "positive"}
    )] = "neutral"

    next_steps: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Identified next steps and follow-ups",
        json_schema_extra={"example": ["Schedule follow-up meeting", "Review budget proposal"]}
    )

    confidence_score: Annotated[float, Field(
        ge=0.0,
        le=1.0,
        description="AI confidence score for the summary quality",
        json_schema_extra={"example": 0.85}
    )] = 0.0

    processing_time_seconds: Annotated[float, Field(
        ge=0.0,
        description="Time taken to process the transcript",
        json_schema_extra={"example": 12.5}
    )] = 0.0

    @computed_field
    @property
    def total_items(self) -> int:
        """Total number of action items and decisions."""
        return len(self.action_items) + len(self.decisions)

    @computed_field
    @property
    def completion_percentage(self) -> float:
        """Percentage of action items that are completed."""
        if not self.action_items:
            return 100.0

        completed = sum(1 for item in self.action_items if item.status == "completed")
        return (completed / len(self.action_items)) * 100.0


class ProcessingStatus(TimestampedModel):
    """Status tracking for transcript processing."""

    meeting_id: str = Field(description="Meeting identifier")
    status: TranscriptStatus = Field(description="Current processing status")
    progress_percentage: Annotated[int, Field(ge=0, le=100)] = 0
    error_message: str | None = Field(default=None, description="Error message if processing failed")
    estimated_completion: datetime | None = Field(default=None, description="Estimated completion time")

    def mark_processing(self, estimated_seconds: int = 60) -> None:
        """Mark as processing with estimated completion time."""
        self.status = TranscriptStatus.PROCESSING
        self.estimated_completion = datetime.now(UTC).replace(
            microsecond=0
        ) + timedelta(seconds=estimated_seconds)
        self.mark_updated()

    def mark_completed(self) -> None:
        """Mark as completed."""
        self.status = TranscriptStatus.COMPLETED
        self.progress_percentage = 100
        self.mark_updated()

    def mark_failed(self, error: str) -> None:
        """Mark as failed with error message."""
        self.status = TranscriptStatus.FAILED
        self.error_message = error
        self.mark_updated()
