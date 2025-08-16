"""
Enhanced Analytics Dashboard for 7taps Analytics
Provides modern UI/UX with interactive visualizations and responsive design
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Base URL for API calls
BASE_URL = "https://seventaps-analytics-5135b3a0701a.herokuapp.com"

async def fetch_analytics_data(endpoint: str) -> Dict[str, Any]:
    """Fetch data from analytics API endpoints with error handling"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BASE_URL}{endpoint}")
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"API endpoint {endpoint} returned {response.status_code}")
                return {"error": f"API returned {response.status_code}"}
    except Exception as e:
        logger.error(f"Error fetching data from {endpoint}: {e}")
        return {"error": str(e)}

async def get_dashboard_data() -> Dict[str, Any]:
    """Get comprehensive dashboard data from multiple endpoints"""
    try:
        # Fetch data from existing endpoints
        tasks = [
            fetch_analytics_data("/api/dashboard/metrics"),
            fetch_analytics_data("/api/dashboard/performance"),
            fetch_analytics_data("/api/dashboard/real-time"),
            fetch_analytics_data("/health/detailed")
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        dashboard_data = {
            "metrics": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
            "performance": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
            "real_time": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
            "system_health": results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])},
            "timestamp": datetime.now().isoformat()
        }
        
        return dashboard_data
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        return {"error": str(e)}

async def get_cohort_analytics() -> Dict[str, Any]:
    """Get cohort analytics data"""
    try:
        # Try to fetch from analytics API first
        cohort_data = await fetch_analytics_data("/api/analytics/cohorts")
        
        if "error" not in cohort_data:
            return cohort_data
        
        # Fallback to existing dashboard metrics
        metrics_data = await fetch_analytics_data("/api/dashboard/metrics")
        if "error" not in metrics_data and "metrics" in metrics_data:
            return {
                "cohorts": metrics_data["metrics"].get("cohort_completion", []),
                "source": "dashboard_metrics"
            }
        
        return {"cohorts": [], "source": "fallback"}
    except Exception as e:
        logger.error(f"Error getting cohort analytics: {e}")
        return {"cohorts": [], "error": str(e)}

async def get_activity_analytics() -> Dict[str, Any]:
    """Get activity analytics data"""
    try:
        # Try to fetch from analytics API first
        activity_data = await fetch_analytics_data("/api/analytics/activities")
        
        if "error" not in activity_data:
            return activity_data
        
        # Fallback to existing dashboard metrics
        metrics_data = await fetch_analytics_data("/api/dashboard/metrics")
        if "error" not in metrics_data and "metrics" in metrics_data:
            return {
                "activities": metrics_data["metrics"].get("top_verbs", []),
                "daily_activity": metrics_data["metrics"].get("daily_activity", []),
                "source": "dashboard_metrics"
            }
        
        return {"activities": [], "source": "fallback"}
    except Exception as e:
        logger.error(f"Error getting activity analytics: {e}")
        return {"activities": [], "error": str(e)}

async def get_learner_analytics() -> Dict[str, Any]:
    """Get learner analytics data"""
    try:
        # Try to fetch from analytics API first
        learner_data = await fetch_analytics_data("/api/analytics/learners")
        
        if "error" not in learner_data:
            return learner_data
        
        # Fallback to existing dashboard metrics
        metrics_data = await fetch_analytics_data("/api/dashboard/metrics")
        if "error" not in metrics_data and "metrics" in metrics_data:
            return {
                "learners": {
                    "total_users": metrics_data["metrics"].get("total_users", 0),
                    "active_users_7d": metrics_data["metrics"].get("active_users_7d", 0),
                    "active_users_30d": metrics_data["metrics"].get("active_users_30d", 0)
                },
                "source": "dashboard_metrics"
            }
        
        return {"learners": {}, "source": "fallback"}
    except Exception as e:
        logger.error(f"Error getting learner analytics: {e}")
        return {"learners": {}, "error": str(e)}

