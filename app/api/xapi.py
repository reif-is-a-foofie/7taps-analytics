"""
xAPI Ingestion Endpoint for receiving and queuing learning statements.
"""

import os
import json
import redis
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.models import (
    xAPIStatement, 
    xAPIIngestionResponse, 
    xAPIIngestionStatus,
    xAPIValidationError
)

# Initialize router
router = APIRouter()

# Global Redis client
redis_client = None
ingestion_stats = {
    "total_statements": 0,
    "error_count": 0,
    "last_ingestion_time": None
}


def get_redis_client():
    """Get Redis client instance."""
    global redis_client
    if redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis_client = redis.from_url(
            redis_url,
            ssl_cert_reqs=None,  # Disable SSL certificate verification for Heroku Redis
            decode_responses=True
        )
    return redis_client


def validate_xapi_statement(statement_data: Dict[str, Any]) -> xAPIStatement:
    """Validate xAPI statement data."""
    try:
        return xAPIStatement(**statement_data)
    except ValidationError as e:
        errors = []
        for error in e.errors():
            errors.append(xAPIValidationError(
                field=error["loc"][0] if error["loc"] else "unknown",
                message=error["msg"],
                value=error.get("input")
            ))
        raise HTTPException(
            status_code=422,
            detail={
                "message": "xAPI statement validation failed",
                "errors": [error.dict() for error in errors]
            }
        )


def queue_statement_to_redis(statement: xAPIStatement, redis_client: redis.Redis) -> str:
    """Queue xAPI statement to Redis Streams."""
    stream_name = "xapi_statements"
    
    # Convert statement to JSON for Redis storage
    statement_data = statement.to_dict()
    
    # Add metadata
    statement_data["ingested_at"] = datetime.utcnow().isoformat()
    statement_data["queue_id"] = str(uuid.uuid4())
    
    # Add to Redis Stream
    message_id = redis_client.xadd(
        stream_name,
        {"data": json.dumps(statement_data)},
        maxlen=10000  # Keep last 10k messages
    )
    
    return message_id


@router.post("/api/xapi/ingest", response_model=xAPIIngestionResponse)
async def ingest_xapi_statement(statement_data: Dict[str, Any]):
    """
    Ingest xAPI statement and queue for ETL processing.
    
    Accepts xAPI statement in JSON format and validates it before
    queuing to Redis Streams for ETL processing.
    """
    try:
        # Get Redis client
        redis_client = get_redis_client()
        
        # Validate xAPI statement
        statement = validate_xapi_statement(statement_data)
        
        # Generate statement ID if not provided
        if not statement.id:
            statement.id = str(uuid.uuid4())
        
        # Queue to Redis Streams
        message_id = queue_statement_to_redis(statement, redis_client)
        
        # Update stats
        ingestion_stats["total_statements"] += 1
        ingestion_stats["last_ingestion_time"] = datetime.utcnow()
        
        # Get queue position (approximate)
        queue_size = redis_client.xlen("xapi_statements")
        
        return xAPIIngestionResponse(
            success=True,
            statement_id=statement.id,
            message=f"xAPI statement ingested successfully. Message ID: {message_id}",
            queue_position=queue_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        ingestion_stats["error_count"] += 1
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to ingest xAPI statement",
                "error": str(e)
            }
        )


@router.get("/ui/test-xapi-ingestion", response_model=xAPIIngestionStatus)
async def get_xapi_ingestion_status():
    """
    Get xAPI ingestion endpoint status and statistics.
    """
    try:
        redis_client = get_redis_client()
        
        # Test Redis connection
        redis_connected = redis_client.ping()
        
        # Get queue size
        queue_size = redis_client.xlen("xapi_statements") if redis_connected else None
        
        return xAPIIngestionStatus(
            endpoint_status="operational",
            redis_connected=redis_connected,
            total_statements_ingested=ingestion_stats["total_statements"],
            last_ingestion_time=ingestion_stats["last_ingestion_time"],
            queue_size=queue_size,
            error_count=ingestion_stats["error_count"]
        )
        
    except Exception as e:
        return xAPIIngestionStatus(
            endpoint_status="error",
            redis_connected=False,
            total_statements_ingested=ingestion_stats["total_statements"],
            last_ingestion_time=ingestion_stats["last_ingestion_time"],
            queue_size=None,
            error_count=ingestion_stats["error_count"]
        )


@router.post("/api/xapi/ingest/batch")
async def ingest_xapi_batch(statements: List[Dict[str, Any]]):
    """
    Ingest multiple xAPI statements in batch.
    """
    results = []
    success_count = 0
    error_count = 0
    
    for i, statement_data in enumerate(statements):
        try:
            # Validate statement
            statement = validate_xapi_statement(statement_data)
            
            # Generate ID if not provided
            if not statement.id:
                statement.id = str(uuid.uuid4())
            
            # Queue to Redis
            redis_client = get_redis_client()
            message_id = queue_statement_to_redis(statement, redis_client)
            
            results.append({
                "index": i,
                "success": True,
                "statement_id": statement.id,
                "message_id": message_id
            })
            success_count += 1
            
        except Exception as e:
            results.append({
                "index": i,
                "success": False,
                "error": str(e)
            })
            error_count += 1
    
    # Update stats
    ingestion_stats["total_statements"] += success_count
    ingestion_stats["error_count"] += error_count
    if success_count > 0:
        ingestion_stats["last_ingestion_time"] = datetime.utcnow()
    
    return {
        "batch_results": results,
        "summary": {
            "total": len(statements),
            "successful": success_count,
            "failed": error_count
        }
    }


@router.get("/api/xapi/statements/{statement_id}")
async def get_statement_status(statement_id: str):
    """
    Get status of a specific xAPI statement.
    """
    try:
        redis_client = get_redis_client()
        
        # Search for statement in Redis Stream
        stream_name = "xapi_statements"
        messages = redis_client.xread({stream_name: "0"}, count=1000)
        
        for stream, message_list in messages:
            for message_id, fields in message_list:
                if b'data' in fields:
                    data = json.loads(fields[b'data'].decode('utf-8'))
                    if data.get('id') == statement_id:
                        return {
                            "found": True,
                            "statement_id": statement_id,
                            "message_id": message_id,
                            "data": data
                        }
        
        return {
            "found": False,
            "statement_id": statement_id,
            "message": "Statement not found in queue"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"message": "Failed to retrieve statement status", "error": str(e)}
        )


# Helper functions for Testing Agent
def redis_client():
    """Get Redis client instance."""
    return get_redis_client()


def validate_statement(statement_data: Dict[str, Any]) -> xAPIStatement:
    """Validate xAPI statement data."""
    return validate_xapi_statement(statement_data)


def queue_statement(statement: xAPIStatement) -> str:
    """Queue statement to Redis Streams."""
    redis_client = get_redis_client()
    return queue_statement_to_redis(statement, redis_client)


def get_ingestion_stats() -> Dict[str, Any]:
    """Get ingestion statistics."""
    return ingestion_stats.copy()


def reset_ingestion_stats():
    """Reset ingestion statistics (for testing)."""
    global ingestion_stats
    ingestion_stats = {
        "total_statements": 0,
        "error_count": 0,
        "last_ingestion_time": None
    } 