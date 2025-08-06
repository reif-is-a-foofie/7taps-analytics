"""
Learning Locker Sync Service

This service syncs xAPI statements from our custom LRS to Learning Locker
for better data exploration and visualization.
"""

import os
import json
import logging
import asyncio
import httpx
from typing import Dict, Any, List
from datetime import datetime
import redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LearningLockerSync:
    """Sync service for Learning Locker integration."""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.learninglocker_url = os.getenv("LEARNINGLOCKER_URL", "http://localhost:8080")
        self.learninglocker_username = os.getenv("LEARNINGLOCKER_USERNAME", "admin@7taps.com")
        self.learninglocker_password = os.getenv("LEARNINGLOCKER_PASSWORD", "admin123")
        
        # Initialize Redis client
        self.redis_client = redis.from_url(
            self.redis_url,
            ssl_cert_reqs=None,
            decode_responses=True
        )
        
        # Initialize HTTP client
        self._http_client = httpx.AsyncClient(timeout=30.0)
        
        # Track sync status
        self.last_sync_time = None
        self.sync_count = 0
        
    async def get_learninglocker_auth(self) -> str:
        """Get Learning Locker authentication token."""
        try:
            # Login to Learning Locker
            login_data = {
                "email": self.learninglocker_username,
                "password": self.learninglocker_password
            }
            
            response = await self._http_client.post(
                f"{self.learninglocker_url}/auth/login",
                json=login_data
            )
            
            if response.status_code == 200:
                # Extract token from response
                # This depends on Learning Locker's auth mechanism
                return response.headers.get("Authorization", "")
            else:
                logger.error(f"Learning Locker login failed: {response.status_code}")
                return ""
                
        except Exception as e:
            logger.error(f"Error getting Learning Locker auth: {e}")
            return ""
    
    async def sync_statement_to_learninglocker(self, statement: Dict[str, Any]) -> bool:
        """Sync a single statement to Learning Locker."""
        try:
            auth_token = await self.get_learninglocker_auth()
            if not auth_token:
                return False
            
            # Post statement to Learning Locker
            headers = {
                "Authorization": auth_token,
                "Content-Type": "application/json",
                "X-Experience-API-Version": "1.0.3"
            }
            
            response = await self._http_client.post(
                f"{self.learninglocker_url}/data/xAPI/statements",
                headers=headers,
                json=statement
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully synced statement {statement.get('id', 'unknown')} to Learning Locker")
                return True
            else:
                logger.error(f"Failed to sync statement: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error syncing statement to Learning Locker: {e}")
            return False
    
    async def sync_redis_to_learninglocker(self, max_statements: int = 10) -> Dict[str, Any]:
        """Sync statements from Redis to Learning Locker."""
        try:
            stream_name = "xapi_statements"
            sync_group = "learninglocker_sync"
            sync_consumer = "sync_worker"
            
            # Create consumer group if it doesn't exist
            try:
                self.redis_client.xgroup_create(
                    stream_name,
                    sync_group,
                    id="0",
                    mkstream=True
                )
            except redis.exceptions.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    logger.error(f"Error creating sync group: {e}")
            
            # Read messages from stream
            messages = self.redis_client.xreadgroup(
                sync_group,
                sync_consumer,
                {stream_name: ">"},
                count=max_statements,
                block=1000
            )
            
            synced_count = 0
            failed_count = 0
            
            for stream, message_list in messages:
                for message_id, fields in message_list:
                    try:
                        # Parse statement data
                        if b'data' in fields:
                            statement_data = json.loads(fields[b'data'].decode('utf-8'))
                        else:
                            statement_data = json.loads(fields.get('data', '{}'))
                        
                        # Sync to Learning Locker
                        success = await self.sync_statement_to_learninglocker(statement_data)
                        
                        if success:
                            synced_count += 1
                            # Acknowledge message
                            self.redis_client.xack(stream_name, sync_group, message_id)
                        else:
                            failed_count += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing message {message_id}: {e}")
                        failed_count += 1
            
            # Update sync status
            self.last_sync_time = datetime.utcnow().isoformat()
            self.sync_count += synced_count
            
            return {
                "synced_count": synced_count,
                "failed_count": failed_count,
                "total_processed": synced_count + failed_count,
                "last_sync_time": self.last_sync_time,
                "total_synced": self.sync_count
            }
            
        except Exception as e:
            logger.error(f"Error in sync process: {e}")
            return {
                "synced_count": 0,
                "failed_count": 0,
                "total_processed": 0,
                "error": str(e)
            }
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status."""
        return {
            "last_sync_time": self.last_sync_time,
            "total_synced": self.sync_count,
            "learninglocker_url": self.learninglocker_url,
            "redis_url": self.redis_url.split("@")[-1] if self.redis_url else "not_configured"
        }
    
    async def close(self):
        """Close HTTP client."""
        await self._http_client.aclose()

# Global sync instance
learninglocker_sync = LearningLockerSync() 