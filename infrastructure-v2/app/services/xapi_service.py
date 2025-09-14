"""
xAPI service for processing and storing xAPI statements.
"""
from typing import Dict, Any, List
import structlog
import json
import uuid
from datetime import datetime
from google.cloud import pubsub_v1

from config.gcp_config import GCPConfig
from app.core.exceptions import ExternalServiceError, ValidationError

logger = structlog.get_logger()


class XAPIService:
    """Service for handling xAPI statement processing."""
    
    def __init__(self, gcp_config: GCPConfig):
        self.gcp_config = gcp_config
        self.pubsub_client = gcp_config.pubsub_client
    
    async def ingest_statement(self, statement: Dict[str, Any]) -> Dict[str, Any]:
        """Process and store a single xAPI statement."""
        try:
            # Generate statement ID if not provided
            if not statement.get('id'):
                statement['id'] = str(uuid.uuid4())
            
            # Add timestamps
            now = datetime.utcnow().isoformat()
            statement['stored'] = statement.get('timestamp', now)
            
            # Validate statement
            self._validate_statement(statement)
            
            # Publish to Pub/Sub
            topic_path = self.gcp_config.get_topic_path(self.gcp_config.pubsub_topic)
            message_data = json.dumps(statement).encode('utf-8')
            
            future = self.pubsub_client.publish(
                topic_path,
                message_data,
                statement_id=statement['id'],
                timestamp=statement['stored']
            )
            
            message_id = future.result()
            
            logger.info(
                "xAPI statement published",
                statement_id=statement['id'],
                message_id=message_id,
                topic=self.gcp_config.pubsub_topic
            )
            
            return {
                "success": True,
                "statement_id": statement['id'],
                "message_id": message_id,
                "topic": self.gcp_config.pubsub_topic
            }
            
        except Exception as e:
            logger.error("Failed to ingest xAPI statement", error=str(e))
            raise ExternalServiceError(f"Failed to process xAPI statement: {str(e)}")
    
    async def ingest_batch(self, statements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and store multiple xAPI statements."""
        results = []
        
        for statement in statements:
            try:
                result = await self.ingest_statement(statement)
                results.append(result)
            except Exception as e:
                logger.error("Failed to process statement in batch", error=str(e))
                results.append({
                    "success": False,
                    "statement_id": statement.get('id'),
                    "error": str(e)
                })
        
        return results
    
    def _validate_statement(self, statement: Dict[str, Any]) -> None:
        """Validate xAPI statement structure."""
        required_fields = ['actor', 'verb', 'object']
        
        for field in required_fields:
            if field not in statement:
                raise ValidationError(f"Missing required field: {field}")
            
            if not isinstance(statement[field], dict):
                raise ValidationError(f"Field '{field}' must be an object")
        
        # Validate actor
        actor = statement['actor']
        if not any(key in actor for key in ['mbox', 'mbox_sha1sum', 'openid']):
            raise ValidationError("Actor must have mbox, mbox_sha1sum, or openid")
        
        # Validate verb
        verb = statement['verb']
        if not verb.get('id'):
            raise ValidationError("Verb must have an id")
        
        # Validate object
        obj = statement['object']
        if not obj.get('id'):
            raise ValidationError("Object must have an id")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get service status and metrics."""
        try:
            # Check Pub/Sub topic
            topic_path = self.gcp_config.get_topic_path(self.gcp_config.pubsub_topic)
            
            # This is a simple check - in production you might want more detailed metrics
            try:
                # Try to get topic info (this will fail if topic doesn't exist)
                topic = self.pubsub_client.get_topic(topic_path)
                pubsub_status = "connected"
            except Exception:
                pubsub_status = "not_found"
            
            return {
                "pubsub": {
                    "status": pubsub_status,
                    "topic": self.gcp_config.pubsub_topic
                },
                "gcp_project": self.gcp_config.project_id
            }
            
        except Exception as e:
            logger.error("Failed to get xAPI service status", error=str(e))
            raise ExternalServiceError(f"Failed to get service status: {str(e)}")


