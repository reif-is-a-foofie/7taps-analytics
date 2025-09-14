"""
BigQuery analytics endpoints with proper query handling and caching.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, Any, Optional, List
import structlog
from datetime import datetime, timedelta

from config.settings import settings
from config.gcp_config import gcp_config
from app.core.exceptions import ValidationError, ExternalServiceError
from app.services.analytics_service import AnalyticsService

logger = structlog.get_logger()
router = APIRouter()


@router.get("/bigquery/status")
async def bigquery_status() -> Dict[str, Any]:
    """Get BigQuery connection and dataset status."""
    try:
        analytics_service = AnalyticsService(gcp_config)
        status = await analytics_service.get_status()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "bigquery": status
        }
        
    except Exception as e:
        logger.error("BigQuery status check failed", error=str(e))
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/bigquery/datasets")
async def list_datasets() -> Dict[str, Any]:
    """List available BigQuery datasets."""
    try:
        analytics_service = AnalyticsService(gcp_config)
        datasets = await analytics_service.list_datasets()
        
        return {
            "datasets": datasets,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to list datasets", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bigquery/tables")
async def list_tables(dataset_id: str = Query(..., description="Dataset ID")) -> Dict[str, Any]:
    """List tables in a specific dataset."""
    try:
        analytics_service = AnalyticsService(gcp_config)
        tables = await analytics_service.list_tables(dataset_id)
        
        return {
            "dataset_id": dataset_id,
            "tables": tables,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to list tables", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bigquery/query")
async def execute_query(
    query: str,
    use_legacy_sql: bool = False,
    max_results: Optional[int] = None
) -> Dict[str, Any]:
    """Execute a BigQuery SQL query."""
    try:
        if not query.strip():
            raise ValidationError("Query cannot be empty")
        
        if len(query) > 10000:  # Reasonable query length limit
            raise ValidationError("Query too long (max 10000 characters)")
        
        analytics_service = AnalyticsService(gcp_config)
        results = await analytics_service.execute_query(
            query, 
            use_legacy_sql=use_legacy_sql,
            max_results=max_results
        )
        
        return {
            "success": True,
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValidationError as e:
        logger.warning("Query validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error("Query execution failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users")
async def get_users(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """Get user analytics data."""
    try:
        analytics_service = AnalyticsService(gcp_config)
        
        query = f"""
        SELECT 
            id,
            email,
            created_at,
            last_activity
        FROM `{gcp_config.project_id}.{settings.bigquery_dataset}.users`
        ORDER BY created_at DESC
        LIMIT {limit}
        OFFSET {offset}
        """
        
        results = await analytics_service.execute_query(query)
        
        return {
            "users": results.get('rows', []),
            "total_rows": results.get('total_rows', 0),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get users", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lessons")
async def get_lessons() -> Dict[str, Any]:
    """Get lesson analytics data."""
    try:
        analytics_service = AnalyticsService(gcp_config)
        
        query = f"""
        SELECT 
            id,
            lesson_name,
            lesson_number,
            created_at
        FROM `{gcp_config.project_id}.{settings.bigquery_dataset}.lessons`
        ORDER BY lesson_number
        """
        
        results = await analytics_service.execute_query(query)
        
        return {
            "lessons": results.get('rows', []),
            "total_rows": results.get('total_rows', 0),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get lessons", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/engagement")
async def get_engagement_metrics(
    days: int = Query(30, ge=1, le=365)
) -> Dict[str, Any]:
    """Get user engagement metrics."""
    try:
        analytics_service = AnalyticsService(gcp_config)
        
        query = f"""
        SELECT 
            DATE(timestamp) as date,
            COUNT(DISTINCT JSON_EXTRACT_SCALAR(actor, '$.mbox')) as unique_users,
            COUNT(*) as total_activities,
            COUNT(DISTINCT JSON_EXTRACT_SCALAR(object, '$.id')) as unique_activities
        FROM `{gcp_config.project_id}.{settings.bigquery_dataset}.xapi_events`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
        """
        
        results = await analytics_service.execute_query(query)
        
        return {
            "engagement_metrics": results.get('rows', []),
            "period_days": days,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get engagement metrics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

