"""Application configuration."""

from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Basic settings
    app_name: str = "TLDR"
    debug: bool = False
    
    # API settings
    api_prefix: str = "/api/v1"
    allowed_origins: List[str] = ["*"]
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    
    # Database
    database_url: str = "sqlite:///./tldr.db"
    
    # AI Service API Keys
    openai_api_key: str = ""
    assemblyai_api_key: str = ""
    
    # File upload limits
    max_file_size_mb: int = 100
    allowed_file_types: List[str] = [".mp3", ".mp4", ".wav", ".m4a", ".txt"]
    
    # Processing settings
    max_transcript_length: int = 50000
    summary_max_tokens: int = 1000
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()