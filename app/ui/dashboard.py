"""
Enhanced Analytics Dashboard with Learning Locker Integration.

This module enhances the existing dashboard with Learning Locker data visualization,
sync status indicators, statement activity graphs, and performance metrics.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, List
import httpx
import json
from datetime import datetime, timedelta
import os

from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("enhanced_dashboard")
templates = Jinja2Templates(directory="templates")

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
                    "export_stats": export_data
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
                activity_data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "statements": 45 + (i % 20),  # Varying activity
                    "completions": 35 + (i % 15),
                    "attempts": 10 + (i % 8),
                    "unique_users": 12 + (i % 5)
                })
            
            return {
                "activity_data": list(reversed(activity_data)),
                "total_days": days,
                "total_statements": sum(d["statements"] for d in activity_data),
                "total_completions": sum(d["completions"] for d in activity_data),
                "total_attempts": sum(d["attempts"] for d in activity_data)
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
                    "statements_per_minute": 45
                },
                "system_performance": {
                    "cpu_usage": 42.3,
                    "memory_usage": 68.7,
                    "disk_usage": 45.2,
                    "response_time_ms": 180
                },
                "user_activity": {
                    "active_users_today": 23,
                    "total_sessions": 156,
                    "average_session_duration": "12m 34s",
                    "peak_hour": "14:00"
                },
                "data_quality": {
                    "valid_statements": 98.2,
                    "duplicate_rate": 1.8,
                    "completion_rate": 78.5,
                    "average_score": 82.3
                }
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
                    "message": "Sync completed successfully"
                },
                {
                    "timestamp": (datetime.utcnow() - timedelta(hours=4)).isoformat(),
                    "status": "success",
                    "statements_processed": 18,
                    "duration_ms": 950,
                    "message": "Sync completed successfully"
                },
                {
                    "timestamp": (datetime.utcnow() - timedelta(hours=6)).isoformat(),
                    "status": "warning",
                    "statements_processed": 15,
                    "failed_count": 3,
                    "duration_ms": 1500,
                    "message": "Some statements failed to sync"
                },
                {
                    "timestamp": (datetime.utcnow() - timedelta(hours=8)).isoformat(),
                    "status": "success",
                    "statements_processed": 22,
                    "duration_ms": 1100,
                    "message": "Sync completed successfully"
                }
            ]
            
            return {"timeline": timeline}
        except Exception as e:
            logger.error("Failed to get sync timeline", error=e)
            return {"error": str(e)}

# Global dashboard instance
dashboard = EnhancedDashboard()

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
            "timestamp": datetime.utcnow().isoformat()
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
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("Failed to get real-time dashboard data", error=e)
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}") 