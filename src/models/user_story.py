"""User story model for meeting transcript analysis."""

from enum import Enum
from typing import Annotated, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class StoryPriority(str, Enum):
    """User story priority levels."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class UserStory(BaseModel):
    """
    User story model for meeting transcript analysis.

    Represents user requirements and needs extracted from meeting discussions.
    """

    id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for the user story"
    )

    story: Annotated[
        str,
        Field(
            min_length=20,
            max_length=500,
            description="User story in standard format: As a [user], I want [goal], so that [benefit]",
            json_schema_extra={
                "example": "As an enterprise user, I want to login automatically when accessing the app from my corporate network, so that I don't need separate credentials"
            },
        ),
    ]

    acceptance_criteria: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Acceptance criteria for the user story",
        json_schema_extra={
            "example": [
                "User is automatically authenticated when coming from corporate network",
                "Fallback to manual login if SSO fails",
                "Support for both SAML and OIDC protocols",
            ]
        },
    )

    priority: StoryPriority = Field(description="Business priority of the user story")

    epic: Optional[str] = Field(
        None,
        max_length=100,
        description="Epic or larger feature group this story belongs to",
        json_schema_extra={"example": "SSO Authentication System"},
    )

    business_value: Optional[str] = Field(
        None,
        max_length=300,
        description="Business value and impact description",
        json_schema_extra={
            "example": "Reduces user friction and improves enterprise adoption"
        },
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "story": "As an enterprise user, I want to login automatically when accessing the app from my corporate network, so that I don't need separate credentials",
                "acceptance_criteria": [
                    "User is automatically authenticated when coming from corporate network",
                    "Fallback to manual login if SSO fails",
                    "Support for both SAML and OIDC protocols",
                ],
                "priority": "high",
                "epic": "SSO Authentication System",
                "business_value": "Reduces user friction and improves enterprise adoption",
            }
        }
