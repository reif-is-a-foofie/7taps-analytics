"""
User Matching UI for manually matching orphaned statements to users.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from app.logging_config import get_logger
from app.config.gcp_config import get_gcp_config

logger = get_logger("user_matching")
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


class MatchStatementRequest(BaseModel):
    statement_id: str
    user_id: str


@router.get("/user-matching", response_class=HTMLResponse)
async def user_matching_page(request: Request) -> HTMLResponse:
    """User matching page for manually matching users."""
    context = {
        "request": request,
        "active_page": "user_matching",
        "title": "User Matching"
    }
    return templates.TemplateResponse("user_matching.html", context)


@router.get("/user-matching/data")
async def get_orphaned_statements() -> JSONResponse:
    """Get orphaned statements (statements without matched users)."""
    try:
        gcp_config = get_gcp_config()
        client = gcp_config.bigquery_client
        dataset_id = gcp_config.bigquery_dataset
        
        # Get orphaned statements (where normalized_user_id is NULL or empty)
        # Check both possible table names
        orphaned_query = f"""
        SELECT 
            statement_id,
            timestamp,
            actor_id,
            actor_name,
            verb_display,
            object_name,
            object_id,
            result_response,
            normalized_user_id
        FROM `{dataset_id}.statements`
        WHERE (normalized_user_id IS NULL OR normalized_user_id = '')
            AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
        ORDER BY timestamp DESC
        LIMIT 100
        """
        
        # Get all users for dropdown
        users_query = f"""
        SELECT 
            user_id,
            email,
            name,
            activity_count,
            first_seen,
            last_seen
        FROM `{dataset_id}.users`
        ORDER BY name ASC, email ASC
        LIMIT 500
        """
        
        # Execute queries
        orphaned_results = list(client.query(orphaned_query).result())
        users_results = list(client.query(users_query).result())
        
        # Format orphaned statements
        orphaned_statements = []
        for row in orphaned_results:
            orphaned_statements.append({
                "statement_id": row.statement_id,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                "actor_id": row.actor_id,
                "actor_name": row.actor_name or "Unknown",
                "verb": row.verb_display or "Unknown",
                "object_name": row.object_name or row.object_id or "Unknown",
                "response": row.result_response[:100] if row.result_response else None,
            })
        
        # Format users for dropdown
        users = []
        for row in users_results:
            display_name = f"{row.name or 'Unknown'}"
            if row.email:
                display_name += f" ({row.email})"
            users.append({
                "user_id": row.user_id,
                "email": row.email,
                "name": row.name,
                "display_name": display_name,
                "activity_count": row.activity_count or 0,
            })
        
        return JSONResponse({
            "success": True,
            "orphaned_count": len(orphaned_statements),
            "orphaned_statements": orphaned_statements,
            "users": users
        })
        
    except Exception as e:
        logger.error(f"Error getting orphaned statements: {e}")
        return JSONResponse({
            "success": False,
            "message": str(e)
        }, status_code=500)


@router.post("/user-matching/match")
async def match_statement_to_user(request: MatchStatementRequest) -> JSONResponse:
    """Match an orphaned statement to a user."""
    try:
        gcp_config = get_gcp_config()
        client = gcp_config.bigquery_client
        dataset_id = gcp_config.bigquery_dataset
        
        statement_id = request.statement_id.strip()
        user_id = request.user_id.strip()
        
        # Verify statement exists and is orphaned
        check_statement_query = f"""
        SELECT 
            statement_id,
            normalized_user_id,
            actor_id,
            actor_name
        FROM `{dataset_id}.statements`
        WHERE statement_id = '{statement_id}'
        """
        
        statement_results = list(client.query(check_statement_query).result())
        
        if not statement_results:
            return JSONResponse({
                "success": False,
                "message": "Statement not found"
            }, status_code=404)
        
        statement = statement_results[0]
        
        if statement.normalized_user_id and statement.normalized_user_id.strip():
            return JSONResponse({
                "success": False,
                "message": f"Statement already matched to user: {statement.normalized_user_id}"
            }, status_code=400)
        
        # Verify user exists
        check_user_query = f"""
        SELECT 
            user_id,
            email,
            name
        FROM `{dataset_id}.users`
        WHERE user_id = '{user_id}'
        """
        
        user_results = list(client.query(check_user_query).result())
        
        if not user_results:
            return JSONResponse({
                "success": False,
                "message": "User not found"
            }, status_code=404)
        
        user = user_results[0]
        
        # Update statement with normalized_user_id
        update_query = f"""
        UPDATE `{dataset_id}.statements`
        SET normalized_user_id = '{user_id}'
        WHERE statement_id = '{statement_id}'
        """
        
        client.query(update_query)
        
        logger.info(f"Matched statement {statement_id} to user {user_id} ({user.email or user.name})")
        
        return JSONResponse({
            "success": True,
            "message": f"Statement matched to {user.name or user.email or user_id}"
        })
        
    except Exception as e:
        logger.error(f"Error matching statement: {e}")
        return JSONResponse({
            "success": False,
            "message": str(e)
        }, status_code=500)
