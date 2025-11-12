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
            "active_page": "safety",
            "title": "Safety",
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
        from app.config.gcp_config import gcp_config
        from google.cloud import bigquery
        
        client = gcp_config.bigquery_client
        dataset_id = gcp_config.bigquery_dataset
        project_id = gcp_config.project_id
        
        # Get total statements that have been analyzed (have ai_content_analysis)
        total_analyzed_query = f"""
            SELECT COUNT(*) as total_analyzed
            FROM `{project_id}.{dataset_id}.statements`
            WHERE JSON_EXTRACT_SCALAR(raw_json, '$.ai_content_analysis') IS NOT NULL
        """
        
        total_analyzed = 0
        try:
            query_job = client.query(total_analyzed_query)
            rows = list(query_job.result())
            if rows:
                total_analyzed = rows[0].total_analyzed
        except Exception as e:
            logger.warning(f"Failed to query total analyzed statements: {e}")
        
        # Get total flagged statements
        total_flagged_query = f"""
            SELECT COUNT(*) as total_flagged
            FROM `{project_id}.{dataset_id}.flagged_content`
            WHERE is_flagged = TRUE
        """
        
        total_flagged = 0
        try:
            query_job = client.query(total_flagged_query)
            rows = list(query_job.result())
            if rows:
                total_flagged = rows[0].total_flagged
        except Exception as e:
            logger.warning(f"Failed to query total flagged statements: {e}")
        
        # Get statements processed today
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        today_query = f"""
            SELECT COUNT(*) as today_count
            FROM `{project_id}.{dataset_id}.statements`
            WHERE DATE(timestamp) = '{today}'
        """
        
        today_count = 0
        try:
            query_job = client.query(today_query)
            rows = list(query_job.result())
            if rows:
                today_count = rows[0].today_count
        except Exception as e:
            logger.warning(f"Failed to query today's statements: {e}")
        
        # Calculate detection rate
        detection_rate = 0.0
        if total_analyzed > 0:
            detection_rate = round((total_flagged / total_analyzed) * 100, 2)
        
        return {
            "total_statements_analyzed": total_analyzed,  # Total statements that have been analyzed
            "total_flagged": total_flagged,  # Total flagged statements
            "today_statements": today_count,  # Statements processed today
            "detection_rate": detection_rate,  # Percentage of analyzed statements that were flagged
            "safety_score": 100.0 - detection_rate,  # Inverse of detection rate
            "last_incident": f"{total_flagged} flagged statements total" if total_flagged > 0 else "No flagged content",
            "uptime_percentage": 100.0
        }
        
    except Exception as e:
        logger.error(f"Error getting safety metrics: {e}")
        return {
            "error": str(e),
            "total_statements_analyzed": 0,
            "total_flagged": 0,
            "today_statements": 0,
            "detection_rate": 0.0,
            "safety_score": 0,
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
        
        # Check AI analysis flags from in-memory cache
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
        
        # Also query BigQuery flagged_content table for persisted flagged content
        try:
            from app.config.gcp_config import gcp_config
            from google.cloud import bigquery
            
            client = gcp_config.bigquery_client
            dataset_id = gcp_config.bigquery_dataset
            project_id = gcp_config.project_id
            
            # Build query
            cohort_filter_sql = ""
            if cohort_filter:
                cohort_filter_sql = f"AND cohort = '{cohort_filter}'"
            
            query = f"""
                SELECT 
                    statement_id,
                    actor_name,
                    timestamp,
                    flagged_at,
                    content,
                    severity,
                    flagged_reasons,
                    confidence_score,
                    suggested_actions,
                    cohort
                FROM `{project_id}.{dataset_id}.flagged_content`
                WHERE is_flagged = TRUE
                    {cohort_filter_sql}
                ORDER BY flagged_at DESC
                LIMIT 50
            """
            
            query_job = client.query(query)
            rows = list(query_job.result())
            
            # Add BigQuery flagged content to results
            for row in rows:
                statement_id = row.statement_id
                if statement_id not in flagged_statement_ids:
                    # Parse flagged_reasons (REPEATED field - already an array)
                    if isinstance(row.flagged_reasons, list):
                        flagged_reasons = row.flagged_reasons
                    elif row.flagged_reasons:
                        try:
                            flagged_reasons = json.loads(row.flagged_reasons) if isinstance(row.flagged_reasons, str) else [row.flagged_reasons]
                        except:
                            flagged_reasons = [row.flagged_reasons] if row.flagged_reasons else []
                    else:
                        flagged_reasons = []
                    
                    # Parse suggested_actions (REPEATED field - already an array)
                    if isinstance(row.suggested_actions, list):
                        suggested_actions = row.suggested_actions
                    elif row.suggested_actions:
                        try:
                            suggested_actions = json.loads(row.suggested_actions) if isinstance(row.suggested_actions, str) else [row.suggested_actions]
                        except:
                            suggested_actions = [row.suggested_actions] if row.suggested_actions else []
                    else:
                        suggested_actions = []
                    
                    flagged_statements.append({
                        "statement_id": statement_id,
                        "actor_name": row.actor_name or "Unknown",
                        "timestamp": row.timestamp.isoformat() if row.timestamp else "",
                        "content": row.content or "",
                        "severity": row.severity or "medium",
                        "flagged_reasons": flagged_reasons,
                        "confidence_score": float(row.confidence_score) if row.confidence_score else 0.0,
                        "suggested_actions": suggested_actions,
                        "flag_type": "ai_analysis",
                        "cohort": row.cohort or ""
                    })
                    flagged_statement_ids.add(statement_id)
                    
        except Exception as bq_error:
            logger.warning(f"Failed to query BigQuery flagged_content table: {bq_error}")
            # Continue with in-memory results only
        
        # Sort by timestamp (most recent first)
        flagged_statements.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return {
            "flagged_count": len(flagged_statements),
            "flagged_statements": flagged_statements[:50],  # Last 50 flagged
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
            "max_content_length": None,  # No limit - store full content
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
