"""
Enhanced Analytics Dashboard with Learning Locker Integration.

This module enhances the existing dashboard with Learning Locker data visualization,
sync status indicators, statement activity graphs, and performance metrics.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("enhanced_dashboard")
templates = Jinja2Templates(directory="app/templates")


class EnhancedDashboard:
    """Enhanced dashboard with Learning Locker integration."""

    def __init__(self):
        self.api_base = "https://seventaps-analytics-5135b3a0701a.herokuapp.com/api"

    async def get_learninglocker_data(self) -> Dict[str, Any]:
        """Get Learning Locker sync data and statistics."""
        try:
            async with httpx.AsyncClient() as client:
                # Get sync status
                sync_response = await client.get(f"{self.api_base}/sync-status")
                sync_data = sync_response.json()

                # Get statement stats
                stats_response = await client.get(f"{self.api_base}/statements/stats")
                stats_data = stats_response.json()

                # Get export stats
                export_response = await client.get(f"{self.api_base}/export/stats")
                export_data = export_response.json()

                return {
                    "sync_status": sync_data,
                    "statement_stats": stats_data,
                    "export_stats": export_data,
                }
        except Exception as e:
            logger.error("Failed to get Learning Locker data", error=e)
            return {"error": str(e)}

    async def get_statement_activity(self, days: int = 30) -> Dict[str, Any]:
        """Get statement activity data for charts."""
        try:
            # Mock activity data for the last N days
            activity_data = []
            for i in range(days):
                date = datetime.utcnow() - timedelta(days=i)
                activity_data.append(
                    {
                        "date": date.strftime("%Y-%m-%d"),
                        "statements": 45 + (i % 20),  # Varying activity
                        "completions": 35 + (i % 15),
                        "attempts": 10 + (i % 8),
                        "unique_users": 12 + (i % 5),
                    }
                )

            return {
                "activity_data": list(reversed(activity_data)),
                "total_days": days,
                "total_statements": sum(d["statements"] for d in activity_data),
                "total_completions": sum(d["completions"] for d in activity_data),
                "total_attempts": sum(d["attempts"] for d in activity_data),
            }
        except Exception as e:
            logger.error("Failed to get statement activity", error=e)
            return {"error": str(e)}

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the dashboard."""
        try:
            # Mock performance metrics
            metrics = {
                "sync_performance": {
                    "last_sync_duration_ms": 1250,
                    "average_sync_duration_ms": 1100,
                    "sync_success_rate": 95.5,
                    "statements_per_minute": 45,
                },
                "system_performance": {
                    "cpu_usage": 42.3,
                    "memory_usage": 68.7,
                    "disk_usage": 45.2,
                    "response_time_ms": 180,
                },
                "user_activity": {
                    "active_users_today": 23,
                    "total_sessions": 156,
                    "average_session_duration": "12m 34s",
                    "peak_hour": "14:00",
                },
                "data_quality": {
                    "valid_statements": 98.2,
                    "duplicate_rate": 1.8,
                    "completion_rate": 78.5,
                    "average_score": 82.3,
                },
            }

            return metrics
        except Exception as e:
            logger.error("Failed to get performance metrics", error=e)
            return {"error": str(e)}

    async def get_sync_timeline(self) -> Dict[str, Any]:
        """Get sync timeline data."""
        try:
            # Mock sync timeline
            timeline = [
                {
                    "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                    "status": "success",
                    "statements_processed": 25,
                    "duration_ms": 1200,
                    "message": "Sync completed successfully",
                },
                {
                    "timestamp": (datetime.utcnow() - timedelta(hours=4)).isoformat(),
                    "status": "success",
                    "statements_processed": 18,
                    "duration_ms": 950,
                    "message": "Sync completed successfully",
                },
                {
                    "timestamp": (datetime.utcnow() - timedelta(hours=6)).isoformat(),
                    "status": "warning",
                    "statements_processed": 15,
                    "failed_count": 3,
                    "duration_ms": 1500,
                    "message": "Some statements failed to sync",
                },
                {
                    "timestamp": (datetime.utcnow() - timedelta(hours=8)).isoformat(),
                    "status": "success",
                    "statements_processed": 22,
                    "duration_ms": 1100,
                    "message": "Sync completed successfully",
                },
            ]

            return {"timeline": timeline}
        except Exception as e:
            logger.error("Failed to get sync timeline", error=e)
            return {"error": str(e)}

    async def get_basic_metrics(self) -> Dict[str, Any]:
        """Get basic dashboard metrics from real database data."""
        try:
            # Get real data from database
            import os

            import psycopg2
            from psycopg2.extras import RealDictCursor

            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                return {"error": "Database not configured"}

            conn = psycopg2.connect(database_url)
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Get total statements count
                    cursor.execute("SELECT COUNT(*) as total FROM statements_flat")
                    total_statements = cursor.fetchone()["total"]

                    # Get unique users count
                    cursor.execute(
                        "SELECT COUNT(DISTINCT actor_id) as total FROM statements_flat WHERE actor_id IS NOT NULL"
                    )
                    total_users = cursor.fetchone()["total"]

                    # Get completion rate (statements with 'completed' verb)
                    cursor.execute(
                        "SELECT COUNT(*) as completed FROM statements_flat WHERE verb_id LIKE '%completed%'"
                    )
                    completed_count = cursor.fetchone()["completed"]
                    completion_rate = (
                        (completed_count / total_statements * 100)
                        if total_statements > 0
                        else 0
                    )

                    # Get active users in last 7 days
                    cursor.execute(
                        """
                        SELECT COUNT(DISTINCT actor_id) as active_7d 
                        FROM statements_flat 
                        WHERE actor_id IS NOT NULL 
                        AND processed_at >= NOW() - INTERVAL '7 days'
                    """
                    )
                    active_users_7d = cursor.fetchone()["active_7d"]

                    # Get active users in last 30 days
                    cursor.execute(
                        """
                        SELECT COUNT(DISTINCT actor_id) as active_30d 
                        FROM statements_flat 
                        WHERE actor_id IS NOT NULL 
                        AND processed_at >= NOW() - INTERVAL '30 days'
                    """
                    )
                    active_users_30d = cursor.fetchone()["active_30d"]

                    # Get top verbs
                    cursor.execute(
                        """
                        SELECT verb_id, COUNT(*) as count 
                        FROM statements_flat 
                        GROUP BY verb_id 
                        ORDER BY count DESC 
                        LIMIT 5
                    """
                    )
                    top_verbs = [
                        {"verb": row["verb_id"], "count": row["count"]}
                        for row in cursor.fetchall()
                    ]

                    # Get daily activity for last 7 days
                    cursor.execute(
                        """
                        SELECT 
                            DATE(processed_at) as date,
                            COUNT(DISTINCT actor_id) as active_users,
                            COUNT(*) as total_statements
                        FROM statements_flat 
                        WHERE processed_at >= NOW() - INTERVAL '7 days'
                        GROUP BY DATE(processed_at)
                        ORDER BY date
                    """
                    )
                    daily_activity = []
                    for row in cursor.fetchall():
                        daily_activity.append(
                            {
                                "date": row["date"].strftime("%Y-%m-%d"),
                                "active_users": row["active_users"],
                                "total_statements": row["total_statements"],
                            }
                        )

                    # Get recent real 7taps statements
                    cursor.execute(
                        """
                        SELECT statement_id, actor_id, verb_id, object_id, timestamp, processed_at
                        FROM statements_flat 
                        WHERE object_id LIKE '%7taps.com%'
                        ORDER BY processed_at DESC 
                        LIMIT 10
                    """
                    )
                    recent_7taps_statements = []
                    for row in cursor.fetchall():
                        recent_7taps_statements.append(
                            {
                                "statement_id": row["statement_id"],
                                "actor_id": row["actor_id"],
                                "verb_id": row["verb_id"],
                                "object_id": row["object_id"],
                                "timestamp": (
                                    row["timestamp"].isoformat()
                                    if row["timestamp"]
                                    else None
                                ),
                                "processed_at": (
                                    row["processed_at"].isoformat()
                                    if row["processed_at"]
                                    else None
                                ),
                            }
                        )

                    return {
                        "total_users": total_users,
                        "total_statements": total_statements,
                        "completion_rate": round(completion_rate, 1),
                        "active_users_7d": active_users_7d,
                        "active_users_30d": active_users_30d,
                        "top_verbs": top_verbs,
                        "daily_activity": daily_activity,
                        "recent_7taps_statements": recent_7taps_statements,
                        "cohort_completion": [
                            {
                                "cohort_name": "Real 7taps Data",
                                "completion_rate": completion_rate,
                            }
                        ],
                    }

            finally:
                conn.close()

        except Exception as e:
            logger.error(f"Failed to get real metrics: {e}")
            return {"error": str(e)}


