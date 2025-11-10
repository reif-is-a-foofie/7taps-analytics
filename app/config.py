import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # 7taps Configuration
    SEVENTAPS_PRIVATE_KEY_PATH: str = "keys/7taps_private_key.pem"
    SEVENTAPS_PUBLIC_KEY_PATH: str = "keys/7taps_public_key.pem"
    SEVENTAPS_WEBHOOK_SECRET: Optional[str] = None
    SEVENTAPS_API_BASE_URL: str = "https://api.7taps.com"
    SEVENTAPS_WEBHOOK_ENDPOINT: str = "/api/7taps/webhook"
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
    
    # Lesson mapping cache (loaded from JSON)
    _lesson_mapping: Optional[Dict[str, Dict[str, Any]]] = None
    _lesson_url_reverse: Optional[Dict[str, str]] = None
    
    # AI Services
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_AI_API_KEY: Optional[str] = None
    PRIVACY_ADMIN_KEY: Optional[str] = None  # For Gemini API
    AI_SERVICE_URL: Optional[str] = None  # URL for AI Analysis Cloud Function

    # Application
    LOG_LEVEL: str = "info"
    PYTHONUNBUFFERED: str = "1"

    # Production settings
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    DEPLOYMENT_MODE: str = "full"  # "full" or "cloud_run"

    # GCP configuration (shared across deployment targets)
    GCP_PROJECT_ID: str = "pol-a-477603"
    GCP_BIGQUERY_DATASET: str = "taps_data"
    GCP_LOCATION: str = "us-central1"
    GCP_SERVICE_ACCOUNT_KEY_PATH: str = ""
    GCP_PUBSUB_TOPIC: str = "xapi-ingestion-topic"
    GCP_STORAGE_BUCKET: str = "xapi-raw-data"

    # Port Configuration (use PORT env var for Cloud Run)
    APP_PORT: int = int(os.getenv("PORT", "8000"))
    REDIS_PORT: int = 6379
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra='ignore'
    )

    def _load_lesson_mapping(self) -> None:
        """Load lesson mapping from JSON file."""
        if self._lesson_mapping is not None:
            return
        
        mapping_path = Path(__file__).parent / "data" / "lesson_mapping.json"
        if not mapping_path.exists():
            self._lesson_mapping = {}
            self._lesson_url_reverse = {}
            return
        
        try:
            with open(mapping_path, 'r') as f:
                data = json.load(f)
                self._lesson_mapping = data.get("lessons", {})
                
                # Build reverse lookup: URL → lesson_number
                self._lesson_url_reverse = {}
                for lesson_num, lesson_data in self._lesson_mapping.items():
                    url = lesson_data.get("lesson_url", "").strip()
                    if url:
                        self._lesson_url_reverse[url] = lesson_num
        except Exception as e:
            print(f"Warning: Failed to load lesson mapping: {e}")
            self._lesson_mapping = {}
            self._lesson_url_reverse = {}
    
    def get_lesson_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Reverse lookup: get lesson metadata by URL."""
        self._load_lesson_mapping()
        lesson_num = self._lesson_url_reverse.get(url.strip())
        if lesson_num:
            return self._lesson_mapping.get(lesson_num)
        return None
    
    def get_lesson_by_number(self, lesson_number: str) -> Optional[Dict[str, Any]]:
        """Get lesson metadata by lesson number."""
        self._load_lesson_mapping()
        return self._lesson_mapping.get(str(lesson_number))
    
    def get_extension_key(self, key_name: str) -> str:
        """Get extension key with dynamic domain support."""
        base_key = self.SEVENTAPS_EXTENSION_KEYS.get(key_name, key_name)
        if not base_key.startswith('http'):
            return f"{self.SEVENTAPS_DOMAIN}/{base_key}"
        return base_key
    
    def get_lesson_url(self, lesson_number: str) -> str:
        """Get lesson URL with fallback."""
        lesson = self.get_lesson_by_number(str(lesson_number))
        return lesson.get("lesson_url", "") if lesson else ""
    
    def get_lesson_name(self, lesson_number: str) -> str:
        """Get lesson name with fallback."""
        lesson = self.get_lesson_by_number(str(lesson_number))
        return lesson.get("lesson_name", f"Lesson {lesson_number}") if lesson else f"Lesson {lesson_number}"


# Global settings instance
settings = Settings()


def get_redis_url() -> str:
    """Get Redis URL with fallback for production."""
    if os.getenv("REDIS_URL"):
        return os.getenv("REDIS_URL")
    return settings.REDIS_URL


def get_extension_key(key_name: str) -> str:
    """Get extension key with dynamic domain support."""
    return settings.get_extension_key(key_name)


def get_lesson_url(lesson_number: str) -> str:
    """Get lesson URL by lesson number."""
    return settings.get_lesson_url(lesson_number)


def get_lesson_name(lesson_number: str) -> str:
    """Get lesson name with fallback."""
    return settings.get_lesson_name(lesson_number)


def get_lesson_by_url(url: str) -> Optional[Dict[str, Any]]:
    """Reverse lookup: get lesson metadata by URL."""
    return settings.get_lesson_by_url(url)


def get_lesson_by_number(lesson_number: str) -> Optional[Dict[str, Any]]:
    """Get lesson metadata by lesson number."""
    return settings.get_lesson_by_number(lesson_number) 
