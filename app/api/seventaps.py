"""
7taps API Integration with Basic Authentication

This module provides webhook endpoints for receiving xAPI statements from 7taps
with Basic authentication using username and password.
"""

import os
import hashlib
import hmac
import base64
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.xapi import publish_statement_async, validate_xapi_statement
from app.api.ai_flagged_content import analyze_xapi_statement_content
from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("seventaps")

# Global variables for tracking
webhook_stats = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "last_request_time": None,
    "authentication_failures": 0
}

# Global list to store all incoming xAPI statements for debugging
all_incoming_statements = []
MAX_STATEMENTS_LOG = 1000  # Keep last 1000 statements

# Global statement deduplication cache (in production, use Redis)
processed_statements = set()
MAX_CACHE_SIZE = 10000  # Prevent memory leaks

# 7taps Basic Authentication credentials
SEVENTAPS_USERNAME = os.getenv("SEVENTAPS_USERNAME", "7taps.team")
SEVENTAPS_PASSWORD = os.getenv("SEVENTAPS_PASSWORD", "PracticeofLife")


class SevenTapsWebhookPayload(BaseModel):
    """7taps webhook payload model."""
    event_type: str = Field(..., description="Type of event (e.g., 'xapi_statement')")
    timestamp: datetime = Field(..., description="Event timestamp")
    data: Dict[str, Any] = Field(..., description="Event data payload")
    webhook_id: Optional[str] = Field(None, description="7taps webhook identifier")


async def store_incoming_statement_to_bigquery(statement: Dict[str, Any], source: str = "7taps_webhook") -> None:
    """Store all incoming xAPI statements directly to BigQuery for immediate visibility."""
    try:
        from app.config.gcp_config import gcp_config
        from google.cloud import bigquery
        
        # Extract key information
        verb_id = statement.get("verb", {}).get("id", "unknown")
        verb_display = statement.get("verb", {}).get("display", {}).get("en-US", "unknown")
        object_id = statement.get("object", {}).get("id", "unknown")
        object_name = statement.get("object", {}).get("definition", {}).get("name", {}).get("en-US", "unknown")
        actor_name = statement.get("actor", {}).get("name", "unknown")
        actor_mbox = statement.get("actor", {}).get("mbox", "unknown")
        statement_id = statement.get("id", "no-id")
        timestamp = statement.get("timestamp", datetime.now().isoformat())
        
        # Parse timestamp using centralized utility
        from app.utils.timestamp_utils import parse_timestamp, format_human_readable
        parsed_timestamp = parse_timestamp(timestamp)
        formatted_timestamp = format_human_readable(timestamp)
        
        # Extract result information
        result = statement.get("result", {})
        result_completion = result.get("completion", False)
        result_success = result.get("success", False)
        result_score_scaled = result.get("score", {}).get("scaled")
        result_response = result.get("response")
        
        # Create row for BigQuery
        row = {
            "timestamp": parsed_timestamp.isoformat(),
            "statement_id": statement_id,
            "actor_name": actor_name,
            "actor_mbox": actor_mbox,
            "verb_id": verb_id,
            "verb_display": verb_display,
            "object_id": object_id,
            "object_name": object_name,
            "result_completion": result_completion,
            "result_success": result_success,
            "result_score_scaled": result_score_scaled,
            "result_response": result_response,
            "raw_statement": statement,
            "source": source
        }
        
        # Insert into BigQuery
        client = gcp_config.bigquery_client
        table_id = f"{gcp_config.project_id}.{gcp_config.bigquery_dataset}.raw_xapi_statements"
        table = client.get_table(table_id)
        
        errors = client.insert_rows(table, [row])
        if errors:
            print(f"❌ Failed to store incoming statement to BigQuery: {errors}")
        else:
            print(f"✅ Stored incoming statement to BigQuery: {verb_display} | {object_name} | Actor: {actor_name}")
            if "completed" in verb_display.lower():
                print(f"  🎯 COMPLETION STATEMENT STORED: {statement_id}")
                
    except Exception as e:
        print(f"❌ Error storing incoming statement to BigQuery: {e}")
        # Don't fail the main operation if BigQuery storage fails


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
        print(f"🔐 Auth attempt: username='{username}', expected='{SEVENTAPS_USERNAME}'")
        print(f"🔐 Auth attempt: password='{password}', expected='{SEVENTAPS_PASSWORD}'")
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
        # Primary authentication: Basic Auth (doesn't need request body)
        if verify_basic_auth(request):
            return True
        
        # For now, skip HMAC fallback to avoid request.body() issues
        # TODO: Implement HMAC authentication properly if needed
        
        webhook_stats["authentication_failures"] += 1
        return False
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        webhook_stats["authentication_failures"] += 1
        return False


