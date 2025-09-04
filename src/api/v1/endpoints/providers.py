"""AI Provider configuration and status endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from src.core.logging import api_logger
from src.models.base import APIResponse
from src.services.summarization_factory import (
    get_available_providers,
    get_recommended_provider,
    validate_provider_config,
)

router = APIRouter()


class ProviderValidationRequest(BaseModel):
    """Request model for provider validation."""

    provider: str
    api_key: str | None = None


@router.get("/status", response_model=APIResponse)
async def get_provider_status():
    """
    Get the status and availability of all AI providers.

    Returns information about:
    - Provider availability (can connect)
    - Configuration status (API keys, etc.)
    - Cost structure (free/paid)
    - Quality and speed estimates
    """
    try:
        api_logger.info("Provider status requested")

        providers = get_available_providers()
        recommended = get_recommended_provider()

        return APIResponse.success_response(
            message="Provider status retrieved successfully",
            data={
                "providers": providers,
                "recommended": recommended,
                "default_provider": "ollama",
            },
        )

    except Exception as e:
        api_logger.error(
            f"Error retrieving provider status: {str(e)}",
            error_type=type(e).__name__,
        )
        return APIResponse.error_response(
            message="Failed to retrieve provider status",
            details=f"Error: {str(e)}",
        )


@router.post("/validate", response_model=APIResponse)
async def validate_provider(request: ProviderValidationRequest):
    """
    Validate a provider configuration without creating a service.

    This endpoint checks if a provider is properly configured and
    accessible without actually starting processing.
    """
    try:
        api_logger.info(
            f"Provider validation requested: {request.provider}",
            provider=request.provider,
            has_api_key=bool(request.api_key),
        )

        validation_result = validate_provider_config(
            provider=request.provider, api_key=request.api_key
        )

        if validation_result["valid"]:
            return APIResponse.success_response(
                message="Provider configuration is valid",
                data=validation_result,
            )
        else:
            return APIResponse.error_response(
                message="Provider configuration is invalid",
                details=validation_result["message"],
                data=validation_result,
            )

    except Exception as e:
        api_logger.error(
            f"Error validating provider {request.provider}: {str(e)}",
            provider=request.provider,
            error_type=type(e).__name__,
        )
        return APIResponse.error_response(
            message="Provider validation failed",
            details=f"Validation error: {str(e)}",
        )


@router.get("/recommended", response_model=APIResponse)
async def get_recommended():
    """
    Get the recommended provider based on current configuration.

    Returns the best available provider considering:
    - API key availability
    - Service connectivity
    - Quality vs cost tradeoffs
    """
    try:
        recommended = get_recommended_provider()
        providers = get_available_providers()

        return APIResponse.success_response(
            message="Recommended provider retrieved",
            data={
                "recommended": recommended,
                "details": providers[recommended],
                "reasoning": _get_recommendation_reasoning(providers, recommended),
            },
        )

    except Exception as e:
        api_logger.error(
            f"Error getting recommended provider: {str(e)}",
            error_type=type(e).__name__,
        )
        return APIResponse.error_response(
            message="Failed to get recommendation",
            details=f"Error: {str(e)}",
        )


def _get_recommendation_reasoning(providers: dict, recommended: str) -> str:
    """Generate human-readable reasoning for provider recommendation."""
    provider_info = providers[recommended]

    if recommended == "openai":
        return "OpenAI provides excellent quality and fast processing with your configured API key."
    elif recommended == "anthropic":
        return "Anthropic Claude provides excellent quality and fast processing with your configured API key."
    elif recommended == "ollama":
        if provider_info["available"]:
            return "Ollama is recommended as the best free option - local processing with good quality and no API costs."
        else:
            return "Ollama would be ideal but is not currently available. Please ensure Ollama is installed and running."
    else:
        return "Mock service provides basic functionality for testing when no other providers are available."