# Global dashboard instance
dashboard = EnhancedDashboard()


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Basic analytics dashboard page."""
    try:
        # Get basic metrics
        metrics = await dashboard.get_basic_metrics()

        context = {
            "request": request,
            "metrics": metrics,
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "refresh_interval": 300,  # 5 minutes
        }

        return templates.TemplateResponse("dashboard.html", context)

    except Exception as e:
        logger.error("Failed to render dashboard", error=e)
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")


@router.get("/api/dashboard/metrics")
async def get_dashboard_metrics():
    """API endpoint for dashboard metrics."""
    try:
        metrics = await dashboard.get_basic_metrics()
        return {
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success",
        }
    except Exception as e:
        logger.error("Failed to get dashboard metrics", error=e)
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")


@router.get("/enhanced-dashboard", response_class=HTMLResponse)
async def enhanced_dashboard_page(request: Request):
    """Enhanced dashboard with Learning Locker integration."""
    try:
        # Get all dashboard data
        ll_data = await dashboard.get_learninglocker_data()
        activity_data = await dashboard.get_statement_activity()
        performance_metrics = await dashboard.get_performance_metrics()
        sync_timeline = await dashboard.get_sync_timeline()

        context = {
            "request": request,
            "learninglocker_data": ll_data,
            "activity_data": activity_data,
            "performance_metrics": performance_metrics,
            "sync_timeline": sync_timeline,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return templates.TemplateResponse("enhanced_dashboard.html", context)

    except Exception as e:
        logger.error("Failed to render enhanced dashboard", error=e)
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")


@router.get("/api/dashboard/learninglocker-data")
async def get_learninglocker_dashboard_data():
    """API endpoint for Learning Locker dashboard data."""
    try:
        data = await dashboard.get_learninglocker_data()
        return data
    except Exception as e:
        logger.error("Failed to get Learning Locker dashboard data", error=e)
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")


@router.get("/api/dashboard/activity")
async def get_activity_data(days: int = 30):
    """API endpoint for statement activity data."""
    try:
        data = await dashboard.get_statement_activity(days)
        return data
    except Exception as e:
        logger.error("Failed to get activity data", error=e)
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")


@router.get("/api/dashboard/performance")
async def get_performance_data():
    """API endpoint for performance metrics."""
    try:
        data = await dashboard.get_performance_metrics()
        return data
    except Exception as e:
        logger.error("Failed to get performance data", error=e)
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")


@router.get("/api/dashboard/sync-timeline")
async def get_sync_timeline_data():
    """API endpoint for sync timeline data."""
    try:
        data = await dashboard.get_sync_timeline()
        return data
    except Exception as e:
        logger.error("Failed to get sync timeline data", error=e)
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")


@router.get("/api/dashboard/real-time")
async def get_real_time_dashboard_data():
    """API endpoint for real-time dashboard updates."""
    try:
        # Get all real-time data
        ll_data = await dashboard.get_learninglocker_data()
        performance_metrics = await dashboard.get_performance_metrics()

        return {
            "learninglocker_data": ll_data,
            "performance_metrics": performance_metrics,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error("Failed to get real-time dashboard data", error=e)
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")


@router.get("/api/dashboard/recent-7taps-statements")
async def get_recent_7taps_statements():
    """API endpoint for recent 7taps xAPI statements."""
    try:
        metrics = await dashboard.get_basic_metrics()
        if "error" in metrics:
            return {"error": metrics["error"]}

        return {
            "recent_7taps_statements": metrics.get("recent_7taps_statements", []),
            "total_7taps_statements": len(metrics.get("recent_7taps_statements", [])),
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success",
        }
    except Exception as e:
        logger.error("Failed to get recent 7taps statements", error=e)
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")
