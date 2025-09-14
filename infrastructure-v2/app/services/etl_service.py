"""
Consolidated ETL service for infrastructure-v2.
Combines streaming, incremental, and BigQuery ETL processing.
"""
from typing import Dict, Any, List, Optional
import structlog
import asyncio
from datetime import datetime
import json

from config.gcp_config import gcp_config
from app.core.exceptions import ExternalServiceError, ValidationError
from app.database import get_db_pool, execute_query
from app.redis_client import get_redis_client

logger = structlog.get_logger()


class ETLService:
    """Consolidated ETL service for all data processing operations."""
    
    def __init__(self):
        self.gcp_config = gcp_config
        self.redis_client = get_redis_client()
        self.db_pool = get_db_pool()
        
        # ETL processors
        self.streaming_processor = None
        self.incremental_processor = None
        self.bigquery_processor = None
        
        # Metrics
        self.metrics = {
            "total_processed": 0,
            "streaming_processed": 0,
            "incremental_processed": 0,
            "bigquery_processed": 0,
            "errors": 0,
            "last_processing_time": None
        }
    
    async def initialize_processors(self):
        """Initialize all ETL processors."""
        try:
            # Import processors dynamically to avoid circular imports
            from app.etl_streaming import ETLStreamingProcessor
            from app.etl_incremental import IncrementalETLProcessor
            from app.etl.bigquery_schema_migration import BigQuerySchemaMigration
            
            self.streaming_processor = ETLStreamingProcessor()
            self.incremental_processor = IncrementalETLProcessor()
            self.bigquery_processor = BigQuerySchemaMigration()
            
            logger.info("ETL processors initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize ETL processors", error=str(e))
            raise ExternalServiceError(f"ETL initialization failed: {str(e)}")
    
    async def process_xapi_statement(self, statement: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single xAPI statement through all ETL pipelines."""
        try:
            if not self.streaming_processor:
                await self.initialize_processors()
            
            # Process through streaming ETL
            streaming_result = await self.streaming_processor.process_statement(statement)
            
            # Process through incremental ETL
            incremental_result = await self.incremental_processor.process_statement(statement)
            
            # Update metrics
            self.metrics["total_processed"] += 1
            self.metrics["streaming_processed"] += 1
            self.metrics["incremental_processed"] += 1
            self.metrics["last_processing_time"] = datetime.utcnow().isoformat()
            
            return {
                "success": True,
                "statement_id": statement.get("id"),
                "streaming_result": streaming_result,
                "incremental_result": incremental_result,
                "processed_at": self.metrics["last_processing_time"]
            }
            
        except Exception as e:
            self.metrics["errors"] += 1
            logger.error("Failed to process xAPI statement", error=str(e))
            raise ExternalServiceError(f"Statement processing failed: {str(e)}")
    
    async def process_batch(self, statements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process multiple xAPI statements in batch."""
        try:
            results = []
            successful = 0
            failed = 0
            
            for statement in statements:
                try:
                    result = await self.process_xapi_statement(statement)
                    results.append(result)
                    successful += 1
                except Exception as e:
                    logger.error("Failed to process statement in batch", error=str(e))
                    results.append({
                        "success": False,
                        "statement_id": statement.get("id"),
                        "error": str(e)
                    })
                    failed += 1
            
            return {
                "success": True,
                "total": len(statements),
                "successful": successful,
                "failed": failed,
                "results": results,
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Batch processing failed", error=str(e))
            raise ExternalServiceError(f"Batch processing failed: {str(e)}")
    
    async def get_etl_status(self) -> Dict[str, Any]:
        """Get comprehensive ETL system status."""
        try:
            # Check Redis connection
            redis_status = "connected" if self.redis_client and self.redis_client.ping() else "disconnected"
            
            # Check database connection
            db_status = "connected" if self.db_pool else "disconnected"
            
            # Check GCP services
            gcp_status = self.gcp_config.validate_connection()
            
            # Get processor statuses
            processor_status = {}
            if self.streaming_processor:
                processor_status["streaming"] = "initialized"
            if self.incremental_processor:
                processor_status["incremental"] = "initialized"
            if self.bigquery_processor:
                processor_status["bigquery"] = "initialized"
            
            return {
                "status": "healthy" if all([
                    redis_status == "connected",
                    db_status == "connected",
                    gcp_status["credentials"] == "valid"
                ]) else "degraded",
                "timestamp": datetime.utcnow().isoformat(),
                "connections": {
                    "redis": redis_status,
                    "database": db_status,
                    "gcp": gcp_status
                },
                "processors": processor_status,
                "metrics": self.metrics
            }
            
        except Exception as e:
            logger.error("Failed to get ETL status", error=str(e))
            return {
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    async def start_streaming_etl(self) -> Dict[str, Any]:
        """Start the streaming ETL processor."""
        try:
            if not self.streaming_processor:
                await self.initialize_processors()
            
            # Start streaming processor
            await self.streaming_processor.start_processing()
            
            return {
                "success": True,
                "message": "Streaming ETL started successfully",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to start streaming ETL", error=str(e))
            raise ExternalServiceError(f"Failed to start streaming ETL: {str(e)}")
    
    async def start_incremental_etl(self) -> Dict[str, Any]:
        """Start the incremental ETL processor."""
        try:
            if not self.incremental_processor:
                await self.initialize_processors()
            
            # Start incremental processor
            await self.incremental_processor.start_processing()
            
            return {
                "success": True,
                "message": "Incremental ETL started successfully",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to start incremental ETL", error=str(e))
            raise ExternalServiceError(f"Failed to start incremental ETL: {str(e)}")
    
    async def get_processing_metrics(self) -> Dict[str, Any]:
        """Get detailed processing metrics."""
        try:
            # Get Redis stream metrics
            redis_metrics = {}
            if self.redis_client:
                try:
                    # Get stream info
                    stream_info = self.redis_client.xinfo_stream("xapi_statements")
                    redis_metrics = {
                        "stream_length": stream_info.get("length", 0),
                        "first_entry": stream_info.get("first-entry"),
                        "last_entry": stream_info.get("last-entry")
                    }
                except Exception as e:
                    redis_metrics = {"error": str(e)}
            
            # Get database metrics
            db_metrics = {}
            if self.db_pool:
                try:
                    # Get table counts
                    tables = ["xapi_statements", "xapi_statements_normalized", "users", "lessons"]
                    for table in tables:
                        result = execute_query(f"SELECT COUNT(*) as count FROM {table}")
                        if result:
                            db_metrics[f"{table}_count"] = result[0]["count"]
                except Exception as e:
                    db_metrics = {"error": str(e)}
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "etl_metrics": self.metrics,
                "redis_metrics": redis_metrics,
                "database_metrics": db_metrics
            }
            
        except Exception as e:
            logger.error("Failed to get processing metrics", error=str(e))
            raise ExternalServiceError(f"Failed to get metrics: {str(e)}")

