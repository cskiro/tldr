"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Basic settings
    app_name: str = "TLDR"
    debug: bool = False

    # API settings
    api_prefix: str = "/api/v1"
    allowed_origins: list[str] = ["*"]

    # Security
    secret_key: str = "your-secret-key-change-in-production"

    # Database
    database_url: str = "sqlite:///./tldr.db"

    # LLM Provider Configuration
    llm_provider: str = "ollama"  # ollama, openai, anthropic, or mock
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    assemblyai_api_key: str = ""

    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"

    # Processing Configuration
    max_tokens: int = 4000
    temperature: float = 0.1
    enable_structured_output: bool = True
    processing_timeout_seconds: float = 120.0

    # File upload limits
    max_file_size_mb: int = 100
    allowed_file_types: list[str] = [".mp3", ".mp4", ".wav", ".m4a", ".txt"]

    # Legacy processing settings (kept for compatibility)
    max_transcript_length: int = 50000
    summary_max_tokens: int = 1000

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
