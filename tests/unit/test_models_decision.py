"""Comprehensive tests for Decision model."""

from datetime import UTC, datetime, timedelta

import pytest

from src.models.decision import (
    Decision,
    DecisionImpact,
    DecisionStatus,
    DecisionUpdate,
)


class TestDecision:
    """Test Decision model functionality."""

    @pytest.fixture
    def valid_decision_data(self):
        """Fixture providing valid decision data."""
        return {
            "decision": "Adopt React for the new frontend project",
            "made_by": "Sarah Chen (CTO)",
            "rationale": "React has better team expertise and component reusability",
            "impact": DecisionImpact.HIGH,
        }

    @pytest.fixture
    def future_date(self):
        """Fixture providing a future date."""
        return datetime.now(UTC) + timedelta(days=30)

    def test_should_create_decision_with_valid_data(self, valid_decision_data):
        """Test creating Decision with valid data."""
        decision = Decision(**valid_decision_data)

        assert decision.decision == valid_decision_data["decision"]
        assert decision.made_by == valid_decision_data["made_by"]
        assert decision.rationale == valid_decision_data["rationale"]
        assert decision.impact == DecisionImpact.HIGH
        assert decision.status == DecisionStatus.APPROVED  # default
        assert decision.confidence_level == 0.5  # default
        assert decision.affected_teams == []  # default
        assert decision.alternatives_considered == []  # default
        assert decision.tags == []  # default
        assert decision.dependencies == []  # default

    def test_should_generate_unique_id(self, valid_decision_data):
        """Test that each Decision gets a unique ID."""
        decision1 = Decision(**valid_decision_data)
        decision2 = Decision(**valid_decision_data)

        assert decision1.id != decision2.id
        assert str(decision1.id)  # Should be valid UUID string

    def test_should_set_automatic_timestamp(self, valid_decision_data):
        """Test that timestamp is automatically set."""
        before = datetime.now(UTC)
        decision = Decision(**valid_decision_data)
        after = datetime.now(UTC)

        assert before <= decision.timestamp <= after
        assert before <= decision.created_at <= after

    def test_should_validate_decision_length(self, valid_decision_data):
        """Test decision text length validation."""
        # Too short
        with pytest.raises(ValueError, match="at least 5 characters"):
            Decision(**{**valid_decision_data, "decision": "hi"})

        # Too long
        long_decision = "x" * 1001
        with pytest.raises(ValueError, match="at most 1000 characters"):
            Decision(**{**valid_decision_data, "decision": long_decision})

        # Valid length
        valid_decision = "We will use TypeScript for better type safety"
        decision = Decision(**{**valid_decision_data, "decision": valid_decision})
        assert decision.decision == valid_decision

    def test_should_validate_made_by_format(self, valid_decision_data):
        """Test made_by field validation."""
        # Empty name
        with pytest.raises(ValueError, match="Decision maker cannot be empty"):
            Decision(**{**valid_decision_data, "made_by": ""})

        # Invalid characters
        with pytest.raises(ValueError, match="invalid characters"):
            Decision(**{**valid_decision_data, "made_by": "Alice@Johnson"})

        # Valid formats
        valid_names = [
            "Alice Johnson",
            "Bob O'Connor (CEO)",
            "Dr. Sarah Chen",
            "Mary-Jane Smith (Product Lead)",
        ]

        for name in valid_names:
            decision = Decision(**{**valid_decision_data, "made_by": name})
            assert decision.made_by == name

    def test_should_validate_rationale_length(self, valid_decision_data):
        """Test rationale length validation."""
        # Too short
        with pytest.raises(ValueError, match="at least 5 characters"):
            Decision(**{**valid_decision_data, "rationale": "ok"})

        # Too long
        long_rationale = "x" * 2001
        with pytest.raises(ValueError, match="at most 2000 characters"):
            Decision(**{**valid_decision_data, "rationale": long_rationale})

    def test_should_validate_future_dates(self, valid_decision_data):
        """Test that implementation and review dates cannot be in the past."""
        past_date = datetime.now(UTC) - timedelta(days=1)

        with pytest.raises(ValueError, match="cannot be in the past"):
            Decision(**{**valid_decision_data, "implementation_date": past_date})

        with pytest.raises(ValueError, match="cannot be in the past"):
            Decision(**{**valid_decision_data, "review_date": past_date})

    def test_should_accept_future_dates(self, valid_decision_data, future_date):
        """Test that future dates are accepted."""
        decision = Decision(
            **{
                **valid_decision_data,
                "implementation_date": future_date,
                "review_date": future_date + timedelta(days=30),
            }
        )

        assert decision.implementation_date == future_date
        assert decision.review_date == future_date + timedelta(days=30)

    def test_should_clean_string_lists(self, valid_decision_data):
        """Test cleaning of string list fields."""
        decision = Decision(
            **{
                **valid_decision_data,
                "affected_teams": [
                    "  Frontend Team  ",
                    "BACKEND",
                    "frontend team",
                    "QA",
                    "x",
                ],
                "alternatives_considered": ["Vue.js", "  Angular  ", "vue.js"],
                "tags": ["tech", "  FRONTEND  ", "tech", "ui"],
                "dependencies": ["Training", "  SETUP  ", "training"],
            }
        )

        # Should be cleaned: trimmed, deduplicated, min length 2
        assert decision.affected_teams == ["Frontend Team", "BACKEND", "QA"]
        assert decision.alternatives_considered == ["Vue.js", "Angular"]
        assert decision.tags == ["tech", "FRONTEND", "ui"]
        assert decision.dependencies == ["Training", "SETUP"]

    def test_should_validate_confidence_level(self, valid_decision_data):
        """Test confidence level validation."""
        # Too low
        with pytest.raises(ValueError, match="greater than or equal to 0"):
            Decision(**{**valid_decision_data, "confidence_level": -0.1})

        # Too high
        with pytest.raises(ValueError, match="less than or equal to 1"):
            Decision(**{**valid_decision_data, "confidence_level": 1.1})

        # Valid values
        for level in [0.0, 0.5, 1.0]:
            decision = Decision(**{**valid_decision_data, "confidence_level": level})
            assert decision.confidence_level == level

    def test_should_mark_implemented_correctly(self, valid_decision_data):
        """Test marking decision as implemented."""
        decision = Decision(**valid_decision_data)

        before = datetime.now(UTC)
        decision.mark_implemented()
        after = datetime.now(UTC)

        assert decision.status == DecisionStatus.IMPLEMENTED
        assert before <= decision.implementation_date <= after
        assert decision.updated_at is not None

    def test_should_preserve_existing_implementation_date(
        self, valid_decision_data, future_date
    ):
        """Test that existing implementation date is preserved."""
        decision = Decision(
            **{**valid_decision_data, "implementation_date": future_date}
        )

        decision.mark_implemented()

        assert decision.status == DecisionStatus.IMPLEMENTED
        assert decision.implementation_date == future_date

    def test_should_mark_deferred_correctly(self, valid_decision_data, future_date):
        """Test marking decision as deferred."""
        decision = Decision(**valid_decision_data)

        decision.mark_deferred(future_date)

        assert decision.status == DecisionStatus.DEFERRED
        assert decision.review_date == future_date
        assert decision.updated_at is not None

    def test_should_mark_deferred_without_new_date(self, valid_decision_data):
        """Test marking decision as deferred without changing review date."""
        original_review = datetime.now(UTC) + timedelta(days=10)
        decision = Decision(**{**valid_decision_data, "review_date": original_review})

        decision.mark_deferred()

        assert decision.status == DecisionStatus.DEFERRED
        assert decision.review_date == original_review

    def test_should_detect_due_for_review(self, valid_decision_data):
        """Test due for review detection."""
        # Past review date
        past_date = datetime.now(UTC) - timedelta(hours=1)
        past_review = Decision(**valid_decision_data)
        past_review.review_date = past_date  # Set after creation
        assert past_review.is_due_for_review() is True

        # Future review date
        future_date = datetime.now(UTC) + timedelta(days=1)
        future_review = Decision(**{**valid_decision_data, "review_date": future_date})
        assert future_review.is_due_for_review() is False

        # No review date
        no_review = Decision(**valid_decision_data)
        assert no_review.is_due_for_review() is False

    def test_should_calculate_days_until_implementation(self, valid_decision_data):
        """Test days until implementation calculation."""
        # Future date
        future_date = datetime.now(UTC) + timedelta(days=10)
        future_impl = Decision(
            **{**valid_decision_data, "implementation_date": future_date}
        )
        assert future_impl.days_until_implementation() == 10

        # Past date (negative days)
        past_date = datetime.now(UTC) - timedelta(days=5)
        past_impl = Decision(**valid_decision_data)
        past_impl.implementation_date = past_date
        assert past_impl.days_until_implementation() == -5

        # No implementation date
        no_impl = Decision(**valid_decision_data)
        assert no_impl.days_until_implementation() is None

    def test_should_handle_all_enum_values(self, valid_decision_data):
        """Test that all enum values work correctly."""
        # Test all status values
        for status in DecisionStatus:
            decision = Decision(**{**valid_decision_data, "status": status})
            assert decision.status == status

        # Test all impact values
        for impact in DecisionImpact:
            decision = Decision(**{**valid_decision_data, "impact": impact})
            assert decision.impact == impact

    def test_should_serialize_correctly(self, valid_decision_data, future_date):
        """Test Decision serialization."""
        decision = Decision(
            **{
                **valid_decision_data,
                "implementation_date": future_date,
                "affected_teams": ["Team A", "Team B"],
                "alternatives_considered": ["Option 1", "Option 2"],
                "tags": ["tech", "frontend"],
                "confidence_level": 0.8,
            }
        )

        data = decision.model_dump()

        # Check key fields are present
        assert data["decision"] == valid_decision_data["decision"]
        assert data["made_by"] == valid_decision_data["made_by"]
        assert data["rationale"] == valid_decision_data["rationale"]
        assert data["status"] == "approved"  # Enum value
        assert data["impact"] == "high"  # Enum value
        assert data["affected_teams"] == ["Team A", "Team B"]
        assert data["alternatives_considered"] == ["Option 1", "Option 2"]
        assert data["tags"] == ["tech", "frontend"]
        assert data["confidence_level"] == 0.8
        assert "id" in data
        assert "timestamp" in data
        assert "created_at" in data


