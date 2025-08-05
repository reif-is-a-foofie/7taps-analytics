"""
7taps API Integration with PEM Key Authentication

This module provides webhook endpoints for receiving xAPI statements from 7taps
with RSA signature verification for secure authentication.
"""

import os
import json
import hashlib
import hmac
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


class SevenTapsWebhookPayload(BaseModel):
    """7taps webhook payload model."""
    event_type: str = Field(..., description="Type of event (e.g., 'xapi_statement')")
    timestamp: datetime = Field(..., description="Event timestamp")
    data: Dict[str, Any] = Field(..., description="Event data payload")
    signature: Optional[str] = Field(None, description="RSA signature for verification")
    webhook_id: Optional[str] = Field(None, description="7taps webhook identifier")


class SevenTapsKeyInfo(BaseModel):
    """7taps key information model."""
    public_key_path: str = Field(..., description="Path to public key file")
    private_key_path: str = Field(..., description="Path to private key file")
    key_size: int = Field(..., description="RSA key size in bits")
    generated_at: datetime = Field(..., description="Key generation timestamp")
    is_valid: bool = Field(..., description="Key validity status")


def get_private_key_path() -> str:
    """Get private key path from environment."""
    return os.getenv("SEVENTAPS_PRIVATE_KEY_PATH", "keys/7taps_private_key.pem")


def get_public_key_path() -> str:
    """Get public key path from environment."""
    return os.getenv("SEVENTAPS_PUBLIC_KEY_PATH", "keys/7taps_public_key.pem")


def verify_7taps_signature(payload: bytes, signature: str, public_key_path: str) -> bool:
    """
    Verify 7taps webhook signature using RSA.
    
    Args:
        payload: Request payload bytes
        signature: RSA signature to verify
        public_key_path: Path to public key file
        
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        
        # Load public key
        with open(public_key_path, 'rb') as f:
            public_key = serialization.load_pem_public_key(f.read())
        
        # Verify signature
        public_key.verify(
            signature.encode(),
            payload,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
        
    except Exception as e:
        print(f"Signature verification failed: {e}")
        return False


def verify_webhook_secret(request_body: str, signature: str) -> bool:
    """
    Verify webhook secret using HMAC.
    
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
    Authenticate 7taps webhook request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        True if authentication successful, False otherwise
    """
    try:
        # Get request body
        body = await request.body()
        body_str = body.decode('utf-8')
        
        # Get signature from headers
        signature = request.headers.get("X-7taps-Signature", "")
        if not signature:
            webhook_stats["authentication_failures"] += 1
            return False
        
        # Verify webhook secret first
        if not verify_webhook_secret(body_str, signature):
            webhook_stats["authentication_failures"] += 1
            return False
        
        # Verify RSA signature if enabled
        verify_rsa = os.getenv("SEVENTAPS_VERIFY_SIGNATURE", "true").lower() == "true"
        if verify_rsa:
            public_key_path = get_public_key_path()
            if not verify_7taps_signature(body, signature, public_key_path):
                webhook_stats["authentication_failures"] += 1
                return False
        
        return True
        
    except Exception as e:
        print(f"Authentication error: {e}")
        webhook_stats["authentication_failures"] += 1
        return False


@router.post("/api/7taps/webhook")
async def receive_7taps_webhook(request: Request):
    """
    Receive webhook from 7taps with xAPI statements.
    
    Authenticates the request using PEM key verification and
    processes xAPI statements for ETL processing.
    """
    try:
        webhook_stats["total_requests"] += 1
        webhook_stats["last_request_time"] = datetime.utcnow()
        
        # Authenticate request
        if not await authenticate_7taps_request(request):
            raise HTTPException(
                status_code=401,
                detail="Invalid webhook signature"
            )
        
        # Parse request body
        body = await request.json()
        webhook_payload = SevenTapsWebhookPayload(**body)
        
        # Process xAPI statement if present
        if webhook_payload.event_type == "xapi_statement":
            xapi_data = webhook_payload.data
            
            # Validate xAPI statement
            try:
                statement = xAPIStatement(**xapi_data)
                
                # Queue to Redis for ETL processing
                from app.api.xapi import queue_statement_to_redis, get_redis_client
                redis_client = get_redis_client()
                message_id = queue_statement_to_redis(statement, redis_client)
                
                webhook_stats["successful_requests"] += 1
                
                return {
                    "success": True,
                    "message": "xAPI statement received and queued",
                    "message_id": message_id,
                    "statement_id": statement.id,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                webhook_stats["failed_requests"] += 1
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid xAPI statement: {str(e)}"
                )
        
        # Handle other event types
        webhook_stats["successful_requests"] += 1
        return {
            "success": True,
            "message": f"Event {webhook_payload.event_type} received",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        webhook_stats["failed_requests"] += 1
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process webhook: {str(e)}"
        )


@router.get("/api/7taps/keys")
async def get_7taps_key_info():
    """
    Get 7taps key information and status.
    """
    try:
        private_key_path = get_private_key_path()
        public_key_path = get_public_key_path()
        
        # Check if keys exist
        private_exists = os.path.exists(private_key_path)
        public_exists = os.path.exists(public_key_path)
        
        # Get key information
        key_info = {
            "private_key_path": private_key_path,
            "public_key_path": public_key_path,
            "private_key_exists": private_exists,
            "public_key_exists": public_exists,
            "authentication_enabled": os.getenv("SEVENTAPS_AUTH_ENABLED", "true").lower() == "true",
            "signature_verification": os.getenv("SEVENTAPS_VERIFY_SIGNATURE", "true").lower() == "true",
            "webhook_secret_configured": bool(os.getenv("SEVENTAPS_WEBHOOK_SECRET")),
            "environment_variables": {
                "SEVENTAPS_PRIVATE_KEY_PATH": private_key_path,
                "SEVENTAPS_PUBLIC_KEY_PATH": public_key_path,
                "SEVENTAPS_WEBHOOK_SECRET": "configured" if os.getenv("SEVENTAPS_WEBHOOK_SECRET") else "not_set",
                "SEVENTAPS_AUTH_ENABLED": os.getenv("SEVENTAPS_AUTH_ENABLED", "true"),
                "SEVENTAPS_VERIFY_SIGNATURE": os.getenv("SEVENTAPS_VERIFY_SIGNATURE", "true")
            }
        }
        
        # Get key details if they exist
        if private_exists and public_exists:
            try:
                from cryptography.hazmat.primitives import serialization
                
                # Load private key to get key size
                with open(private_key_path, 'rb') as f:
                    private_key = serialization.load_pem_private_key(f.read(), password=None)
                    key_info["key_size"] = private_key.key_size
                    key_info["key_type"] = "RSA"
                    key_info["generated_at"] = datetime.fromtimestamp(
                        os.path.getctime(private_key_path)
                    ).isoformat()
                    
            except Exception as e:
                key_info["key_size"] = "unknown"
                key_info["error"] = str(e)
        
        return key_info
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get key information: {str(e)}"
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
def generate_key_pair(key_size: int = 2048) -> tuple:
    """Generate RSA key pair for testing."""
    from scripts.generate_pem_keys import generate_rsa_key_pair
    return generate_rsa_key_pair(key_size)


def verify_signature(payload: bytes, signature: str, public_key_path: str) -> bool:
    """Verify signature for testing."""
    return verify_7taps_signature(payload, signature, public_key_path)


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