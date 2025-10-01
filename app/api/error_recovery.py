"""
Error Recovery API endpoints for managing failed xAPI statements.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
import logging

from app.etl.error_recovery import get_error_recovery

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/error-recovery", tags=["error-recovery"])


@router.get("/failed-statements")
async def get_failed_statements(
    limit: int = Query(50, ge=1, le=100),
    processing_stage: Optional[str] = Query(None),
    error_type: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get failed statements for review and retry."""
    try:
        error_recovery = get_error_recovery()
        failed_statements = error_recovery.get_failed_statements(
            limit=limit,
            processing_stage=processing_stage,
            error_type=error_type
        )
        
        return {
            "success": True,
            "failed_statements": failed_statements,
            "count": len(failed_statements),
            "limit": limit,
            "filters": {
                "processing_stage": processing_stage,
                "error_type": error_type
            }
        }
    except Exception as e:
        logger.error(f"Failed to get failed statements: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retry/{statement_id}")
async def retry_failed_statement(statement_id: str) -> Dict[str, Any]:
    """Retry a specific failed statement."""
    try:
        error_recovery = get_error_recovery()
        result = error_recovery.retry_failed_statement(statement_id)
        
        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "retry_count": result["retry_count"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry statement {statement_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resolve/{statement_id}")
async def mark_statement_resolved(statement_id: str) -> Dict[str, Any]:
    """Mark a failed statement as resolved."""
    try:
        error_recovery = get_error_recovery()
        success = error_recovery.mark_statement_resolved(statement_id)
        
        if success:
            return {
                "success": True,
                "message": f"Statement {statement_id} marked as resolved"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to mark statement as resolved")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark statement {statement_id} as resolved: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics")
async def get_error_analytics() -> Dict[str, Any]:
    """Get analytics about failed statements."""
    try:
        error_recovery = get_error_recovery()
        analytics = error_recovery.get_error_analytics()
        
        return {
            "success": True,
            "analytics": analytics
        }
    except Exception as e:
        logger.error(f"Failed to get error analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
