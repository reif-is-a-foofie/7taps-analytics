"""
Configuration for AI Analysis Service
"""

import os
from typing import Optional

class Settings:
    """Configuration settings for AI service."""
    
    # AI Services
    GOOGLE_AI_API_KEY: Optional[str] = os.getenv('GOOGLE_AI_API_KEY')
    
    # Batch Processing
    BATCH_SIZE: int = 50
    BATCH_TIMEOUT_MINUTES: int = 2
    MAX_TOKENS_PER_BATCH: int = 100000

settings = Settings()
