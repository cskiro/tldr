"""Factory for creating appropriate summarization services based on provider and configuration."""

from typing import Optional

from src.core.config import settings
from src.core.logging import service_logger

from .base import SummarizationServiceBase


def create_summarization_service(
    provider: Optional[str] = None, 
    api_key: Optional[str] = None
) -> SummarizationServiceBase:
    """
    Create appropriate summarization service based on provider and availability.
    
    Args:
        provider: Optional provider override ("ollama", "openai", "anthropic", "mock")
        api_key: Optional API key for cloud providers
        
    Returns:
        SummarizationServiceBase: Configured service instance
        
    Priority order:
    1. Explicit provider parameter with valid configuration
    2. Settings-configured provider with valid configuration
    3. Ollama if available locally
    4. Mock service as fallback
    """
    # Use provided provider or fall back to settings
    provider = provider or settings.llm_provider
    
    service_logger.info(
        "Creating summarization service",
        extra={
            "requested_provider": provider,
            "has_custom_api_key": bool(api_key),
            "settings_provider": settings.llm_provider
        }
    )
    
    try:
        # Try requested provider first
        if provider == "ollama":
            return _create_ollama_service()
        elif provider == "openai":
            return _create_openai_service(api_key)
        elif provider == "anthropic":
            return _create_anthropic_service(api_key)
        elif provider == "mock":
            return _create_mock_service()
        else:
            service_logger.warning(f"Unknown provider: {provider}, trying fallback options")
            
    except Exception as e:
        service_logger.warning(
            f"Failed to create {provider} service: {e}, trying fallback options"
        )
    
    # Fallback chain: Check availability first
    providers = get_available_providers()
    
    # Try Ollama if available
    if providers["ollama"]["available"]:
        try:
            service_logger.info("Attempting Ollama fallback")
            return _create_ollama_service()
        except Exception as e:
            service_logger.warning(f"Ollama fallback failed: {e}")
    else:
        service_logger.info("Ollama not available, skipping fallback")
    
    # Final fallback to mock service
    service_logger.info("Using mock service as final fallback")
    return _create_mock_service()


def _create_ollama_service() -> SummarizationServiceBase:
    """Create Ollama service with health check."""
    try:
        from .ollama_service import OllamaService
        
        service = OllamaService(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout=settings.processing_timeout_seconds
        )
        
        # Basic connectivity check (synchronous)
        import httpx
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{settings.ollama_base_url}/api/tags")
                if response.status_code != 200:
                    raise Exception("Ollama server not responding correctly")
        except Exception as e:
            raise Exception(f"Ollama health check failed: {e}")
            
        service_logger.info("Successfully created Ollama service")
        return service
        
    except ImportError:
        raise Exception("Ollama dependencies not available")
    except Exception as e:
        raise Exception(f"Failed to initialize Ollama service: {e}")


def _create_openai_service(api_key: Optional[str] = None) -> SummarizationServiceBase:
    """Create OpenAI service with API key validation."""
    try:
        from .llm_provider_service import LLMProviderService
        
        # Use provided key or settings key
        key = api_key or settings.openai_api_key
        if not key:
            raise Exception("No OpenAI API key provided")
            
        service = LLMProviderService("openai", key)
        service_logger.info("Successfully created OpenAI service")
        return service
        
    except ImportError:
        raise Exception("OpenAI dependencies not available")
    except Exception as e:
        raise Exception(f"Failed to initialize OpenAI service: {e}")


def _create_anthropic_service(api_key: Optional[str] = None) -> SummarizationServiceBase:
    """Create Anthropic service with API key validation."""
    try:
        from .llm_provider_service import LLMProviderService
        
        # Use provided key or settings key
        key = api_key or settings.anthropic_api_key
        if not key:
            raise Exception("No Anthropic API key provided")
            
        service = LLMProviderService("anthropic", key)
        service_logger.info("Successfully created Anthropic service")
        return service
        
    except ImportError:
        raise Exception("Anthropic dependencies not available")
    except Exception as e:
        raise Exception(f"Failed to initialize Anthropic service: {e}")