class TestDecisionUpdate:
    """Test DecisionUpdate model functionality."""

    def test_should_create_partial_update(self):
        """Test creating partial update with only some fields."""
        update = DecisionUpdate(
            decision="Updated decision text", impact=DecisionImpact.CRITICAL
        )

        assert update.decision == "Updated decision text"
        assert update.impact == DecisionImpact.CRITICAL
        assert update.rationale is None  # Not provided
        assert update.status is None  # Not provided

    def test_should_validate_updated_fields(self):
        """Test that updated fields are validated."""
        # Invalid decision length
        with pytest.raises(ValueError, match="at least 5 characters"):
            DecisionUpdate(decision="hi")

        # Invalid rationale length
        with pytest.raises(ValueError, match="at least 5 characters"):
            DecisionUpdate(rationale="ok")

        # Invalid confidence level
        with pytest.raises(ValueError, match="greater than or equal to 0"):
            DecisionUpdate(confidence_level=-0.1)

    def test_should_allow_all_none_values(self):
        """Test that update can have all None values."""
        update = DecisionUpdate()

        assert update.decision is None
        assert update.rationale is None
        assert update.status is None
        assert update.impact is None
        assert update.confidence_level is None

    def test_should_serialize_correctly(self):
        """Test DecisionUpdate serialization."""
        future_date = datetime.now(UTC) + timedelta(days=14)

        update = DecisionUpdate(
            decision="New decision text",
            status=DecisionStatus.DEFERRED,
            implementation_date=future_date,
            tags=["updated", "test"],
            confidence_level=0.9,
        )

        data = update.model_dump()

        assert data["decision"] == "New decision text"
        assert data["status"] == "deferred"
        assert data["rationale"] is None
        assert data["tags"] == ["updated", "test"]
        assert data["confidence_level"] == 0.9
