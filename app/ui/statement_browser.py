"""
Statement Browser UI for Learning Locker.

This module provides a statement browser interface with filtering,
search, and pagination for xAPI statements.
"""

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, List, Optional
import httpx
import json
from datetime import datetime
import os

from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("statement_browser")
templates = Jinja2Templates(directory="templates")

class StatementBrowser:
    """Statement browser interface."""
    
    def __init__(self):
        self.api_base = os.getenv("API_BASE_URL", "") + "/api"
        
    async def get_statements(self, 
                           page: int = 1, 
                           limit: int = 20,
                           actor_filter: Optional[str] = None,
                           verb_filter: Optional[str] = None,
                           object_filter: Optional[str] = None,
                           search_query: Optional[str] = None) -> Dict[str, Any]:
        """Get xAPI statements with filtering and pagination."""
        try:
            # Mock statement data for demonstration
            # In production, this would query the database
            statements = [
                {
                    "id": "statement-001",
                    "actor": {
                        "account": {"name": "user1@7taps.com"}
                    },
                    "verb": {
                        "id": "http://adlnet.gov/expapi/verbs/completed"
                    },
                    "object": {
                        "id": "http://7taps.com/activities/course-1",
                        "objectType": "Activity"
                    },
                    "timestamp": "2025-01-05T10:30:00Z",
                    "result": {
                        "score": {"raw": 85, "min": 0, "max": 100}
                    }
                },
                {
                    "id": "statement-002",
                    "actor": {
                        "account": {"name": "user2@7taps.com"}
                    },
                    "verb": {
                        "id": "http://adlnet.gov/expapi/verbs/attempted"
                    },
                    "object": {
                        "id": "http://7taps.com/activities/quiz-1",
                        "objectType": "Activity"
                    },
                    "timestamp": "2025-01-05T11:15:00Z",
                    "result": {
                        "success": True
                    }
                },
                {
                    "id": "statement-003",
                    "actor": {
                        "account": {"name": "user3@7taps.com"}
                    },
                    "verb": {
                        "id": "http://adlnet.gov/expapi/verbs/experienced"
                    },
                    "object": {
                        "id": "http://7taps.com/activities/video-1",
                        "objectType": "Activity"
                    },
                    "timestamp": "2025-01-05T12:00:00Z"
                }
            ]
            
            # Apply filters
            if actor_filter:
                statements = [s for s in statements if actor_filter.lower() in s.get("actor", {}).get("account", {}).get("name", "").lower()]
            
            if verb_filter:
                statements = [s for s in statements if verb_filter.lower() in s.get("verb", {}).get("id", "").lower()]
            
            if object_filter:
                statements = [s for s in statements if object_filter.lower() in s.get("object", {}).get("id", "").lower()]
            
            if search_query:
                search_lower = search_query.lower()
                statements = [s for s in statements if 
                           search_lower in json.dumps(s).lower()]
            
            # Pagination
            total_count = len(statements)
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_statements = statements[start_idx:end_idx]
            
            return {
                "statements": paginated_statements,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_count": total_count,
                    "total_pages": (total_count + limit - 1) // limit,
                    "has_next": end_idx < total_count,
                    "has_prev": page > 1
                },
                "filters": {
                    "actor": actor_filter,
                    "verb": verb_filter,
                    "object": object_filter,
                    "search": search_query
                }
            }
            
        except Exception as e:
            logger.error("Failed to get statements", error=e)
            return {"error": str(e)}
    
    async def get_statement_detail(self, statement_id: str) -> Dict[str, Any]:
        """Get detailed view of a specific statement."""
        try:
            # Mock statement detail
            statement = {
                "id": statement_id,
                "actor": {
                    "account": {"name": "user1@7taps.com"},
                    "name": "Test User"
                },
                "verb": {
                    "id": "http://adlnet.gov/expapi/verbs/completed",
                    "display": {"en-US": "completed"}
                },
                "object": {
                    "id": "http://7taps.com/activities/course-1",
                    "objectType": "Activity",
                    "definition": {
                        "name": {"en-US": "Introduction Course"},
                        "description": {"en-US": "Basic introduction to the platform"}
                    }
                },
                "timestamp": "2025-01-05T10:30:00Z",
                "result": {
                    "score": {"raw": 85, "min": 0, "max": 100},
                    "success": True,
                    "completion": True
                },
                "context": {
                    "platform": "7taps",
                    "language": "en-US"
                }
            }
            
            return statement
            
        except Exception as e:
            logger.error("Failed to get statement detail", error=e)
            return {"error": str(e)}
    
    async def get_statement_stats(self) -> Dict[str, Any]:
        """Get statement statistics."""
        try:
            # Mock statistics
            stats = {
                "total_statements": 1250,
                "statements_today": 45,
                "unique_actors": 89,
                "unique_activities": 23,
                "completion_rate": 78.5,
                "average_score": 82.3,
                "top_verbs": [
                    {"verb": "completed", "count": 450},
                    {"verb": "attempted", "count": 320},
                    {"verb": "experienced", "count": 280}
                ],
                "top_activities": [
                    {"activity": "course-1", "count": 120},
                    {"activity": "quiz-1", "count": 95},
                    {"activity": "video-1", "count": 87}
                ]
            }
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get statement stats", error=e)
            return {"error": str(e)}

