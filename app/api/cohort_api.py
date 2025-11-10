"""
API endpoint for cohort filtering and management.
Provides endpoints to get available cohorts and filter data by cohort.
"""

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from typing import Optional
from app.logging_config import get_logger
from app.utils.cohort_filtering import get_all_available_cohorts, build_cohort_filter_sql
from app.services.cohort_sync import get_cohort_sync_service

logger = get_logger("cohort_api")
router = APIRouter()


@router.get("/api/cohorts/available")
async def get_available_cohorts() -> JSONResponse:
    """Get all available cohorts from statements and users."""
    try:
        cohorts = await get_all_available_cohorts()
        
        return JSONResponse({
            "success": True,
            "cohorts": cohorts,
            "total": len(cohorts)
        })
        
    except Exception as e:
        logger.error(f"Error getting available cohorts: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
            "cohorts": []
        }, status_code=500)


@router.post("/api/cohorts/sync")
async def sync_cohorts() -> JSONResponse:
    """Manually trigger cohort sync from users table to cohorts table."""
    try:
        service = get_cohort_sync_service()
        result = await service.sync_cohorts_from_users()
        
        if result.get("success"):
            return JSONResponse({
                "success": True,
                "message": f"Synced {result.get('synced_count', 0)} cohorts",
                "synced_count": result.get("synced_count", 0),
                "cohorts": result.get("cohorts", [])
            })
        else:
            return JSONResponse({
                "success": False,
                "error": result.get("error", "Unknown error")
            }, status_code=500)
            
    except Exception as e:
        logger.error(f"Error syncing cohorts: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