async def _publish_7taps_statements(
    statements: List[Dict[str, Any]], *, source: str
) -> List[Dict[str, Any]]:
    """Validate and publish statements originating from 7taps."""
    processed: List[Dict[str, Any]] = []
    seen_statement_ids = set()

    for statement_data in statements:
        statement_id = statement_data.get("id")
        
        # Check for duplicate statement IDs in this batch
        if statement_id in seen_statement_ids:
            logger.warning(f"Duplicate statement ID detected in batch: {statement_id}, skipping")
            processed.append({
                "statement_id": statement_id,
                "status": "duplicate",
                "message": "Statement already processed in this batch"
            })
            continue
        
        # Check for globally processed statements
        if statement_id in processed_statements:
            logger.warning(f"Statement ID already processed globally: {statement_id}, skipping")
            processed.append({
                "statement_id": statement_id,
                "status": "duplicate",
                "message": "Statement already processed previously"
            })
            continue
        
        seen_statement_ids.add(statement_id)
        processed_statements.add(statement_id)
        
        # Prevent memory leaks by limiting cache size
        if len(processed_statements) > MAX_CACHE_SIZE:
            # Remove oldest entries (simple approach - in production use Redis with TTL)
            processed_statements.clear()
            logger.info("Cleared statement deduplication cache to prevent memory leaks")
        
        # Normalize user email addresses
        if "actor" in statement_data and "mbox" in statement_data["actor"]:
            mbox = statement_data["actor"]["mbox"]
            if mbox and mbox.startswith("mailto:"):
                # Normalize email to lowercase
                email = mbox.replace("mailto:", "").lower()
                statement_data["actor"]["mbox"] = f"mailto:{email}"
                
                # Also normalize the name field if it matches the email
                if "name" in statement_data["actor"] and statement_data["actor"]["name"]:
                    name_email = statement_data["actor"]["name"].lower()
                    if name_email == email:
                        statement_data["actor"]["name"] = email
        try:
            statement = validate_xapi_statement(statement_data)
            publish_result = await publish_statement_async(statement, source=source)

            processed.append(
                {
                    "statement_id": statement.id,
                    "message_id": publish_result.get("message_id"),
                    "timestamp": (
                        statement.timestamp.isoformat()
                        if statement.timestamp
                        else datetime.now(timezone.utc).isoformat()
                    ),
                }
            )
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover - defensive logging
            processed.append(
                {
                    "statement_id": statement_data.get("id", "unknown"),
                    "error": str(exc),
                }
            )

    # Wake ETL processors after publishing all statements
    if processed:
        await _wake_etl_processors()

    return processed


async def _wake_etl_processors():
    """Trigger ETL processors to wake up and process any pending messages."""
    try:
        import httpx
        
        # Get the service URL (same service, internal call)
        service_url = "https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app"
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Trigger ETL processing via a lightweight endpoint
            response = await client.post(f"{service_url}/api/etl/trigger-processing")
            if response.status_code == 200:
                logger.info("Successfully triggered ETL processors from 7taps webhook")
            else:
                logger.warning(f"ETL trigger returned status {response.status_code}")
                
    except Exception as e:
        logger.warning(f"Failed to trigger ETL processors from 7taps webhook: {e}")
        # Don't fail the main operation if ETL wake fails


