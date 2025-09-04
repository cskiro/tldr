"""Comprehensive tests for ActionItem model."""

from datetime import UTC, datetime, timedelta

import pytest

from src.models.action_item import (
    ActionItem,
    ActionItemPriority,
    ActionItemStatus,
    ActionItemUpdate,
)


class TestActionItem:
    """Test ActionItem model functionality."""

    @pytest.fixture
    def valid_action_item_data(self):
        """Fixture providing valid action item data."""
        return {
            "task": "Complete quarterly budget analysis",
            "assignee": "Alice Johnson",
            "priority": ActionItemPriority.HIGH,
            "context": "Needed for Q1 planning meeting next week",
        }

    @pytest.fixture
    def future_date(self):
        """Fixture providing a future date."""
        return datetime.now(UTC) + timedelta(days=7)

    def test_should_create_action_item_with_valid_data(self, valid_action_item_data):
        """Test creating ActionItem with valid data."""
        action_item = ActionItem(**valid_action_item_data)

        assert action_item.task == valid_action_item_data["task"]
        assert action_item.assignee == valid_action_item_data["assignee"]
        assert action_item.priority == ActionItemPriority.HIGH
        assert action_item.status == ActionItemStatus.PENDING  # default
        assert action_item.context == valid_action_item_data["context"]
        assert action_item.tags == []  # default
        assert action_item.estimated_hours is None  # default
        assert action_item.completed_at is None
        assert action_item.completion_notes == ""

    def test_should_generate_unique_id(self, valid_action_item_data):
        """Test that each ActionItem gets a unique ID."""
        item1 = ActionItem(**valid_action_item_data)
        item2 = ActionItem(**valid_action_item_data)

        assert item1.id != item2.id
        assert str(item1.id)  # Should be valid UUID string

    def test_should_inherit_timestamp_functionality(self, valid_action_item_data):
        """Test that ActionItem inherits timestamp behavior."""
        before = datetime.now(UTC)
        action_item = ActionItem(**valid_action_item_data)
        after = datetime.now(UTC)

        assert before <= action_item.created_at <= after
        assert action_item.updated_at is None

    def test_should_validate_task_length(self, valid_action_item_data):
        """Test task length validation."""
        # Too short
        with pytest.raises(ValueError, match="at least 5 characters"):
            ActionItem(**{**valid_action_item_data, "task": "hi"})

        # Too long
        long_task = "x" * 501
        with pytest.raises(ValueError, match="at most 500 characters"):
            ActionItem(**{**valid_action_item_data, "task": long_task})

        # Valid length
        valid_task = "Complete the analysis report"
        action_item = ActionItem(**{**valid_action_item_data, "task": valid_task})
        assert action_item.task == valid_task

    def test_should_validate_assignee_format(self, valid_action_item_data):
        """Test assignee name validation."""
        # Empty assignee
        with pytest.raises(ValueError, match="Assignee cannot be empty"):
            ActionItem(**{**valid_action_item_data, "assignee": ""})

        # Invalid characters
        with pytest.raises(ValueError, match="invalid characters"):
            ActionItem(**{**valid_action_item_data, "assignee": "Alice@Johnson"})

        # Valid names
        valid_names = [
            "Alice Johnson",
            "Bob O'Connor",
            "Mary-Jane Smith",
            "Dr. Sarah Chen",
        ]

        for name in valid_names:
            action_item = ActionItem(**{**valid_action_item_data, "assignee": name})
            assert action_item.assignee == name

    def test_should_validate_due_date_not_in_past(self, valid_action_item_data):
        """Test that due date cannot be in the past."""
        past_date = datetime.now(UTC) - timedelta(days=1)

        with pytest.raises(ValueError, match="Due date cannot be in the past"):
            ActionItem(**{**valid_action_item_data, "due_date": past_date})

    def test_should_accept_future_due_date(self, valid_action_item_data, future_date):
        """Test that future due dates are accepted."""
        action_item = ActionItem(**{**valid_action_item_data, "due_date": future_date})
        assert action_item.due_date == future_date

    def test_should_validate_and_clean_tags(self, valid_action_item_data):
        """Test tag validation and cleaning."""
        tags = ["  Budget  ", "QUARTERLY", "budget", "analysis", "x"]
        action_item = ActionItem(**{**valid_action_item_data, "tags": tags})

        # Should be cleaned: lowercased, stripped, deduplicated, min length
        expected_tags = ["budget", "quarterly", "analysis"]
        assert action_item.tags == expected_tags

    def test_should_validate_estimated_hours(self, valid_action_item_data):
        """Test estimated hours validation."""
        # Too small
        with pytest.raises(ValueError, match="greater than or equal to 0.1"):
            ActionItem(**{**valid_action_item_data, "estimated_hours": 0.05})

        # Too large
        with pytest.raises(ValueError, match="less than or equal to 200"):
            ActionItem(**{**valid_action_item_data, "estimated_hours": 201})

        # Valid hours
        action_item = ActionItem(**{**valid_action_item_data, "estimated_hours": 4.5})
        assert action_item.estimated_hours == 4.5

    def test_should_mark_completed_correctly(self, valid_action_item_data):
        """Test marking action item as completed."""
        action_item = ActionItem(**valid_action_item_data)
        notes = "Finished ahead of schedule"

        before = datetime.now(UTC)
        action_item.mark_completed(notes)
        after = datetime.now(UTC)

        assert action_item.status == ActionItemStatus.COMPLETED
        assert before <= action_item.completed_at <= after
        assert action_item.completion_notes == notes
        assert action_item.updated_at is not None

    def test_should_mark_in_progress_correctly(self, valid_action_item_data):
        """Test marking action item as in progress."""
        action_item = ActionItem(**valid_action_item_data)

        action_item.mark_in_progress()

        assert action_item.status == ActionItemStatus.IN_PROGRESS
        assert action_item.updated_at is not None

    def test_should_mark_blocked_correctly(self, valid_action_item_data):
        """Test marking action item as blocked."""
        action_item = ActionItem(**valid_action_item_data)

        action_item.mark_blocked()

        assert action_item.status == ActionItemStatus.BLOCKED
        assert action_item.updated_at is not None

    def test_should_detect_overdue_items(self, valid_action_item_data):
        """Test overdue detection."""
        past_due = datetime.now(UTC) - timedelta(hours=1)
        future_due = datetime.now(UTC) + timedelta(days=1)

        # Overdue item
        overdue_item = ActionItem(**{**valid_action_item_data, "due_date": past_due})
        overdue_item.due_date = past_due  # Set after creation to bypass validation
        assert overdue_item.is_overdue() is True

        # Not overdue
        future_item = ActionItem(**{**valid_action_item_data, "due_date": future_due})
        assert future_item.is_overdue() is False

        # No due date
        no_date_item = ActionItem(**valid_action_item_data)
        assert no_date_item.is_overdue() is False

        # Completed item (not overdue even if past due date)
        completed_item = ActionItem(**{**valid_action_item_data, "due_date": past_due})
        completed_item.due_date = past_due
        completed_item.mark_completed()
        assert completed_item.is_overdue() is False

    def test_should_calculate_days_until_due(self, valid_action_item_data):
        """Test days until due date calculation."""
        # Future date
        future_date = datetime.now(UTC) + timedelta(days=5)
        future_item = ActionItem(**{**valid_action_item_data, "due_date": future_date})
        assert future_item.days_until_due() == 5

        # Past date (negative days)
        past_date = datetime.now(UTC) - timedelta(days=2)
        past_item = ActionItem(**valid_action_item_data)
        past_item.due_date = past_date
        assert past_item.days_until_due() == -2

        # No due date
        no_date_item = ActionItem(**valid_action_item_data)
        assert no_date_item.days_until_due() is None

    def test_should_serialize_correctly(self, valid_action_item_data, future_date):
        """Test ActionItem serialization."""
        action_item = ActionItem(**{
            **valid_action_item_data,
            "due_date": future_date,
            "tags": ["budget", "quarterly"],
            "estimated_hours": 5.5,
        })

        data = action_item.model_dump()

        # Check key fields are present
        assert data["task"] == valid_action_item_data["task"]
        assert data["assignee"] == valid_action_item_data["assignee"]
        assert data["priority"] == "high"  # Enum value
        assert data["status"] == "pending"  # Enum value
        assert data["tags"] == ["budget", "quarterly"]
        assert data["estimated_hours"] == 5.5
        assert "id" in data
        assert "created_at" in data

    def test_should_handle_all_enum_values(self, valid_action_item_data):
        """Test that all enum values work correctly."""
        # Test all status values
        for status in ActionItemStatus:
            action_item = ActionItem(**{**valid_action_item_data, "status": status})
            assert action_item.status == status

        # Test all priority values
        for priority in ActionItemPriority:
            action_item = ActionItem(**{**valid_action_item_data, "priority": priority})
            assert action_item.priority == priority


