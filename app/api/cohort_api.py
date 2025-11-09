"""
API endpoint for cohort filtering and management.
Provides endpoints to get available cohorts and filter data by cohort.
"""

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from typing import Optional
from app.logging_config import get_logger
from app.utils.cohort_filtering import get_all_available_cohorts, build_cohort_filter_sql

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

