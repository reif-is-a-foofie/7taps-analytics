"""
Redis client utilities for infrastructure-v2.
"""
import os
import redis
from typing import Optional
import structlog

logger = structlog.get_logger()

# Global Redis client
_redis_client: Optional[redis.Redis] = None

def get_redis_url() -> str:
    """Get Redis URL from environment."""
    return os.getenv("REDIS_URL", "redis://localhost:6379")

def get_redis_client() -> Optional[redis.Redis]:
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        try:
            redis_url = get_redis_url()
            _redis_client = redis.from_url(
                redis_url,
                ssl_cert_reqs=None,  # Disable SSL certificate verification for Heroku Redis
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True,
                socket_keepalive=True
            )
            # Test connection
            _redis_client.ping()
            logger.info("Redis client connected successfully")
        except Exception as e:
            logger.warning("Redis connection failed, caching disabled", error=str(e))
            _redis_client = None
    return _redis_client

def generate_cache_key(query: str, params: Optional[dict] = None) -> str:
    """Generate cache key for query."""
    import hashlib
    import json
    
    key_data = {"query": query, "params": params or {}}
    key_string = json.dumps(key_data, sort_keys=True)
    return f"query_cache:{hashlib.md5(key_string.encode()).hexdigest()}"