@router.get("/enhanced-dashboard", response_class=HTMLResponse)
async def enhanced_dashboard(request: Request):
    """Enhanced analytics dashboard main page"""
    try:
        dashboard_data = await get_dashboard_data()
        
        return templates.TemplateResponse(
            "enhanced_dashboard.html",
            {
                "request": request,
                "dashboard_data": dashboard_data,
                "page_title": "Enhanced Analytics Dashboard",
                "timestamp": datetime.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error rendering enhanced dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")

@router.get("/cohort-analytics", response_class=HTMLResponse)
async def cohort_analytics(request: Request):
    """Cohort analytics page"""
    try:
        cohort_data = await get_cohort_analytics()
        
        return templates.TemplateResponse(
            "components/cohort_analytics.html",
            {
                "request": request,
                "cohort_data": cohort_data,
                "page_title": "Cohort Analytics",
                "timestamp": datetime.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error rendering cohort analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Cohort analytics error: {str(e)}")

@router.get("/activity-analytics", response_class=HTMLResponse)
async def activity_analytics(request: Request):
    """Activity analytics page"""
    try:
        activity_data = await get_activity_analytics()
        
        return templates.TemplateResponse(
            "components/activity_analytics.html",
            {
                "request": request,
                "activity_data": activity_data,
                "page_title": "Activity Analytics",
                "timestamp": datetime.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error rendering activity analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Activity analytics error: {str(e)}")

@router.get("/learner-analytics", response_class=HTMLResponse)
async def learner_analytics(request: Request):
    """Learner analytics page"""
    try:
        learner_data = await get_learner_analytics()
        
        return templates.TemplateResponse(
            "components/learner_analytics.html",
            {
                "request": request,
                "learner_data": learner_data,
                "page_title": "Learner Analytics",
                "timestamp": datetime.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error rendering learner analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Learner analytics error: {str(e)}")

@router.get("/api/enhanced-dashboard/data")
async def get_enhanced_dashboard_data():
    """API endpoint for enhanced dashboard data"""
    try:
        dashboard_data = await get_dashboard_data()
        return {
            "status": "success",
            "data": dashboard_data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting enhanced dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/enhanced-dashboard/cohorts")
async def get_cohort_data():
    """API endpoint for cohort data"""
    try:
        cohort_data = await get_cohort_analytics()
        return {
            "status": "success",
            "data": cohort_data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting cohort data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/enhanced-dashboard/activities")
async def get_activity_data():
    """API endpoint for activity data"""
    try:
        activity_data = await get_activity_analytics()
        return {
            "status": "success",
            "data": activity_data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting activity data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/enhanced-dashboard/learners")
async def get_learner_data():
    """API endpoint for learner data"""
    try:
        learner_data = await get_learner_analytics()
        return {
            "status": "success",
            "data": learner_data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting learner data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/enhanced-dashboard/export")
async def export_dashboard_data(format: str = "json"):
    """Export dashboard data in various formats"""
    try:
        dashboard_data = await get_dashboard_data()
        
        if format.lower() == "csv":
            # Convert to CSV format
            csv_data = convert_to_csv(dashboard_data)
            return {
                "status": "success",
                "format": "csv",
                "data": csv_data,
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Default JSON format
            return {
                "status": "success",
                "format": "json",
                "data": dashboard_data,
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Error exporting dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def convert_to_csv(data: Dict[str, Any]) -> str:
    """Convert dashboard data to CSV format"""
    try:
        csv_lines = []
        
        # Add header
        csv_lines.append("metric,value,timestamp")
        
        # Extract key metrics
        if "metrics" in data and "error" not in data["metrics"]:
            metrics = data["metrics"].get("metrics", {})
            for key, value in metrics.items():
                if isinstance(value, (int, float, str)):
                    csv_lines.append(f"{key},{value},{data.get('timestamp', '')}")
        
        return "\n".join(csv_lines)
    except Exception as e:
        logger.error(f"Error converting to CSV: {e}")
        return "error,conversion_failed," + datetime.now().isoformat()