def _create_mock_service() -> SummarizationServiceBase:
    """Create mock service (always available)."""
    try:
        from .mock_summarization_service import MockSummarizationService
        
        service = MockSummarizationService()
        service_logger.info("Successfully created Mock service")
        return service
        
    except Exception as e:
        service_logger.error(f"Even mock service creation failed: {e}")
        raise Exception("Critical error: Cannot create any summarization service")


def get_available_providers() -> dict[str, dict[str, any]]:
    """
    Get information about available providers and their status.
    
    Returns:
        Dict with provider information including availability and configuration
    """
    providers = {}
    
    # Check Ollama
    try:
        import httpx
        with httpx.Client(timeout=3.0) as client:
            response = client.get(f"{settings.ollama_base_url}/api/tags")
            ollama_available = response.status_code == 200
    except Exception:
        ollama_available = False
        
    providers["ollama"] = {
        "available": ollama_available,
        "configured": True,  # Always configured through settings
        "cost": "free",
        "quality": "good",
        "speed": "medium",
        "config": {
            "base_url": settings.ollama_base_url,
            "model": settings.ollama_model
        }
    }
    
    # Check OpenAI
    providers["openai"] = {
        "available": bool(settings.openai_api_key),
        "configured": bool(settings.openai_api_key),
        "cost": "paid",
        "quality": "excellent",
        "speed": "fast",
        "config": {
            "has_api_key": bool(settings.openai_api_key),
            "model": "gpt-4o-mini"
        }
    }
    
    # Check Anthropic
    providers["anthropic"] = {
        "available": bool(settings.anthropic_api_key),
        "configured": bool(settings.anthropic_api_key),
        "cost": "paid",
        "quality": "excellent",
        "speed": "fast",
        "config": {
            "has_api_key": bool(settings.anthropic_api_key),
            "model": "claude-3-haiku-20240307"
        }
    }
    
    # Mock is always available
    providers["mock"] = {
        "available": True,
        "configured": True,
        "cost": "free",
        "quality": "basic",
        "speed": "very_fast",
        "config": {
            "rule_based": True
        }
    }
    
    return providers


def get_recommended_provider() -> str:
    """
    Get the recommended provider based on current configuration and availability.
    
    Returns:
        Recommended provider name
    """
    providers = get_available_providers()
    
    # Priority: OpenAI/Anthropic (if configured) > Ollama (if available) > Mock
    if providers["openai"]["available"]:
        return "openai"
    elif providers["anthropic"]["available"]:
        return "anthropic"
    elif providers["ollama"]["available"]:
        return "ollama"
    else:
        return "mock"


def validate_provider_config(provider: str, api_key: Optional[str] = None) -> dict[str, any]:
    """
    Validate provider configuration without creating the service.
    
    Args:
        provider: Provider name to validate
        api_key: Optional API key for validation
        
    Returns:
        Validation result with status and details
    """
    result = {
        "provider": provider,
        "valid": False,
        "available": False,
        "message": "",
        "requirements_met": False
    }
    
    try:
        if provider == "ollama":
            import httpx
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{settings.ollama_base_url}/api/tags")
                if response.status_code == 200:
                    result["valid"] = True
                    result["available"] = True
                    result["requirements_met"] = True
                    result["message"] = "Ollama service is accessible"
                else:
                    result["message"] = "Ollama service not responding"
                    
        elif provider == "openai":
            key = api_key or settings.openai_api_key
            if not key:
                result["message"] = "OpenAI API key not provided"
            else:
                result["valid"] = True
                result["available"] = True
                result["requirements_met"] = True
                result["message"] = "OpenAI configuration valid"
                
        elif provider == "anthropic":
            key = api_key or settings.anthropic_api_key
            if not key:
                result["message"] = "Anthropic API key not provided"
            else:
                result["valid"] = True
                result["available"] = True
                result["requirements_met"] = True
                result["message"] = "Anthropic configuration valid"
                
        elif provider == "mock":
            result["valid"] = True
            result["available"] = True
            result["requirements_met"] = True
            result["message"] = "Mock service always available"
            
        else:
            result["message"] = f"Unknown provider: {provider}"
            
    except Exception as e:
        result["message"] = f"Validation error: {str(e)}"
        
    return result