import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Database
    DATABASE_URL: str = "postgresql://analytics_user:analytics_pass@localhost:5432/7taps_analytics"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Direct Database Connections (No MCP needed)
    # PostgreSQL and Redis are accessed directly via psycopg2 and redis-py
    
    # 7taps Configuration
    SEVENTAPS_PRIVATE_KEY_PATH: str = "keys/7taps_private_key.pem"
    SEVENTAPS_PUBLIC_KEY_PATH: str = "keys/7taps_public_key.pem"
    SEVENTAPS_WEBHOOK_SECRET: Optional[str] = None
    SEVENTAPS_API_BASE_URL: str = "https://api.7taps.com"
    SEVENTAPS_WEBHOOK_ENDPOINT: str = "/api/7taps/webhook"
    SEVENTAPS_AUTH_ENABLED: bool = True
    SEVENTAPS_VERIFY_SIGNATURE: bool = True
    
    # OpenAI (for NLP)
    OPENAI_API_KEY: Optional[str] = None
    
    # Application
    LOG_LEVEL: str = "info"
    PYTHONUNBUFFERED: str = "1"
    
    # Production settings
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_database_url() -> str:
    """Get database URL with fallback for production."""
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")
    return settings.DATABASE_URL


def get_redis_url() -> str:
    """Get Redis URL with fallback for production."""
    if os.getenv("REDIS_URL"):
        return os.getenv("REDIS_URL")
    return settings.REDIS_URL 