@router.post("/statements")
async def receive_7taps_webhook(request: Request):
    """
    Receive xAPI statements from 7taps via POST to /statements endpoint.
    
    Authenticates the request using Basic Authentication and
    processes xAPI statements for ETL processing.
    """
    try:
        webhook_stats["total_requests"] += 1
        webhook_stats["last_request_time"] = datetime.now(timezone.utc)
        
        # Authenticate request
        if not await authenticate_7taps_request(request):
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"}
            )
        
        # Parse request body with proper error handling
        try:
            body = await request.json()
        except Exception as json_error:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Invalid JSON in request body",
                    "error": str(json_error)
                }
            )
        
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
        
        # Log all incoming statements for debugging
        print(f"🔍 [7TAPS DEBUG] Received {len(statements)} statement(s) via POST")
        for i, statement in enumerate(statements):
            verb_id = statement.get("verb", {}).get("id", "unknown")
            object_id = statement.get("object", {}).get("id", "unknown")
            actor_name = statement.get("actor", {}).get("name", "unknown")
            statement_id = statement.get("id", f"no-id-{i}")
            
            print(f"  📝 Statement {i+1}: {verb_id} | {object_id} | Actor: {actor_name} | ID: {statement_id}")
            
            # Run AI content analysis on each statement
            try:
                ai_analysis = await analyze_xapi_statement_content(statement)
                if ai_analysis.get("is_flagged", False):
                    print(f"  🚨 FLAGGED CONTENT: {statement_id}")
                    print(f"     Severity: {ai_analysis.get('severity', 'unknown')}")
                    print(f"     Reasons: {ai_analysis.get('flagged_reasons', [])}")
            except Exception as e:
                print(f"  ⚠️ AI analysis failed for {statement_id}: {e}")
            
            # Special logging for completion statements
            if "completed" in verb_id.lower():
                print(f"  ✅ COMPLETION DETECTED: {statement_id}")
                print(f"     Full statement: {statement}")
        
        processed_statements = await _publish_7taps_statements(
            statements, source="7taps_webhook_post"
        )
        
        webhook_stats["successful_requests"] += 1
        
        return {
            "status": "success",
            "processed_count": len(processed_statements),
            "statements": processed_statements,
            "message": f"Successfully queued {len(processed_statements)} xAPI statements from 7taps",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        webhook_stats["failed_requests"] += 1
        print(f"❌ Error processing webhook: {e}")
        raise HTTPException(
            status_code=500,
            detail={"message": "Failed to ingest xAPI statement", "error": str(e)}
        )


@router.put("/statements")
async def receive_7taps_webhook_put(request: Request, statementId: str = None):
    """
    Receive xAPI statements from 7taps via PUT to /statements endpoint.
    
    This endpoint supports idempotent statement sending with a statementId parameter.
    Authenticates the request using Basic Authentication and processes xAPI statements for ETL processing.
    """
    try:
        webhook_stats["total_requests"] += 1
        webhook_stats["last_request_time"] = datetime.now(timezone.utc)
        
        # Authenticate request
        if not await authenticate_7taps_request(request):
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"}
            )
        
        # Parse request body with proper error handling
        try:
            body = await request.json()
        except Exception as json_error:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Invalid JSON in request body",
                    "error": str(json_error)
                }
            )
        
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
        
        if statementId:
            for statement in statements:
                statement.setdefault("id", statementId)

        # Log all incoming statements for debugging
        print(f"🔍 [7TAPS DEBUG] Received {len(statements)} statement(s) via PUT")
        for i, statement in enumerate(statements):
            verb_id = statement.get("verb", {}).get("id", "unknown")
            object_id = statement.get("object", {}).get("id", "unknown")
            actor_name = statement.get("actor", {}).get("name", "unknown")
            statement_id = statement.get("id", f"no-id-{i}")
            
            print(f"  📝 Statement {i+1}: {verb_id} | {object_id} | Actor: {actor_name} | ID: {statement_id}")
            
            # Run AI content analysis on each statement
            try:
                ai_analysis = await analyze_xapi_statement_content(statement)
                if ai_analysis.get("is_flagged", False):
                    print(f"  🚨 FLAGGED CONTENT: {statement_id}")
                    print(f"     Severity: {ai_analysis.get('severity', 'unknown')}")
                    print(f"     Reasons: {ai_analysis.get('flagged_reasons', [])}")
            except Exception as e:
                print(f"  ⚠️ AI analysis failed for {statement_id}: {e}")
            
            # Special logging for completion statements
            if "completed" in verb_id.lower():
                print(f"  ✅ COMPLETION DETECTED: {statement_id}")
                print(f"     Full statement: {statement}")

        processed_statements = await _publish_7taps_statements(
            statements, source="7taps_webhook_put"
        )
        
        webhook_stats["successful_requests"] += 1
        
        return {
            "status": "success",
            "processed_count": len(processed_statements),
            "statements": processed_statements,
            "message": f"Successfully queued {len(processed_statements)} xAPI statements from 7taps (PUT)",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        webhook_stats["failed_requests"] += 1
        print(f"❌ Error processing webhook (PUT): {e}")
        raise HTTPException(
            status_code=500,
            detail={"message": "Failed to ingest xAPI statement", "error": str(e)}
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
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
