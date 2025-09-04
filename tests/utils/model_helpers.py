"""Model testing utilities for bypassing validation in edge cases.

This module provides utilities for creating model instances with invalid data
for testing purposes only. These utilities should NEVER be used in production code.
"""

from datetime import datetime
from typing import Any

from src.models.action_item import ActionItem
from src.models.decision import Decision


def create_action_item_with_past_date(
    data: dict[str, Any], past_date: datetime
) -> ActionItem:
    """Create ActionItem with past due_date for testing overdue scenarios.

    Uses Pydantic's model_construct() to bypass validation for testing purposes.
    This allows testing edge cases like overdue calculations without compromising
    production validation safety.

    Args:
        data: Valid ActionItem data dictionary
        past_date: A datetime in the past to set as due_date

    Returns:
        ActionItem instance with past due_date set
    """
    # Create with all data including the past date
    item_data = {**data, "due_date": past_date}

    # Use model_construct to bypass validation
    return ActionItem.model_construct(**item_data)


def create_decision_with_past_date(
    data: dict[str, Any],
    past_date: datetime,
    date_field: str = "review_date"
) -> Decision:
    """Create Decision with past implementation/review date for testing.

    Uses Pydantic's model_construct() to bypass validation for testing purposes.
    This allows testing edge cases like overdue review detection without
    compromising production validation safety.

    Args:
        data: Valid Decision data dictionary
        past_date: A datetime in the past to set as the specified date field
        date_field: Which date field to set ("review_date" or "implementation_date")

    Returns:
        Decision instance with past date set
    """
    # Create with all data including the past date
    decision_data = {**data, date_field: past_date}

    # Use model_construct to bypass validation
    return Decision.model_construct(**decision_data)
