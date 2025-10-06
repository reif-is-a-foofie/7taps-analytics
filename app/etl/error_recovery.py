"""
Error Recovery System for xAPI ETL Processing.
Tracks failed statements, provides retry mechanisms, and maintains error analytics.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

# Google Cloud imports
from google.cloud import pubsub_v1, bigquery, storage
from google.api_core import exceptions as gcp_exceptions

# Local imports
from app.config.gcp_config import gcp_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FailedStatement:
    """Represents a failed xAPI statement with error details."""
    statement_id: str
    raw_statement: Dict[str, Any]
    error_message: str
    error_type: str
    failed_at: str
    retry_count: int = 0
    last_retry_at: Optional[str] = None
    processing_stage: str = "unknown"  # storage, bigquery, etc.
    message_id: Optional[str] = None


class ErrorRecoverySystem:
    """Manages failed statement recovery and retry logic."""
    
    def __init__(self):
        self.project_id = gcp_config.project_id
        self.dataset_id = gcp_config.bigquery_dataset
        self.bucket_name = gcp_config.storage_bucket
        
        # Initialize clients
        self.bq_client = gcp_config.bigquery_client
        self.storage_client = gcp_config.storage_client
        self.pubsub_client = pubsub_v1.PublisherClient(credentials=gcp_config.credentials)
        
        # Dead letter queue topic
        self.dead_letter_topic = f"{gcp_config.pubsub_topic}-dead-letter"
        self.dead_letter_topic_path = self.pubsub_client.topic_path(
            self.project_id, self.dead_letter_topic
        )
        
        # Ensure dead letter topic exists
        self._ensure_dead_letter_topic()
        
        # Ensure error tracking table exists
        self._ensure_error_tracking_table()
    
    def _ensure_dead_letter_topic(self) -> bool:
        """Ensure the dead letter topic exists."""
        try:
            try:
                self.pubsub_client.get_topic(request={"topic": self.dead_letter_topic_path})
                logger.info(f"Dead letter topic {self.dead_letter_topic} already exists")
                return True
            except gcp_exceptions.NotFound:
                # Create dead letter topic
                self.pubsub_client.create_topic(request={"name": self.dead_letter_topic_path})
                logger.info(f"Created dead letter topic {self.dead_letter_topic}")
                return True
        except Exception as e:
            logger.error(f"Failed to ensure dead letter topic exists: {str(e)}")
            return False
    
    def _ensure_error_tracking_table(self) -> bool:
        """Ensure the error tracking table exists in BigQuery."""
        try:
            table_id = f"{self.project_id}.{self.dataset_id}.failed_statements"
            
            # Define table schema
            schema = [
                bigquery.SchemaField("statement_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("raw_statement", "JSON", mode="REQUIRED"),
                bigquery.SchemaField("error_message", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("error_type", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("failed_at", "TIMESTAMP", mode="REQUIRED"),
                bigquery.SchemaField("retry_count", "INTEGER", mode="REQUIRED"),
                bigquery.SchemaField("last_retry_at", "TIMESTAMP", mode="NULLABLE"),
                bigquery.SchemaField("processing_stage", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("message_id", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("resolved_at", "TIMESTAMP", mode="NULLABLE"),
            ]
            
            table = bigquery.Table(table_id, schema=schema)
            
            try:
                self.bq_client.get_table(table_id)
                logger.info("Error tracking table already exists")
                return True
            except gcp_exceptions.NotFound:
                table = self.bq_client.create_table(table)
                logger.info(f"Created error tracking table {table_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to ensure error tracking table exists: {str(e)}")
            return False
    
    def record_failed_statement(
        self, 
        statement_id: str,
        raw_statement: Dict[str, Any],
        error_message: str,
        error_type: str,
        processing_stage: str,
        message_id: Optional[str] = None
    ) -> bool:
        """Record a failed statement for later retry."""
        try:
            failed_statement = FailedStatement(
                statement_id=statement_id,
                raw_statement=raw_statement,
                error_message=error_message,
                error_type=error_type,
                failed_at=datetime.now(timezone.utc).isoformat(),
                processing_stage=processing_stage,
                message_id=message_id
            )
            
            # Store in BigQuery
            table_id = f"{self.project_id}.{self.dataset_id}.failed_statements"
            table = self.bq_client.get_table(table_id)
            
            # Convert to BigQuery row format
            row = {
                "statement_id": failed_statement.statement_id,
                "raw_statement": json.dumps(failed_statement.raw_statement),
                "error_message": failed_statement.error_message,
                "error_type": failed_statement.error_type,
                "failed_at": failed_statement.failed_at,
                "retry_count": failed_statement.retry_count,
                "last_retry_at": failed_statement.last_retry_at,
                "processing_stage": failed_statement.processing_stage,
                "message_id": failed_statement.message_id,
                "resolved_at": None
            }
            
            errors = self.bq_client.insert_rows(table, [row])
            if errors:
                logger.error(f"Failed to record failed statement: {errors}")
                return False
            
            # Also publish to dead letter queue for immediate retry attempts
            self._publish_to_dead_letter_queue(failed_statement)
            
            logger.info(f"Recorded failed statement {statement_id} for retry")
            return True
            
        except Exception as e:
            logger.error(f"Failed to record failed statement {statement_id}: {str(e)}")
            return False
    
    def _publish_to_dead_letter_queue(self, failed_statement: FailedStatement) -> bool:
        """Publish failed statement to dead letter queue for retry."""
        try:
            # Add retry metadata
            retry_data = {
                "original_statement": failed_statement.raw_statement,
                "retry_metadata": {
                    "statement_id": failed_statement.statement_id,
                    "error_message": failed_statement.error_message,
                    "error_type": failed_statement.error_type,
                    "processing_stage": failed_statement.processing_stage,
                    "retry_count": failed_statement.retry_count,
                    "failed_at": failed_statement.failed_at
                }
            }
            
            # Publish to dead letter topic
            message_data = json.dumps(retry_data).encode('utf-8')
            future = self.pubsub_client.publish(
                self.dead_letter_topic_path, 
                message_data,
                statement_id=failed_statement.statement_id,
                retry_count=str(failed_statement.retry_count)
            )
            
            logger.info(f"Published failed statement {failed_statement.statement_id} to dead letter queue")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish to dead letter queue: {str(e)}")
            return False
    
    def get_failed_statements(
        self, 
        limit: int = 50,
        processing_stage: Optional[str] = None,
        error_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve failed statements for review and retry."""
        try:
            query = f"""
            SELECT 
                statement_id,
                raw_statement,
                error_message,
                error_type,
                failed_at,
                retry_count,
                last_retry_at,
                processing_stage,
                message_id,
                resolved_at
            FROM `{self.project_id}.{self.dataset_id}.failed_statements`
            WHERE resolved_at IS NULL
            """
            
            if processing_stage:
                query += f" AND processing_stage = '{processing_stage}'"
            
            if error_type:
                query += f" AND error_type = '{error_type}'"
            
            query += f" ORDER BY failed_at DESC LIMIT {limit}"
            
            query_job = self.bq_client.query(query)
            results = query_job.result()
            
            failed_statements = []
            for row in results:
                statement_data = {
                    "statement_id": row.statement_id,
                    "raw_statement": json.loads(row.raw_statement),
                    "error_message": row.error_message,
                    "error_type": row.error_type,
                    "failed_at": row.failed_at.isoformat() if row.failed_at else None,
                    "retry_count": row.retry_count,
                    "last_retry_at": row.last_retry_at.isoformat() if row.last_retry_at else None,
                    "processing_stage": row.processing_stage,
                    "message_id": row.message_id,
                    "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None
                }
                failed_statements.append(statement_data)
            
            return failed_statements
            
        except Exception as e:
            logger.error(f"Failed to get failed statements: {str(e)}")
            return []
    
    def retry_failed_statement(self, statement_id: str) -> Dict[str, Any]:
        """Manually retry a specific failed statement."""
        try:
            # Get the failed statement
            query = f"""
            SELECT 
                statement_id,
                raw_statement,
                error_message,
                error_type,
                retry_count,
                processing_stage
            FROM `{self.project_id}.{self.dataset_id}.failed_statements`
            WHERE statement_id = '{statement_id}' AND resolved_at IS NULL
            """
            
            query_job = self.bq_client.query(query)
            results = list(query_job.result())
            
            if not results:
                return {
                    "success": False,
                    "error": f"Failed statement {statement_id} not found or already resolved"
                }
            
            row = results[0]
            raw_statement = json.loads(row.raw_statement)
            
            # Update retry count
            new_retry_count = row.retry_count + 1
            update_query = f"""
            UPDATE `{self.project_id}.{self.dataset_id}.failed_statements`
            SET 
                retry_count = {new_retry_count},
                last_retry_at = CURRENT_TIMESTAMP()
            WHERE statement_id = '{statement_id}' AND resolved_at IS NULL
            """
            
            self.bq_client.query(update_query).result()
            
            # Publish to dead letter queue for retry
            retry_data = {
                "original_statement": raw_statement,
                "retry_metadata": {
                    "statement_id": statement_id,
                    "error_message": row.error_message,
                    "error_type": row.error_type,
                    "processing_stage": row.processing_stage,
                    "retry_count": new_retry_count,
                    "failed_at": datetime.now(timezone.utc).isoformat()
                }
            }
            
            message_data = json.dumps(retry_data).encode('utf-8')
            future = self.pubsub_client.publish(
                self.dead_letter_topic_path, 
                message_data,
                statement_id=statement_id,
                retry_count=str(new_retry_count)
            )
            
            return {
                "success": True,
                "message": f"Statement {statement_id} queued for retry (attempt #{new_retry_count})",
                "retry_count": new_retry_count
            }
            
        except Exception as e:
            logger.error(f"Failed to retry statement {statement_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def mark_statement_resolved(self, statement_id: str) -> bool:
        """Mark a failed statement as resolved."""
        try:
            update_query = f"""
            UPDATE `{self.project_id}.{self.dataset_id}.failed_statements`
            SET resolved_at = CURRENT_TIMESTAMP()
            WHERE statement_id = '{statement_id}' AND resolved_at IS NULL
            """
            
            self.bq_client.query(update_query).result()
            logger.info(f"Marked statement {statement_id} as resolved")
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark statement {statement_id} as resolved: {str(e)}")
            return False
    
    def get_error_analytics(self) -> Dict[str, Any]:
        """Get analytics about failed statements."""
        try:
            # Error types breakdown
            error_types_query = f"""
            SELECT 
                error_type,
                COUNT(*) as count,
                AVG(retry_count) as avg_retries
            FROM `{self.project_id}.{self.dataset_id}.failed_statements`
            WHERE resolved_at IS NULL
            GROUP BY error_type
            ORDER BY count DESC
            """
            
            # Processing stage breakdown
            stage_query = f"""
            SELECT 
                processing_stage,
                COUNT(*) as count,
                AVG(retry_count) as avg_retries
            FROM `{self.project_id}.{self.dataset_id}.failed_statements`
            WHERE resolved_at IS NULL
            GROUP BY processing_stage
            ORDER BY count DESC
            """
            
            # Recent failures
            recent_query = f"""
            SELECT 
                COUNT(*) as total_failed,
                COUNT(CASE WHEN failed_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR) THEN 1 END) as failed_last_hour,
                COUNT(CASE WHEN failed_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR) THEN 1 END) as failed_last_24h
            FROM `{self.project_id}.{self.dataset_id}.failed_statements`
            WHERE resolved_at IS NULL
            """
            
            error_types_job = self.bq_client.query(error_types_query)
            stage_job = self.bq_client.query(stage_query)
            recent_job = self.bq_client.query(recent_query)
            
            error_types = [dict(row) for row in error_types_job.result()]
            stages = [dict(row) for row in stage_job.result()]
            recent = list(recent_job.result())[0]
            
            return {
                "error_types": error_types,
                "processing_stages": stages,
                "recent_failures": {
                    "total_failed": recent.total_failed,
                    "failed_last_hour": recent.failed_last_hour,
                    "failed_last_24h": recent.failed_last_24h
                },
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get error analytics: {str(e)}")
            return {"error": str(e)}


# Global error recovery instance
_error_recovery = None

def get_error_recovery() -> ErrorRecoverySystem:
    """Get the global error recovery instance."""
    global _error_recovery
    if _error_recovery is None:
        _error_recovery = ErrorRecoverySystem()
    return _error_recovery
