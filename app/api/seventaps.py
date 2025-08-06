"""
7taps API Integration with Basic Authentication

This module provides webhook endpoints for receiving xAPI statements from 7taps
with Basic authentication using username and password.
"""

import os
import json
import hashlib
import hmac
import base64
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import httpx

# Import xAPI models
from app.models import xAPIStatement, xAPIIngestionResponse

router = APIRouter()

# Global variables for tracking
webhook_stats = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "last_request_time": None,
    "authentication_failures": 0
}

# 7taps Basic Authentication credentials
SEVENTAPS_USERNAME = os.getenv("SEVENTAPS_USERNAME", "7taps_user")
SEVENTAPS_PASSWORD = os.getenv("SEVENTAPS_PASSWORD", "7taps_password_2025")


class SevenTapsWebhookPayload(BaseModel):
    """7taps webhook payload model."""
    event_type: str = Field(..., description="Type of event (e.g., 'xapi_statement')")
    timestamp: datetime = Field(..., description="Event timestamp")
    data: Dict[str, Any] = Field(..., description="Event data payload")
    webhook_id: Optional[str] = Field(None, description="7taps webhook identifier")


def verify_basic_auth(request: Request) -> bool:
    """
    Verify Basic Authentication credentials for 7taps webhook.
    
    Args:
        request: FastAPI request object
        
    Returns:
        True if authentication successful, False otherwise
    """
    try:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Basic "):
            return False
        
        # Decode credentials
        credentials = base64.b64decode(auth_header[6:]).decode('utf-8')
        username, password = credentials.split(':', 1)
        
        # Verify credentials
        return username == SEVENTAPS_USERNAME and password == SEVENTAPS_PASSWORD
        
    except Exception as e:
        print(f"7taps authentication error: {e}")
        return False


