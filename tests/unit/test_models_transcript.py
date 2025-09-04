"""Comprehensive tests for transcript models."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError

from src.models.action_item import ActionItem, ActionItemStatus
from src.models.decision import Decision
from src.models.transcript import (
    MeetingSummary,
    MeetingType,
    ProcessingStatus,
    TranscriptInput,
    TranscriptStatus,
)


class TestTranscriptInput:
    """Test TranscriptInput model functionality."""

    @pytest.fixture
    def valid_transcript_data(self):
        """Fixture providing valid transcript input data."""
        return {
            "meeting_id": "standup_2025_01_15_team_alpha",
            "raw_text": "John: Good morning everyone. Let's discuss our progress...",
            "participants": ["John Smith", "Alice Johnson", "Bob Wilson"],
            "duration_minutes": 30,
            "meeting_type": MeetingType.STANDUP,
        }

    def test_should_create_transcript_with_valid_data(self, valid_transcript_data):
        """Test creating TranscriptInput with valid data."""
        transcript = TranscriptInput(**valid_transcript_data)

        assert transcript.meeting_id == valid_transcript_data["meeting_id"]
        assert transcript.raw_text == valid_transcript_data["raw_text"]
        assert transcript.participants == valid_transcript_data["participants"]
        assert transcript.duration_minutes == valid_transcript_data["duration_minutes"]
        assert transcript.meeting_type == MeetingType.STANDUP
        assert transcript.audio_url is None  # Not provided
        assert transcript.metadata == {}  # Default

    def test_should_set_automatic_meeting_date(self, valid_transcript_data):
        """Test that meeting_date is automatically set."""
        before = datetime.now(UTC)
        transcript = TranscriptInput(**valid_transcript_data)
        after = datetime.now(UTC)

        assert before <= transcript.meeting_date <= after

    def test_should_accept_custom_meeting_date(self, valid_transcript_data):
        """Test that custom meeting_date can be provided."""
        custom_date = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
        transcript = TranscriptInput(
            **{**valid_transcript_data, "meeting_date": custom_date}
        )

        assert transcript.meeting_date == custom_date

    def test_should_validate_meeting_id_format(self, valid_transcript_data):
        """Test meeting ID format validation."""
        # Invalid characters
        with pytest.raises(ValueError, match="String should match pattern"):
            TranscriptInput(
                **{**valid_transcript_data, "meeting_id": "meeting@with#special$chars"}
            )

        # Too short
        with pytest.raises(
            ValidationError, match="String should have at least 1 character"
        ):
            TranscriptInput(**{**valid_transcript_data, "meeting_id": ""})

        # Too long
        long_id = "x" * 101
        with pytest.raises(ValueError, match="at most 100 characters"):
            TranscriptInput(**{**valid_transcript_data, "meeting_id": long_id})

        # Valid formats
        valid_ids = [
            "meeting-123",
            "standup_team_alpha",
            "call_2025-01-15",
            "MEETING123",
        ]

        for meeting_id in valid_ids:
            transcript = TranscriptInput(
                **{**valid_transcript_data, "meeting_id": meeting_id}
            )
            assert transcript.meeting_id == meeting_id

    def test_should_validate_raw_text_length(self, valid_transcript_data):
        """Test raw text length validation."""
        # Too short
        with pytest.raises(ValueError, match="at least 10 characters"):
            TranscriptInput(**{**valid_transcript_data, "raw_text": "Hi there"})

        # Too long
        long_text = "x" * 100001
        with pytest.raises(ValueError, match="at most 100000 characters"):
            TranscriptInput(**{**valid_transcript_data, "raw_text": long_text})

    def test_should_validate_audio_url_format(self, valid_transcript_data):
        """Test audio URL format validation."""
        # Invalid format
        with pytest.raises(ValueError, match="String should match pattern"):
            TranscriptInput(
                **{
                    **valid_transcript_data,
                    "audio_url": "not-a-valid-url",
                    "raw_text": None,
                }
            )

        # Valid URLs
        valid_urls = [
            "https://example.com/meeting.mp3",
            "http://storage.com/audio.wav",
            "https://cdn.com/recording.m4a",
            "https://bucket.s3.com/file.mp4",
        ]

        for url in valid_urls:
            transcript = TranscriptInput(
                **{**valid_transcript_data, "audio_url": url, "raw_text": None}
            )
            assert transcript.audio_url == url

    def test_should_allow_optional_content_source(self, valid_transcript_data):
        """Test that raw_text and audio_url are both optional."""
        # Both fields are optional in the current model
        transcript = TranscriptInput(
            **{**valid_transcript_data, "raw_text": None, "audio_url": None}
        )
        assert transcript.raw_text is None
        assert transcript.audio_url is None

    def test_should_validate_participants_list(self, valid_transcript_data):
        """Test participants list validation."""
        # Empty list
        with pytest.raises(
            ValidationError, match="List should have at least 1 item after validation"
        ):
            TranscriptInput(**{**valid_transcript_data, "participants": []})

        # Too many participants
        too_many = [f"Person {i}" for i in range(51)]
        with pytest.raises(ValueError, match="at most 50 items"):
            TranscriptInput(**{**valid_transcript_data, "participants": too_many})

    def test_should_clean_participants_list(self, valid_transcript_data):
        """Test participants list cleaning."""
        messy_participants = [
            "  John Smith  ",
            "ALICE JOHNSON",
            "alice johnson",  # Duplicate
            "",  # Empty
            "Bob Wilson",
            "   ",  # Whitespace only
        ]

        transcript = TranscriptInput(
            **{**valid_transcript_data, "participants": messy_participants}
        )

        # Should be cleaned: trimmed, deduplicated (case-insensitive), empty removed
        expected = ["John Smith", "ALICE JOHNSON", "Bob Wilson"]
        assert transcript.participants == expected

    def test_should_validate_duration_minutes(self, valid_transcript_data):
        """Test duration validation."""
        # Too short
        with pytest.raises(ValueError, match="greater than 0"):
            TranscriptInput(**{**valid_transcript_data, "duration_minutes": 0})

        # Too long (over 8 hours)
        with pytest.raises(ValueError, match="less than or equal to 480"):
            TranscriptInput(**{**valid_transcript_data, "duration_minutes": 481})

        # Valid durations
        for duration in [1, 60, 240, 480]:
            transcript = TranscriptInput(
                **{**valid_transcript_data, "duration_minutes": duration}
            )
            assert transcript.duration_minutes == duration

    def test_should_handle_all_meeting_types(self, valid_transcript_data):
        """Test that all meeting types work correctly."""
        for meeting_type in MeetingType:
            transcript = TranscriptInput(
                **{**valid_transcript_data, "meeting_type": meeting_type}
            )
            assert transcript.meeting_type == meeting_type

    def test_should_serialize_correctly(self, valid_transcript_data):
        """Test TranscriptInput serialization."""
        transcript = TranscriptInput(
            **{
                **valid_transcript_data,
                "metadata": {"platform": "zoom", "recording_id": "123456"},
            }
        )

        data = transcript.model_dump()

        # Check key fields are present
        assert data["meeting_id"] == valid_transcript_data["meeting_id"]
        assert data["raw_text"] == valid_transcript_data["raw_text"]
        assert data["participants"] == valid_transcript_data["participants"]
        assert data["duration_minutes"] == valid_transcript_data["duration_minutes"]
        assert data["meeting_type"] == "standup"  # Enum value
        assert data["metadata"] == {"platform": "zoom", "recording_id": "123456"}
        assert "meeting_date" in data


class TestMeetingSummary:
    """Test MeetingSummary model functionality."""

    @pytest.fixture
    def sample_action_item(self):
        """Fixture providing a sample action item."""
        return ActionItem(
            task="Complete budget analysis",
            assignee="Alice Johnson",
            status=ActionItemStatus.PENDING,
        )

    @pytest.fixture
    def sample_decision(self):
        """Fixture providing a sample decision."""
        return Decision(
            decision="Use React for frontend",
            made_by="CTO",
            rationale="Better team expertise",
        )

    @pytest.fixture
    def valid_summary_data(self, sample_action_item, sample_decision):
        """Fixture providing valid summary data."""
        return {
            "meeting_id": "standup_123",
            "summary": "Team discussed quarterly goals and project timelines",
            "key_topics": ["Q1 Planning", "Budget Review", "Team Capacity"],
            "participants": ["Alice", "Bob", "Carol"],
            "action_items": [sample_action_item],
            "decisions": [sample_decision],
            "confidence_score": 0.85,
            "processing_time_seconds": 12.5,
        }

    def test_should_create_summary_with_valid_data(self, valid_summary_data):
        """Test creating MeetingSummary with valid data."""
        summary = MeetingSummary(**valid_summary_data)

        assert summary.meeting_id == valid_summary_data["meeting_id"]
        assert summary.summary == valid_summary_data["summary"]
        assert summary.key_topics == valid_summary_data["key_topics"]
        assert summary.participants == valid_summary_data["participants"]
        assert len(summary.action_items) == 1
        assert len(summary.decisions) == 1
        assert summary.confidence_score == 0.85
        assert summary.processing_time_seconds == 12.5
        assert summary.sentiment == "neutral"  # default
        assert summary.next_steps == []  # default

    def test_should_generate_unique_id(self, valid_summary_data):
        """Test that each MeetingSummary gets a unique ID."""
        summary1 = MeetingSummary(**valid_summary_data)
        summary2 = MeetingSummary(**valid_summary_data)

        assert summary1.id != summary2.id
        assert isinstance(summary1.id, UUID)

    def test_should_validate_summary_length(self, valid_summary_data):
        """Test summary text length validation."""
        # Too short
        with pytest.raises(ValueError, match="at least 10 characters"):
            MeetingSummary(**{**valid_summary_data, "summary": "Short"})

        # Too long
        long_summary = "x" * 5001
        with pytest.raises(ValueError, match="at most 5000 characters"):
            MeetingSummary(**{**valid_summary_data, "summary": long_summary})

    def test_should_validate_key_topics(self, valid_summary_data):
        """Test key topics validation."""
        # Too few topics
        with pytest.raises(
            ValidationError, match="List should have at least 1 item after validation"
        ):
            MeetingSummary(**{**valid_summary_data, "key_topics": []})

        # Too many topics
        too_many = [f"Topic {i}" for i in range(21)]
        with pytest.raises(ValueError, match="at most 20 items"):
            MeetingSummary(**{**valid_summary_data, "key_topics": too_many})

    def test_should_validate_sentiment(self, valid_summary_data):
        """Test sentiment validation."""
        # Invalid sentiment
        with pytest.raises(ValueError, match="String should match pattern"):
            MeetingSummary(**{**valid_summary_data, "sentiment": "excited"})

        # Valid sentiments
        for sentiment in ["positive", "neutral", "negative"]:
            summary = MeetingSummary(**{**valid_summary_data, "sentiment": sentiment})
            assert summary.sentiment == sentiment

    def test_should_validate_confidence_score(self, valid_summary_data):
        """Test confidence score validation."""
        # Too low
        with pytest.raises(ValueError, match="greater than or equal to 0"):
            MeetingSummary(**{**valid_summary_data, "confidence_score": -0.1})

        # Too high
        with pytest.raises(ValueError, match="less than or equal to 1"):
            MeetingSummary(**{**valid_summary_data, "confidence_score": 1.1})

        # Valid scores
        for score in [0.0, 0.5, 1.0]:
            summary = MeetingSummary(
                **{**valid_summary_data, "confidence_score": score}
            )
            assert summary.confidence_score == score

    def test_should_validate_processing_time(self, valid_summary_data):
        """Test processing time validation."""
        # Negative time
        with pytest.raises(ValueError, match="greater than or equal to 0"):
            MeetingSummary(**{**valid_summary_data, "processing_time_seconds": -1.0})

        # Valid times
        for time_val in [0.0, 5.5, 120.0]:
            summary = MeetingSummary(
                **{**valid_summary_data, "processing_time_seconds": time_val}
            )
            assert summary.processing_time_seconds == time_val

    def test_should_compute_total_items(self, valid_summary_data):
        """Test total_items computed field."""
        summary = MeetingSummary(**valid_summary_data)

        # 1 action item + 1 decision = 2 total items
        assert summary.total_items == 2

        # Test with no items
        summary_empty = MeetingSummary(
            **{**valid_summary_data, "action_items": [], "decisions": []}
        )
        assert summary_empty.total_items == 0

    def test_should_compute_completion_percentage(
        self, valid_summary_data, sample_action_item
    ):
        """Test completion_percentage computed field."""
        # Test with no action items
        summary_no_items = MeetingSummary(**{**valid_summary_data, "action_items": []})
        assert summary_no_items.completion_percentage == 100.0

        # Test with pending action item
        summary_pending = MeetingSummary(**valid_summary_data)
        assert summary_pending.completion_percentage == 0.0

        # Test with completed action item
        completed_item = ActionItem(
            task="Completed task", assignee="Alice", status=ActionItemStatus.COMPLETED
        )
        summary_completed = MeetingSummary(
            **{
                **valid_summary_data,
                "action_items": [sample_action_item, completed_item],
            }
        )
        assert summary_completed.completion_percentage == 50.0  # 1 of 2 completed


class TestProcessingStatus:
    """Test ProcessingStatus model functionality."""

    @pytest.fixture
    def valid_status_data(self):
        """Fixture providing valid status data."""
        return {
            "meeting_id": "meeting_123",
            "status": TranscriptStatus.UPLOADED,
        }

    def test_should_create_status_with_valid_data(self, valid_status_data):
        """Test creating ProcessingStatus with valid data."""
        status = ProcessingStatus(**valid_status_data)

        assert status.meeting_id == valid_status_data["meeting_id"]
        assert status.status == TranscriptStatus.UPLOADED
        assert status.progress_percentage == 0  # default
        assert status.error_message is None  # default
        assert status.estimated_completion is None  # default

    def test_should_validate_progress_percentage(self, valid_status_data):
        """Test progress percentage validation."""
        # Too low
        with pytest.raises(ValueError, match="greater than or equal to 0"):
            ProcessingStatus(**{**valid_status_data, "progress_percentage": -1})

        # Too high
        with pytest.raises(ValueError, match="less than or equal to 100"):
            ProcessingStatus(**{**valid_status_data, "progress_percentage": 101})

        # Valid percentages
        for percentage in [0, 50, 100]:
            status = ProcessingStatus(
                **{**valid_status_data, "progress_percentage": percentage}
            )
            assert status.progress_percentage == percentage

    def test_should_mark_processing_correctly(self, valid_status_data):
        """Test mark_processing method."""
        status = ProcessingStatus(**valid_status_data)

        before = datetime.now(UTC)
        status.mark_processing(estimated_seconds=120)
        after = datetime.now(UTC)

        assert status.status == TranscriptStatus.PROCESSING
        assert status.updated_at is not None
        assert before <= status.updated_at <= after

        # Check estimated completion time - allow some precision variance
        expected_completion = before + timedelta(seconds=120)
        actual_completion = status.estimated_completion
        # Allow up to 1 second variance due to timing precision
        assert abs((actual_completion - expected_completion).total_seconds()) <= 1

    def test_should_mark_completed_correctly(self, valid_status_data):
        """Test mark_completed method."""
        status = ProcessingStatus(**valid_status_data)

        status.mark_completed()

        assert status.status == TranscriptStatus.COMPLETED
        assert status.progress_percentage == 100
        assert status.updated_at is not None

    def test_should_mark_failed_correctly(self, valid_status_data):
        """Test mark_failed method."""
        status = ProcessingStatus(**valid_status_data)
        error_msg = "Transcription service unavailable"

        status.mark_failed(error_msg)

        assert status.status == TranscriptStatus.FAILED
        assert status.error_message == error_msg
        assert status.updated_at is not None

    def test_should_handle_all_status_values(self, valid_status_data):
        """Test that all transcript status values work correctly."""
        for transcript_status in TranscriptStatus:
            status = ProcessingStatus(
                **{**valid_status_data, "status": transcript_status}
            )
            assert status.status == transcript_status

    def test_should_serialize_correctly(self, valid_status_data):
        """Test ProcessingStatus serialization."""
        status = ProcessingStatus(
            **{
                **valid_status_data,
                "progress_percentage": 75,
                "error_message": "Partial failure",
            }
        )

        data = status.model_dump()

        assert data["meeting_id"] == valid_status_data["meeting_id"]
        assert data["status"] == "uploaded"  # Enum value
        assert data["progress_percentage"] == 75
        assert data["error_message"] == "Partial failure"
        assert "created_at" in data
