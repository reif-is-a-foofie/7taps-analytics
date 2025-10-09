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
from app.api.xapi import get_recent_statements, get_ingestion_stats

router = APIRouter()
logger = get_logger("statement_browser")
templates = Jinja2Templates(directory="app/templates")

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
            # Get real xAPI statements from the ingestion pipeline
            all_statements = get_recent_statements(limit=0)  # Get all available
            
            # Apply filters
            filtered_statements = []
            for entry in all_statements:
                statement = entry.get("payload", {})
                
                # Actor filter
                if actor_filter:
                    actor_name = statement.get("actor", {}).get("account", {}).get("name", "")
                    if actor_filter.lower() not in actor_name.lower():
                        continue
                
                # Verb filter  
                if verb_filter:
                    verb_id = statement.get("verb", {}).get("id", "")
                    if verb_filter.lower() not in verb_id.lower():
                        continue
                
                # Object filter
                if object_filter:
                    object_id = statement.get("object", {}).get("id", "")
                    if object_filter.lower() not in object_id.lower():
                        continue
                
                # Search query (search in all text fields)
                if search_query:
                    search_text = f"{actor_name} {verb_id} {object_id}".lower()
                    if search_query.lower() not in search_text:
                        continue
                
                filtered_statements.append(entry)
            
            # Pagination
            total_count = len(filtered_statements)
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            page_statements = filtered_statements[start_idx:end_idx]
            
            # Format for UI display
            formatted_statements = []
            for entry in page_statements:
                statement = entry.get("payload", {})
                formatted_statements.append({
                    "id": statement.get("id", "unknown"),
                    "actor": statement.get("actor", {}),
                    "verb": statement.get("verb", {}),
                    "object": statement.get("object", {}),
                    "timestamp": statement.get("timestamp", ""),
                    "result": statement.get("result", {}),
                    "published_at": entry.get("published_at", ""),
                    "message_id": entry.get("message_id", "")
                })
            
            return {
                "statements": formatted_statements,
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
        """Get real statement statistics from ingestion pipeline."""
        try:
            # Get real ingestion stats
            ingestion_stats = get_ingestion_stats()
            all_statements = get_recent_statements(limit=0)
            
            # Calculate real statistics
            unique_actors = set()
            unique_activities = set()
            verb_counts = {}
            activity_counts = {}
            completed_count = 0
            total_score = 0
            score_count = 0
            
            from datetime import datetime, timezone
            today = datetime.now(timezone.utc).date()
            statements_today = 0
            
            for entry in all_statements:
                statement = entry.get("payload", {})
                
                # Count statements from today
                timestamp_str = statement.get("timestamp", "")
                if timestamp_str:
                    try:
                        from app.utils.timestamp_utils import parse_timestamp
                        stmt_date = parse_timestamp(timestamp_str).date()
                        if stmt_date == today:
                            statements_today += 1
                    except:
                        pass
                
                # Track unique actors
                actor_name = statement.get("actor", {}).get("account", {}).get("name", "")
                if actor_name:
                    unique_actors.add(actor_name)
                
                # Track unique activities
                activity_id = statement.get("object", {}).get("id", "")
                if activity_id:
                    unique_activities.add(activity_id)
                    activity_counts[activity_id] = activity_counts.get(activity_id, 0) + 1
                
                # Track verbs
                verb_id = statement.get("verb", {}).get("id", "")
                if verb_id:
                    verb_name = verb_id.split("/")[-1]  # Extract verb name from URI
                    verb_counts[verb_name] = verb_counts.get(verb_name, 0) + 1
                    
                    if "completed" in verb_name.lower():
                        completed_count += 1
                
                # Track scores
                result = statement.get("result", {})
                if result and "score" in result:
                    score = result["score"].get("raw")
                    if score is not None:
                        total_score += score
                        score_count += 1
            
            # Calculate completion rate and average score
            total_statements = len(all_statements)
            completion_rate = (completed_count / total_statements * 100) if total_statements > 0 else 0
            average_score = (total_score / score_count) if score_count > 0 else 0
            
            # Top verbs and activities
            top_verbs = [{"verb": verb, "count": count} for verb, count in 
                        sorted(verb_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
            top_activities = [{"activity": activity.split("/")[-1], "count": count} for activity, count in 
                            sorted(activity_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
            
            stats = {
                "total_statements": total_statements,
                "statements_today": statements_today,
                "unique_actors": len(unique_actors),
                "unique_activities": len(unique_activities),
                "completion_rate": round(completion_rate, 1),
                "average_score": round(average_score, 1),
                "top_verbs": top_verbs,
                "top_activities": top_activities,
                "ingestion_stats": ingestion_stats
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
            "timestamp": datetime.now(timezone.utc).isoformat()
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
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return templates.TemplateResponse("statement_detail.html", context)
        
    except Exception as e:
        logger.error("Failed to render statement detail", error=e)
        raise HTTPException(status_code=500, detail=f"Detail page error: {str(e)}") 