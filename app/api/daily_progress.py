"""
Daily Progress Analytics - Simplified for 7pm Email Workflow

This focuses on the core requirement: who completed lessons today and who didn't,
with actionable insights for the daily progress email.
"""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, date
import json

from app.logging_config import get_logger
from app.api.bigquery_analytics import execute_bigquery_query

router = APIRouter()
logger = get_logger("daily_progress")
templates = Jinja2Templates(directory="app/templates")

def get_daily_progress_data(target_date: str, group: Optional[str] = None) -> Dict[str, Any]:
    """Get daily progress data for the 7pm email workflow."""
    try:
        # Simple query to get today's lesson completions
        platform_filter = "AND context_platform = '7taps'" if group == "7taps" else ""
        
        query = f"""
        WITH daily_activity AS (
            SELECT 
                actor_id,
                actor_name,
                verb_display,
                object_name as lesson_name,
                result_completion,
                result_success,
                result_response,
                timestamp,
                DATE(timestamp) as activity_date
            FROM taps_data.statements 
            WHERE DATE(timestamp) = '{target_date}'
            {platform_filter}
        ),
        user_summary AS (
            SELECT 
                actor_id,
                actor_name,
                COUNT(*) as total_activities,
                COUNT(CASE WHEN result_completion = true THEN 1 END) as completed_activities,
                COUNT(CASE WHEN verb_display = 'completed' THEN 1 END) as lessons_completed,
                COUNT(CASE WHEN verb_display = 'answered' THEN 1 END) as responses_given,
                MAX(timestamp) as last_activity,
                STRING_AGG(DISTINCT lesson_name, ', ') as lessons_attempted,
                STRING_AGG(DISTINCT result_response, ' | ') as sample_responses
            FROM daily_activity
            GROUP BY actor_id, actor_name
        )
        SELECT 
            actor_id,
            actor_name,
            total_activities,
            completed_activities,
            lessons_completed,
            responses_given,
            last_activity,
            lessons_attempted,
            sample_responses,
            CASE 
                WHEN lessons_completed > 0 THEN 'Completed'
                WHEN total_activities > 0 THEN 'Partial'
                ELSE 'Not Started'
            END as status
        FROM user_summary
        ORDER BY lessons_completed DESC, total_activities DESC
        """
        
        result = execute_bigquery_query(query)
        
        if result["success"]:
            # Handle different possible result structures
            if "data" in result and "rows" in result["data"]:
                users = result["data"]["rows"]
            elif "results" in result:
                users = result["results"]
            else:
                users = []
            
            # Calculate summary metrics
            total_users = len(users)
            completed_users = [u for u in users if u.get("status") == "Completed"]
            partial_users = [u for u in users if u.get("status") == "Partial"]
            not_started_users = [u for u in users if u.get("status") == "Not Started"]
            
            completion_rate = (len(completed_users) / max(total_users, 1)) * 100
            
            # Extract actionable insights
            insights = []
            
            if len(completed_users) > 0:
                insights.append(f"✅ {len(completed_users)} learners completed their lessons today")
            
            if len(partial_users) > 0:
                insights.append(f"⚠️ {len(partial_users)} learners started but didn't finish")
            
            if len(not_started_users) > 0:
                insights.append(f"❌ {len(not_started_users)} learners haven't started today's lesson")
            
            # Look for quote-worthy responses
            quote_worthy = []
            for user in users:
                responses = user.get("sample_responses", "")
                if responses and len(responses) > 20:
                    quote_worthy.append({
                        "user": user["actor_name"],
                        "response": responses[:100] + "..." if len(responses) > 100 else responses
                    })
            
            if quote_worthy:
                insights.append(f"💬 Found {len(quote_worthy)} detailed responses for potential quotes")
            
            return {
                "success": True,
                "date": target_date,
                "group": group,
                "summary": {
                    "total_users": total_users,
                    "completed_users": len(completed_users),
                    "partial_users": len(partial_users),
                    "not_started_users": len(not_started_users),
                    "completion_rate": round(completion_rate, 1)
                },
                "users": users,
                "completed_users": completed_users,
                "partial_users": partial_users,
                "not_started_users": not_started_users,
                "insights": insights,
                "quote_worthy": quote_worthy[:3],  # Top 3 for email
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Query failed"),
                "users": [],
                "summary": {"total_users": 0, "completion_rate": 0}
            }
            
    except Exception as e:
        logger.error(f"Failed to get daily progress data: {e}")
        return {
            "success": False,
            "error": str(e),
            "users": [],
            "summary": {"total_users": 0, "completion_rate": 0}
        }

@router.get("/ui/daily-progress", response_class=HTMLResponse)
async def daily_progress_dashboard(
    request: Request,
    target_date: Optional[str] = Query(None, description="Target date (YYYY-MM-DD)"),
    group: Optional[str] = Query(None, description="Group filter (e.g., 7taps)")
):
    """Daily progress dashboard for 7pm email workflow."""
    try:
        # Default to today
        if not target_date:
            target_date = date.today().strftime("%Y-%m-%d")
        
        # Get progress data
        progress_data = get_daily_progress_data(target_date, group)
        
        context = {
            "request": request,
            "title": "Daily Progress - 7pm Email Prep",
            "target_date": target_date,
            "group": group or "All Groups",
            "data": progress_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return templates.TemplateResponse("daily_progress_working.html", context)
        
    except Exception as e:
        logger.error(f"Failed to render daily progress dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")

@router.get("/api/daily-progress/data")
async def get_daily_progress_api(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    group: Optional[str] = Query(None, description="Group filter")
):
    """Get daily progress data as JSON for email workflow."""
    return get_daily_progress_data(date, group)

@router.get("/api/daily-progress/email-summary")
async def get_email_summary(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    group: Optional[str] = Query(None, description="Group filter")
):
    """Get formatted summary for 7pm email."""
    data = get_daily_progress_data(date, group)
    
    if not data["success"]:
        return {"error": data["error"]}
    
    summary = data["summary"]
    insights = data["insights"]
    
    # Format for email
    email_summary = {
        "date": date,
        "group": group or "All Groups",
        "completion_rate": f"{summary['completion_rate']}%",
        "completed_count": summary["completed_users"],
        "total_count": summary["total_users"],
        "key_insights": insights,
        "quote_worthy_responses": data.get("quote_worthy", []),
        "recommended_tone": "celebratory" if summary["completion_rate"] > 70 else "encouraging" if summary["completion_rate"] > 40 else "supportive",
        "ready_for_email": True
    }
    
    return email_summary