class TestActionItemUpdate:
    """Test ActionItemUpdate model functionality."""

    def test_should_create_partial_update(self):
        """Test creating partial update with only some fields."""
        update = ActionItemUpdate(
            task="Updated task description",
            priority=ActionItemPriority.URGENT
        )

        assert update.task == "Updated task description"
        assert update.priority == ActionItemPriority.URGENT
        assert update.assignee is None  # Not provided
        assert update.due_date is None  # Not provided

    def test_should_validate_updated_fields(self):
        """Test that updated fields are validated."""
        # Invalid task length
        with pytest.raises(ValueError, match="at least 5 characters"):
            ActionItemUpdate(task="hi")

        # Invalid assignee
        with pytest.raises(ValueError, match="at least 1 characters"):
            ActionItemUpdate(assignee="")

        # Invalid estimated hours
        with pytest.raises(ValueError, match="greater than or equal to 0.1"):
            ActionItemUpdate(estimated_hours=0.05)

    def test_should_allow_all_none_values(self):
        """Test that update can have all None values."""
        update = ActionItemUpdate()

        assert update.task is None
        assert update.assignee is None
        assert update.due_date is None
        assert update.priority is None
        assert update.status is None

    def test_should_serialize_correctly(self):
        """Test ActionItemUpdate serialization."""
        future_date = datetime.now(UTC) + timedelta(days=3)

        update = ActionItemUpdate(
            task="New task",
            priority=ActionItemPriority.HIGH,
            due_date=future_date,
            tags=["updated", "test"]
        )

        data = update.model_dump()

        assert data["task"] == "New task"
        assert data["priority"] == "high"
        assert data["assignee"] is None
        assert data["tags"] == ["updated", "test"]
