import os
from typing import Optional, Dict
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
    SEVENTAPS_WEBHOOK_ENDPOINT: str = "/api/pol/webhook"
    SEVENTAPS_AUTH_ENABLED: bool = True
    SEVENTAPS_VERIFY_SIGNATURE: bool = True
    
    # 7taps Domain Configuration (Dynamic)
    SEVENTAPS_DOMAIN: str = "https://7taps.com"
    SEVENTAPS_EXTENSION_KEYS: Dict[str, str] = {
        "lesson_number": "https://7taps.com/lesson-number",
        "lesson_name": "https://7taps.com/lesson-name", 
        "lesson_url": "https://7taps.com/lesson-url",
        "global_q": "https://7taps.com/global-q",
        "card_type": "https://7taps.com/card-type",
        "card_number": "https://7taps.com/card-number",
        "pdf_page": "https://7taps.com/pdf-page",
        "source": "https://7taps.com/source",
        "full_card_text": "https://7taps.com/full-card-text",
        "question_text": "https://7taps.com/question-text",
        "cohort": "https://7taps.com/cohort",
        "poll_metadata": "https://7taps.com/poll-metadata",
        "audio_metadata": "https://7taps.com/audio-metadata"
    }
    
    # Lesson Mappings (Configurable)
    LESSON_URL_MAPPING: Dict[str, str] = {
        "1": "https://7taps.com/lessons/digital-wellness-foundations",
        "2": "https://7taps.com/lessons/screen-habits-awareness", 
        "3": "https://7taps.com/lessons/device-relationship",
        "4": "https://7taps.com/lessons/productivity-focus",
        "5": "https://7taps.com/lessons/connection-balance"
    }
    
    LESSON_NAME_MAPPING: Dict[str, str] = {
        "1": "Digital Wellness Foundations",
        "2": "Screen Habits Awareness",
        "3": "Device Relationship", 
        "4": "Productivity Focus",
        "5": "Connection Balance"
    }
    
    # OpenAI (for NLP)
    OPENAI_API_KEY: Optional[str] = None
    
    # Application
    LOG_LEVEL: str = "info"
    PYTHONUNBUFFERED: str = "1"
    
    # Production settings
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # Port Configuration (use PORT env var for Cloud Run)
    APP_PORT: int = int(os.getenv("PORT", "8000"))
    POSTGRES_PORT: int = 5432
    REDIS_PORT: int = 6379
    
    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_extension_key(self, key_name: str) -> str:
        """Get extension key with dynamic domain support."""
        base_key = self.SEVENTAPS_EXTENSION_KEYS.get(key_name, key_name)
        if not base_key.startswith('http'):
            return f"{self.SEVENTAPS_DOMAIN}/{base_key}"
        return base_key
    
    def get_lesson_url(self, lesson_number: str) -> str:
        """Get lesson URL with dynamic domain support."""
        base_url = self.LESSON_URL_MAPPING.get(str(lesson_number), "")
        if base_url and not base_url.startswith('http'):
            return f"{self.SEVENTAPS_DOMAIN}{base_url}"
        return base_url
    
    def get_lesson_name(self, lesson_number: str) -> str:
        """Get lesson name with fallback."""
        return self.LESSON_NAME_MAPPING.get(str(lesson_number), f"Lesson {lesson_number}")


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


def get_extension_key(key_name: str) -> str:
    """Get extension key with dynamic domain support."""
    return settings.get_extension_key(key_name)


def get_lesson_url(lesson_number: str) -> str:
    """Get lesson URL with dynamic domain support."""
    return settings.get_lesson_url(lesson_number)


def get_lesson_name(lesson_number: str) -> str:
    """Get lesson name with fallback."""
    return settings.get_lesson_name(lesson_number) 