# Global browser instance
browser = StatementBrowser()

@router.get("/statement-browser", response_class=HTMLResponse)
async def statement_browser_page(request: Request,
                               page: int = Query(1, ge=1),
                               limit: int = Query(20, ge=1, le=100),
                               actor: Optional[str] = Query(None),
                               verb: Optional[str] = Query(None),
                               object: Optional[str] = Query(None),
                               search: Optional[str] = Query(None)):
    """Statement browser main page."""
    try:
        data = await browser.get_statements(
            page=page,
            limit=limit,
            actor_filter=actor,
            verb_filter=verb,
            object_filter=object,
            search_query=search
        )
        
        stats = await browser.get_statement_stats()
        
        context = {
            "request": request,
            "data": data,
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return templates.TemplateResponse("statement_browser.html", context)
        
    except Exception as e:
        logger.error("Failed to render statement browser", error=e)
        raise HTTPException(status_code=500, detail=f"Browser error: {str(e)}")

@router.get("/api/statements")
async def get_statements_api(page: int = Query(1, ge=1),
                           limit: int = Query(20, ge=1, le=100),
                           actor: Optional[str] = Query(None),
                           verb: Optional[str] = Query(None),
                           object: Optional[str] = Query(None),
                           search: Optional[str] = Query(None)):
    """API endpoint for getting statements."""
    try:
        data = await browser.get_statements(
            page=page,
            limit=limit,
            actor_filter=actor,
            verb_filter=verb,
            object_filter=object,
            search_query=search
        )
        return data
    except Exception as e:
        logger.error("Failed to get statements via API", error=e)
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")

@router.get("/api/statements/{statement_id}")
async def get_statement_detail_api(statement_id: str):
    """API endpoint for getting statement detail."""
    try:
        data = await browser.get_statement_detail(statement_id)
        return data
    except Exception as e:
        logger.error("Failed to get statement detail via API", error=e)
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")

@router.get("/api/statements/stats")
async def get_statement_stats_api():
    """API endpoint for getting statement statistics."""
    try:
        data = await browser.get_statement_stats()
        return data
    except Exception as e:
        logger.error("Failed to get statement stats via API", error=e)
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")

@router.get("/statement-detail/{statement_id}", response_class=HTMLResponse)
async def statement_detail_page(request: Request, statement_id: str):
    """Statement detail page."""
    try:
        statement = await browser.get_statement_detail(statement_id)
        
        context = {
            "request": request,
            "statement": statement,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return templates.TemplateResponse("statement_detail.html", context)
        
    except Exception as e:
        logger.error("Failed to render statement detail", error=e)
        raise HTTPException(status_code=500, detail=f"Detail page error: {str(e)}") 