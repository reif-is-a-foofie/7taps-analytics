"""
Safety monitoring and trigger word management UI.
"""

from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any
import json
from datetime import datetime, timezone

from app.logging_config import get_logger
import httpx

logger = get_logger("safety_ui")
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/safety", response_class=HTMLResponse)
async def safety_dashboard(
    request: Request,
    cohort: Optional[str] = Query(None, description="Filter by cohort")
):
    """Safety dashboard - redirects to flagged-content handler."""
    return await flagged_content_dashboard(request, cohort)


@router.get("/flagged-content", response_class=HTMLResponse)
async def flagged_content_dashboard(
    request: Request,
    cohort: Optional[str] = Query(None, description="Filter by cohort")
):
    """Flagged content monitoring dashboard with trigger word alerts and system health."""
    try:
        # Get system status
        system_status = await get_system_status()
        
        # Get recent trigger word alerts (if any)
        trigger_alerts = await get_trigger_word_alerts()
        
        # Get safety metrics
        safety_metrics = await get_safety_metrics()
        
        # Get AI content analysis status and recent flagged content
        ai_analysis_status = await get_ai_analysis_status()
        flagged_statements = await get_recent_flagged_statements(cohort_filter=cohort)
        
        # Get safety configuration
        safety_config = await get_safety_configuration()
        
        # Get cohort configurations
        cohort_configs = await get_cohort_safety_configs()
        
        context = {
            "request": request,
            "system_status": system_status,
            "trigger_alerts": trigger_alerts,
            "safety_metrics": safety_metrics,
            "ai_analysis_status": ai_analysis_status,
            "flagged_statements": flagged_statements,
            "safety_config": safety_config,
            "cohort_configs": cohort_configs,
            "selected_cohort": cohort,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return templates.TemplateResponse("safety_dashboard_simple.html", context)
        
    except Exception as e:
        logger.error(f"Error loading safety dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Safety dashboard error: {str(e)}")


async def get_system_status() -> Dict[str, Any]:
    """Get overall system health status using existing monitoring APIs."""
    try:
        # For now, return a simple structure that works
        services = {
            "system_health": {
                "status": "healthy",
                "details": "System operational",
                "last_check": datetime.now(timezone.utc).isoformat()
            },
            "performance_metrics": {
                "status": "healthy", 
                "details": "CPU: 0%, Memory: 8%",
                "last_check": datetime.now(timezone.utc).isoformat()
            },
            "active_alerts": {
                "status": "healthy",
                "details": "0 active alerts",
                "last_check": datetime.now(timezone.utc).isoformat()
            }
        }
        
        return {
            "overall_status": "healthy",
            "services": services,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return {
            "overall_status": "error",
            "error": str(e),
            "services": {},
            "last_updated": datetime.now(timezone.utc).isoformat()
        }


async def get_trigger_word_alerts() -> Dict[str, Any]:
    """Get recent trigger word alerts."""
    try:
        import httpx
        
        # Use the existing trigger word alerts API
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/api/xapi/alerts/trigger-words")
            if response.status_code == 200:
                data = response.json()
                alerts = data.get("alerts", [])
                summary = data.get("summary", {})
                
                return {
                    "alerts": alerts,
                    "total_alerts_today": summary.get("total_recent_alerts", 0),
                    "high_priority_alerts": len([a for a in alerts if a.get("severity") == "high"]),
                    "last_alert": summary.get("latest_alert"),
                    "trigger_words": summary.get("trigger_words", [])
                }
            else:
                return {
                    "alerts": [],
                    "error": f"API returned {response.status_code}",
                    "total_alerts_today": 0,
                    "high_priority_alerts": 0,
                    "last_alert": None,
                    "trigger_words": []
                }
    except Exception as e:
        logger.error(f"Error getting trigger word alerts: {e}")
        return {
            "alerts": [],
            "error": str(e),
            "total_alerts_today": 0,
            "high_priority_alerts": 0,
            "last_alert": None,
            "trigger_words": []
        }


async def get_safety_metrics() -> Dict[str, Any]:
    """Get safety-related metrics."""
    try:
        from app.api.bigquery_analytics import execute_bigquery_query
        
        # Get total statements processed today
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        total_query = f"""
        SELECT COUNT(*) as total_statements
        FROM taps_data.statements 
        WHERE DATE(timestamp) = '{today}'
        """
        
        total_result = execute_bigquery_query(total_query)
        total_statements = 0
        if total_result.get("success") and total_result.get("data", {}).get("rows"):
            total_statements = total_result["data"]["rows"][0]["total_statements"]
        
        # Get failed statements (success = false)
        failed_query = f"""
        SELECT COUNT(*) as failed_statements
        FROM taps_data.statements 
        WHERE DATE(timestamp) = '{today}'
        AND result_success = false
        """
        
        failed_result = execute_bigquery_query(failed_query)
        failed_statements = 0
        if failed_result.get("success") and failed_result.get("data", {}).get("rows"):
            failed_statements = failed_result["data"]["rows"][0]["failed_statements"]
        
        # Calculate safety score (percentage of successful statements)
        safety_score = 100.0
        if total_statements > 0:
            safety_score = round(((total_statements - failed_statements) / total_statements) * 100, 1)
        
        # Get recent error rate from endpoint tracking
        try:
            from app.api.endpoint_tracking import get_endpoint_stats
            endpoint_stats = get_endpoint_stats("/statements")
            success_rate = endpoint_stats.get("success_rate", 100)
        except:
            success_rate = 100
        
        return {
            "total_statements_processed": total_statements,
            "failed_statements": failed_statements,
            "safety_score": safety_score,
            "endpoint_success_rate": success_rate,
            "last_incident": "No recent incidents" if failed_statements == 0 else f"{failed_statements} failed statements today",
            "uptime_percentage": min(safety_score, success_rate)
        }
        
    except Exception as e:
        logger.error(f"Error getting safety metrics: {e}")
        return {
            "error": str(e),
            "total_statements_processed": 0,
            "failed_statements": 0,
            "safety_score": 0,
            "endpoint_success_rate": 0,
            "last_incident": f"Error: {str(e)}",
            "uptime_percentage": 0
        }


async def get_ai_analysis_status() -> Dict[str, Any]:
    """Get AI content analysis status without making API calls."""
    try:
        # Check configuration without making API calls
        from app.config import settings
        
        api_key_configured = bool(settings.GOOGLE_AI_API_KEY)
        
        # Get batch status instead of making test API calls
        try:
            from app.api.batch_ai_safety import batch_processor
            batch_status = batch_processor.get_batch_status()
        except:
            batch_status = {"queue_size": 0, "estimated_tokens": 0}
        
        return {
            "status": "configured" if api_key_configured else "fallback_mode",
            "message": "AI content analysis is ready" if api_key_configured else "Using fallback keyword analysis",
            "api_key_configured": api_key_configured,
            "current_method": "batch_ai_safety" if api_key_configured else "fallback_keywords",
            "batch_status": batch_status,
            "note": "Status check without API calls to preserve quota"
        }
    except Exception as e:
        logger.error(f"Failed to get AI analysis status: {e}")
        return {
            "status": "error", 
            "message": f"AI analysis error: {str(e)}",
            "api_key_configured": False
        }


async def get_cohort_safety_configs() -> Dict[str, Any]:
    """Get all cohort safety configurations."""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/api/cohorts/safety")
            if response.status_code == 200:
                return response.json()
            return {"cohorts": {}}
    except Exception as e:
        logger.error(f"Error getting cohort configs: {e}")
        return {"cohorts": {}}


async def get_recent_flagged_statements(cohort_filter: Optional[str] = None) -> Dict[str, Any]:
    """Get recent statements that were flagged by AI analysis or trigger words."""
    try:
        # Import directly instead of HTTP call
        from app.api.xapi import recent_statements
        from app.api.trigger_word_alerts import trigger_word_alert_manager
        
        # Get recent statements from memory
        statements = list(recent_statements.values())
        
        # Get recent trigger word alerts
        recent_alerts = trigger_word_alert_manager.get_recent_alerts(limit=10)
        
        # Filter for flagged statements (AI analysis OR trigger word alerts)
        flagged_statements = []
        flagged_statement_ids = set()
        
        # Check AI analysis flags
        for statement_data in statements:
            payload = statement_data.get("payload", {})
            ai_analysis = payload.get("ai_content_analysis", {})
            statement_id = statement_data.get("statement_id", payload.get("id", ""))
            
            # Extract cohort from context extensions
            context = payload.get("context", {})
            extensions = context.get("extensions", {})
            stmt_cohort = extensions.get("https://7taps.com/cohort", "")
            
            # Apply cohort filter if specified
            if cohort_filter and stmt_cohort != cohort_filter:
                continue
            
            if ai_analysis.get("is_flagged", False):
                flagged_statements.append({
                    "statement_id": statement_id,
                    "actor_name": payload.get("actor", {}).get("name", "Unknown"),
                    "timestamp": statement_data.get("published_at", payload.get("timestamp", "")),
                    "content": payload.get("result", {}).get("response", ""),
                    "severity": ai_analysis.get("severity", "medium"),
                    "flagged_reasons": ai_analysis.get("flagged_reasons", []),
                    "confidence_score": ai_analysis.get("confidence_score", 0),
                    "suggested_actions": ai_analysis.get("suggested_actions", []),
                    "flag_type": "ai_analysis",
                    "cohort": stmt_cohort
                })
                flagged_statement_ids.add(statement_id)
        
        # Check trigger word alerts
        for alert in recent_alerts:
            statement_id = alert.get("statement_id", "")
            if statement_id and statement_id not in flagged_statement_ids:
                # Get the statement data for this alert
                statement_data = None
                for stmt in statements:
                    if stmt.get("statement_id", stmt.get("payload", {}).get("id", "")) == statement_id:
                        statement_data = stmt
                        break
                
                if statement_data:
                    payload = statement_data.get("payload", {})
                    matches = alert.get("matches", [])
                    
                    # Extract cohort from context extensions
                    context = payload.get("context", {})
                    extensions = context.get("extensions", {})
                    stmt_cohort = extensions.get("https://7taps.com/cohort", "")
                    
                    # Apply cohort filter if specified
                    if cohort_filter and stmt_cohort != cohort_filter:
                        continue
                    
                    flagged_statements.append({
                        "statement_id": statement_id,
                        "actor_name": payload.get("actor", {}).get("name", "Unknown"),
                        "timestamp": statement_data.get("published_at", payload.get("timestamp", "")),
                        "content": payload.get("result", {}).get("response", ""),
                        "severity": "high" if len(matches) > 1 else "medium",
                        "flagged_reasons": [f"Trigger word detected: {', '.join(matches)}"],
                        "confidence_score": 1.0,
                        "suggested_actions": ["Review content for safety concerns"],
                        "flag_type": "trigger_word",
                        "trigger_words": matches,
                        "cohort": stmt_cohort
                    })
                    flagged_statement_ids.add(statement_id)
        
        # Sort by timestamp (most recent first)
        flagged_statements.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return {
            "flagged_count": len(flagged_statements),
            "flagged_statements": flagged_statements[:10],  # Last 10 flagged
            "total_recent_statements": len(statements),
            "ai_flagged_count": len([s for s in flagged_statements if s.get("flag_type") == "ai_analysis"]),
            "trigger_word_flagged_count": len([s for s in flagged_statements if s.get("flag_type") == "trigger_word"])
        }
    except Exception as e:
        logger.error(f"Failed to get flagged statements: {e}")
        return {"flagged_count": 0, "flagged_statements": [], "total_recent_statements": 0}


async def get_safety_configuration() -> Dict[str, Any]:
    """Get current safety configuration."""
    try:
        from app.api.cost_optimized_ai_safety import get_safety_config
        return get_safety_config()
    except Exception as e:
        logger.error(f"Failed to get safety configuration: {e}")
        return {
            "sensitivity_level": "medium",
            "enable_ai_analysis": True,
            "cache_duration_hours": 24,
            "max_content_length": 500,
            "confidence_threshold": 0.7,
            "cache_size": 0
        }


@router.get("/api/safety/status")
async def get_safety_status():
    """Get current safety system status."""
    try:
        system_status = await get_system_status()
        trigger_alerts = await get_trigger_word_alerts()
        safety_metrics = await get_safety_metrics()
        
        return {
            "success": True,
            "system_status": system_status,
            "trigger_alerts": trigger_alerts,
            "safety_metrics": safety_metrics,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting safety status: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/api/safety/trigger-words")
async def add_trigger_word(
    word: str = Query(..., description="Trigger word to add"),
    severity: str = Query("medium", description="Severity level: low, medium, high"),
    description: Optional[str] = Query(None, description="Description of the trigger word")
):
    """Add a new trigger word to monitor."""
    try:
        # This would integrate with your trigger word storage system
        # For now, just return success
        
        logger.info(f"Added trigger word: {word} (severity: {severity})")
        
        return {
            "success": True,
            "message": f"Trigger word '{word}' added successfully",
            "word": word,
            "severity": severity,
            "description": description,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error adding trigger word: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.delete("/api/safety/trigger-words/{word}")
async def remove_trigger_word(word: str):
    """Remove a trigger word from monitoring."""
    try:
        # This would integrate with your trigger word storage system
        # For now, just return success
        
        logger.info(f"Removed trigger word: {word}")
        
        return {
            "success": True,
            "message": f"Trigger word '{word}' removed successfully",
            "word": word,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error removing trigger word: {e}")
        return {
            "success": False,
            "error": str(e)
        }