def verify_webhook_secret(request_body: str, signature: str) -> bool:
    """
    Verify webhook secret using HMAC (fallback method).
    
    Args:
        request_body: Request body as string
        signature: HMAC signature to verify
        
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        webhook_secret = os.getenv("SEVENTAPS_WEBHOOK_SECRET", "")
        if not webhook_secret:
            return False
        
        # Calculate expected signature
        expected_signature = hmac.new(
            webhook_secret.encode(),
            request_body.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
        
    except Exception as e:
        print(f"Webhook secret verification failed: {e}")
        return False


async def authenticate_7taps_request(request: Request) -> bool:
    """
    Authenticate 7taps webhook request using Basic Authentication.
    
    Args:
        request: FastAPI request object
        
    Returns:
        True if authentication successful, False otherwise
    """
    try:
        # Primary authentication: Basic Auth
        if verify_basic_auth(request):
            return True
        
        # Fallback: HMAC webhook secret (if configured)
        body = await request.body()
        body_str = body.decode('utf-8')
        signature = request.headers.get("X-7taps-Signature", "")
        
        if signature and verify_webhook_secret(body_str, signature):
            return True
        
        webhook_stats["authentication_failures"] += 1
        return False
        
    except Exception as e:
        print(f"Authentication error: {e}")
        webhook_stats["authentication_failures"] += 1
        return False


@router.post("/statements")
async def receive_7taps_webhook(request: Request):
    """
    Receive xAPI statements from 7taps via POST to /statements endpoint.
    
    Authenticates the request using Basic Authentication and
    processes xAPI statements for ETL processing.
    """
    try:
        webhook_stats["total_requests"] += 1
        webhook_stats["last_request_time"] = datetime.utcnow()
        
        # Authenticate request
        if not await authenticate_7taps_request(request):
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"}
            )
        
        # Parse request body
        body = await request.json()
        
        # Handle both single statement and array of statements
        if isinstance(body, list):
            statements = body
        else:
            # Single statement or webhook payload
            if "event_type" in body and body.get("event_type") == "xapi_statement":
                # Webhook format
                statements = [body.get("data", {})]
            else:
                # Direct xAPI statement
                statements = [body]
        
        processed_statements = []
        
        for statement_data in statements:
            # Log the xAPI statement
            print(f"🎉 xAPI STATEMENT RECEIVED: {statement_data}")
            
            # Queue xAPI statement to Redis Streams for ETL processing
            try:
                import redis
                import uuid
                
                # Get Redis client with SSL configuration
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
                redis_client = redis.from_url(
                    redis_url,
                    ssl_cert_reqs=None,  # Disable SSL certificate verification for Heroku Redis
                    decode_responses=True
                )
                
                # Prepare statement data for Redis
                statement_id = statement_data.get("id", str(uuid.uuid4()))
                statement_data["id"] = statement_id
                
                # Add metadata
                statement_data["webhook_source"] = "7taps"
                statement_data["ingested_at"] = datetime.utcnow().isoformat()
                
                # Add to Redis Stream
                stream_name = "xapi_statements"
                message_id = redis_client.xadd(
                    stream_name,
                    {"data": json.dumps(statement_data)},
                    maxlen=10000  # Keep last 10k messages
                )
                
                print(f"✅ xAPI statement queued to Redis Stream: {message_id}")
                
                processed_statements.append({
                    "statement_id": statement_id,
                    "message_id": message_id,
                    "timestamp": statement_data.get("timestamp", datetime.utcnow().isoformat())
                })
                
            except Exception as e:
                print(f"❌ Error queuing to Redis: {e}")
                processed_statements.append({
                    "statement_id": statement_data.get("id", "unknown"),
                    "error": str(e)
                })
        
        webhook_stats["successful_requests"] += 1
        
        return {
            "status": "success",
            "processed_count": len(processed_statements),
            "statements": processed_statements,
            "message": f"Successfully queued {len(processed_statements)} xAPI statements from 7taps",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        webhook_stats["failed_requests"] += 1
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process statements: {str(e)}"
        )


@router.get("/api/7taps/keys")
async def get_7taps_auth_info():
    """
    Get 7taps authentication information and status.
    """
    try:
        auth_info = {
            "authentication_method": "Basic Authentication",
            "username": SEVENTAPS_USERNAME,
            "password_configured": bool(SEVENTAPS_PASSWORD),
            "authentication_enabled": True,
            "webhook_secret_configured": bool(os.getenv("SEVENTAPS_WEBHOOK_SECRET")),
            "environment_variables": {
                "SEVENTAPS_USERNAME": SEVENTAPS_USERNAME,
                "SEVENTAPS_PASSWORD": "configured" if SEVENTAPS_PASSWORD else "not_set",
                "SEVENTAPS_WEBHOOK_SECRET": "configured" if os.getenv("SEVENTAPS_WEBHOOK_SECRET") else "not_set"
            },
            "authentication_headers": {
                "Authorization": "Basic <base64-encoded-credentials>"
            },
            "fallback_method": "HMAC webhook secret (if configured)",
            "message": "7taps webhook uses Basic Authentication with username/password"
        }
        
        return auth_info
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get authentication information: {str(e)}"
        )


@router.get("/api/7taps/webhook-stats")
async def get_webhook_stats():
    """
    Get webhook processing statistics.
    """
    return {
        "webhook_stats": webhook_stats,
        "timestamp": datetime.utcnow().isoformat(),
        "success_rate": (
            webhook_stats["successful_requests"] / webhook_stats["total_requests"]
            if webhook_stats["total_requests"] > 0 else 0
        )
    }


# Helper functions for Testing Agent
def verify_basic_auth_helper(request: Request) -> bool:
    """Verify Basic Authentication for testing."""
    return verify_basic_auth(request)


def get_webhook_statistics() -> Dict[str, Any]:
    """Get webhook statistics for testing."""
    return webhook_stats.copy()


def reset_webhook_stats():
    """Reset webhook statistics for testing."""
    global webhook_stats
    webhook_stats = {
        "total_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "last_request_time": None,
        "authentication_failures": 0
    } 