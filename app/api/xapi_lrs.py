"""
xAPI Learning Record Store (LRS) endpoint.

This module implements a standard xAPI LRS that accepts statements
via Basic Authentication and follows the xAPI specification.
"""

import base64
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


# xAPI Statement model
class xAPIStatement(BaseModel):
    """xAPI Statement model following the specification."""

    id: Optional[str] = Field(None, description="Statement ID")
    actor: Dict[str, Any] = Field(..., description="Actor performing the action")
    verb: Dict[str, Any] = Field(..., description="Action being performed")
    object: Dict[str, Any] = Field(..., description="Object of the action")
    timestamp: Optional[str] = Field(None, description="Timestamp of the statement")
    stored: Optional[str] = Field(None, description="When the statement was stored")
    authority: Optional[Dict[str, Any]] = Field(
        None, description="Authority for the statement"
    )
    version: Optional[str] = Field("1.0.3", description="xAPI version")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="Attachments")
    context: Optional[Dict[str, Any]] = Field(
        None, description="Context of the statement"
    )
    result: Optional[Dict[str, Any]] = Field(None, description="Result of the action")


# LRS Configuration
LRS_USERNAME = os.getenv("XAPI_LRS_USERNAME", "7taps_user")
LRS_PASSWORD = os.getenv("XAPI_LRS_PASSWORD", "7taps_password_2025")


def verify_basic_auth(request: Request) -> bool:
    """
    Verify Basic Authentication credentials.

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
        credentials = base64.b64decode(auth_header[6:]).decode("utf-8")
        username, password = credentials.split(":", 1)

        # Verify credentials
        return username == LRS_USERNAME and password == LRS_PASSWORD

    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return False


def get_redis_client():
    """Get Redis client for statement queuing."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    return redis.from_url(redis_url, ssl_cert_reqs=None, decode_responses=True)


@router.post("/statements")
async def post_statements(request: Request, statements: List[xAPIStatement]):
    """
    Accept xAPI statements via POST to /statements endpoint.

    This follows the xAPI specification for statement posting.
    """
    # Verify Basic Authentication
    if not verify_basic_auth(request):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    try:
        redis_client = get_redis_client()
        stream_name = "xapi_statements"

        processed_statements = []

        for statement in statements:
            # Generate statement ID if not provided
            if not statement.id:
                import uuid

                statement.id = str(uuid.uuid4())

            # Add timestamp if not provided
            if not statement.timestamp:
                statement.timestamp = datetime.utcnow().isoformat()

            # Add stored timestamp
            statement.stored = datetime.utcnow().isoformat()

            # Convert to dict for Redis
            statement_dict = statement.dict()

            # Add to Redis Stream
            message_id = redis_client.xadd(
                stream_name,
                {"data": json.dumps(statement_dict)},
                maxlen=10000,  # Keep last 10,000 statements
            )

            processed_statements.append(
                {
                    "statement_id": statement.id,
                    "message_id": message_id,
                    "timestamp": statement.timestamp,
                }
            )

            logger.info(f"Queued xAPI statement {statement.id} to Redis")

        return {
            "status": "success",
            "processed_count": len(processed_statements),
            "statements": processed_statements,
            "message": f"Successfully queued {len(processed_statements)} xAPI statements",
        }

    except Exception as e:
        logger.error(f"Error processing xAPI statements: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error processing statements: {str(e)}"
        )


@router.get("/statements")
async def get_statements(
    request: Request,
    statementId: Optional[str] = None,
    voidedStatementId: Optional[str] = None,
    agent: Optional[str] = None,
    verb: Optional[str] = None,
    activity: Optional[str] = None,
    registration: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: Optional[int] = 100,
    format: Optional[str] = "exact",
    attachments: Optional[bool] = False,
    ascending: Optional[bool] = False,
):
    """
    Retrieve xAPI statements via GET to /statements endpoint.

    This follows the xAPI specification for statement retrieval.
    """
    # Verify Basic Authentication
    if not verify_basic_auth(request):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    try:
        # For now, return a simple response indicating the endpoint is working
        # In a full implementation, this would query the database for statements
        return {
            "statements": [],
            "more": "",
            "message": "xAPI LRS statements endpoint is working",
        }

    except Exception as e:
        logger.error(f"Error retrieving xAPI statements: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving statements: {str(e)}"
        )


@router.get("/about")
async def get_about(request: Request):
    """
    Get xAPI LRS information.

    This follows the xAPI specification for the about endpoint.
    """
    # Verify Basic Authentication
    if not verify_basic_auth(request):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return {
        "version": ["1.0.3"],
        "extensions": {
            "http://id.tincanapi.com/extension/activity-type": {
                "type": "http://www.adlnet.gov/expapi/activities/course"
            }
        },
    }


@router.get("/activities/state")
async def get_activities_state(request: Request):
    """
    Get activity state (placeholder for xAPI specification).
    """
    # Verify Basic Authentication
    if not verify_basic_auth(request):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return {"message": "Activity state endpoint (placeholder)"}


@router.get("/activities/profile")
async def get_activities_profile(request: Request):
    """
    Get activity profile (placeholder for xAPI specification).
    """
    # Verify Basic Authentication
    if not verify_basic_auth(request):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return {"message": "Activity profile endpoint (placeholder)"}


@router.get("/agents/profile")
async def get_agents_profile(request: Request):
    """
    Get agent profile (placeholder for xAPI specification).
    """
    # Verify Basic Authentication
    if not verify_basic_auth(request):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return {"message": "Agent profile endpoint (placeholder)"}
