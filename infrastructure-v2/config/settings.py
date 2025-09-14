"""
Production-ready configuration management with proper secrets handling.
"""
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import validator
import os


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "7taps Analytics v2"
    debug: bool = False
    environment: str = "production"
    
    # Google Cloud Platform
    gcp_project_id: str = ""
    gcp_region: str = "us-central1"
    gcp_service_account_key: Optional[str] = None
    
    # Database
    database_url: Optional[str] = None
    
    # Redis
    redis_url: Optional[str] = None
    
    # BigQuery
    bigquery_dataset: str = ""
    
    # Pub/Sub
    pubsub_topic: str = ""
    pubsub_storage_subscription: str = ""
    pubsub_bigquery_subscription: str = ""
    
    # Cloud Storage
    storage_bucket: str = ""
    
    # Monitoring
    enable_monitoring: bool = True
    log_level: str = "INFO"
    
    # Security
    secret_key: Optional[str] = None
    allowed_hosts: List[str] = []
    
    # API Configuration
    api_base_url: str = ""
    cors_origins: List[str] = []
    
    @validator('gcp_service_account_key', pre=True)
    def load_service_account_key(cls, v):
        """Load service account key from file if path provided."""
        if v and os.path.exists(v):
            with open(v, 'r') as f:
                return f.read()
        return v
    
    @validator('secret_key', pre=True)
    def generate_secret_key(cls, v):
        """Generate secret key if not provided."""
        if not v:
            import secrets
            return secrets.token_urlsafe(32)
        return v
    
    @validator('gcp_project_id')
    def validate_gcp_project_id(cls, v):
        """Validate GCP project ID is provided."""
        if not v:
            raise ValueError("GCP_PROJECT_ID environment variable is required")
        return v
    
    @validator('bigquery_dataset')
    def validate_bigquery_dataset(cls, v):
        """Validate BigQuery dataset is provided."""
        if not v:
            raise ValueError("BIGQUERY_DATASET environment variable is required")
        return v
    
    @validator('pubsub_topic')
    def validate_pubsub_topic(cls, v):
        """Validate Pub/Sub topic is provided."""
        if not v:
            raise ValueError("PUBSUB_TOPIC environment variable is required")
        return v
    
    @validator('storage_bucket')
    def validate_storage_bucket(cls, v):
        """Validate Cloud Storage bucket is provided."""
        if not v:
            raise ValueError("STORAGE_BUCKET environment variable is required")
        return v
    
    @validator('allowed_hosts')
    def validate_allowed_hosts(cls, v):
        """Validate allowed hosts configuration."""
        if not v:
            # Default to localhost for development
            return ["localhost", "127.0.0.1"]
        if "*" in v and len(v) > 1:
            raise ValueError("Cannot specify '*' with other hosts")
        return v
    
    @validator('cors_origins')
    def validate_cors_origins(cls, v):
        """Validate CORS origins configuration."""
        if not v:
            # Default to localhost for development
            return ["http://localhost:3000", "http://localhost:8000"]
        if "*" in v and len(v) > 1:
            raise ValueError("Cannot specify '*' with other origins")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

