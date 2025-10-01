"""
xAPI Learning Record Store (LRS) endpoint.

This module implements a standard xAPI LRS that accepts statements
via Basic Authentication and follows the xAPI specification.
"""

import os
import json
import base64
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.api.xapi import publish_statement_async, validate_xapi_statement

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
    authority: Optional[Dict[str, Any]] = Field(None, description="Authority for the statement")
    version: Optional[str] = Field("1.0.3", description="xAPI version")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="Attachments")
    context: Optional[Dict[str, Any]] = Field(None, description="Context of the statement")
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
        credentials = base64.b64decode(auth_header[6:]).decode('utf-8')
        username, password = credentials.split(':', 1)
        
        # Verify credentials
        return username == LRS_USERNAME and password == LRS_PASSWORD
        
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return False

@router.post("/statements")
async def post_statements(
    request: Request,
    statements: List[xAPIStatement]
):
    """
    Accept xAPI statements via POST to /statements endpoint.
    
    This follows the xAPI specification for statement posting.
    """
    # Verify Basic Authentication
    if not verify_basic_auth(request):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"}
        )
    
    try:
        processed_statements = []

        for statement in statements:
            statement_payload = statement.model_dump()
            validated_statement = validate_xapi_statement(statement_payload)

            if not validated_statement.id:
                validated_statement.id = str(uuid.uuid4())
            if not validated_statement.timestamp:
                validated_statement.timestamp = datetime.now(timezone.utc)
            if not validated_statement.stored:
                validated_statement.stored = datetime.now(timezone.utc)

            publish_result = await publish_statement_async(
                validated_statement, source="xapi_lrs_post"
            )

            processed_statements.append(
                {
                    "statement_id": validated_statement.id,
                    "message_id": publish_result.get("message_id"),
                    "timestamp": (
                        validated_statement.timestamp.isoformat()
                        if isinstance(validated_statement.timestamp, datetime)
                        else validated_statement.timestamp
                    ),
                }
            )

            logger.info(
                "Published xAPI statement %s to Pub/Sub via LRS", validated_statement.id
            )

        return {
            "status": "success",
            "processed_count": len(processed_statements),
            "statements": processed_statements,
            "message": f"Successfully published {len(processed_statements)} xAPI statements",
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error processing xAPI statements: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing statements: {str(exc)}",
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
    ascending: Optional[bool] = False
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
            headers={"WWW-Authenticate": "Basic"}
        )
    
    try:
        # For now, return a simple response indicating the endpoint is working
        # In a full implementation, this would query the database for statements
        return {
            "statements": [],
            "more": "",
            "message": "xAPI LRS statements endpoint is working"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving xAPI statements: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving statements: {str(e)}"
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
            headers={"WWW-Authenticate": "Basic"}
        )
    
    return {
        "version": ["1.0.3"],
        "extensions": {
            "http://id.tincanapi.com/extension/activity-type": {
                "type": "http://www.adlnet.gov/expapi/activities/course"
            }
        }
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
            headers={"WWW-Authenticate": "Basic"}
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
            headers={"WWW-Authenticate": "Basic"}
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
            headers={"WWW-Authenticate": "Basic"}
        )
    
    return {"message": "Agent profile endpoint (placeholder)"} 
