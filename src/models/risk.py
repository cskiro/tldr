"""Risk model for meeting transcript analysis."""

from enum import Enum
from typing import Annotated, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RiskCategory(str, Enum):
    """Risk categories for meeting analysis."""

    TECHNICAL = "technical"
    SECURITY = "security"
    BUSINESS = "business"


class RiskImpact(str, Enum):
    """Risk impact levels."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskLikelihood(str, Enum):
    """Risk likelihood levels."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Risk(BaseModel):
    """
    Risk model for meeting transcript analysis.

    Represents identified risks with impact assessment and mitigation strategies.
    """

    id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for the risk"
    )

    risk: Annotated[
        str,
        Field(
            min_length=10,
            max_length=1000,
            description="Detailed description of the risk",
            json_schema_extra={
                "example": "Dual protocol implementation may exceed timeline due to complexity"
            },
        ),
    ]

    category: RiskCategory = Field(description="Risk category classification")

    impact: RiskImpact = Field(description="Potential impact level of the risk")

    likelihood: RiskLikelihood = Field(description="Likelihood of the risk occurring")

    mitigation: Annotated[
        str,
        Field(
            min_length=5,
            max_length=500,
            description="Mitigation strategy or approach",
            json_schema_extra={
                "example": "Implement feature flags for gradual rollout"
            },
        ),
    ]

    owner: Optional[str] = Field(
        None,
        max_length=100,
        description="Person responsible for managing this risk",
        json_schema_extra={"example": "Marcus Rodriguez"},
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "risk": "Dual protocol implementation (SAML + OIDC) may exceed 8-week timeline due to session management complexity",
                "category": "technical",
                "impact": "high",
                "likelihood": "medium",
                "mitigation": "Implement feature flags for gradual rollout, consider OIDC-first approach",
                "owner": "Marcus Rodriguez",
            }
        }
