"""Test configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def sample_transcript():
    """Sample transcript for testing."""
    return """
    John: Good morning everyone. Let's start with the quarterly review.
    
    Sarah: Thanks John. Our revenue is up 15% from last quarter.
    We need to focus on customer retention this quarter.
    
    Mike: I'll take the lead on the retention project.
    We should have a proposal ready by Friday.
    
    John: Great. Let's also discuss the new product launch.
    Sarah, can you coordinate with marketing?
    
    Sarah: Absolutely. I'll set up a meeting with the marketing team this week.
    
    John: Perfect. Any other business? No? Meeting adjourned.
    """


@pytest.fixture
def expected_summary():
    """Expected summary structure for testing."""
    return {
        "summary": "Quarterly review meeting discussing revenue growth and upcoming projects.",
        "key_topics": ["Quarterly Review", "Revenue Growth", "Customer Retention", "Product Launch"],
        "decisions": [
            {
                "decision": "Focus on customer retention this quarter",
                "made_by": "Team consensus",
                "rationale": "Revenue up 15% but need to maintain growth"
            }
        ],
        "action_items": [
            {
                "task": "Lead customer retention project",
                "assignee": "Mike",
                "due_date": "Friday",
                "priority": "High"
            },
            {
                "task": "Coordinate with marketing team",
                "assignee": "Sarah",
                "due_date": "This week",
                "priority": "Medium"
            }
        ]
    }
