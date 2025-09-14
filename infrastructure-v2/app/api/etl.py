"""
ETL API endpoints for testing and monitoring ETL processes.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import asyncio
from datetime import datetime

from app.services.etl_service import ETLService
from app.core.exceptions import ExternalServiceError

router = APIRouter()

# Global ETL service instance
_etl_service = None

def get_etl_service() -> ETLService:
    """Get or create ETL service instance."""
    global _etl_service
    if _etl_service is None:
        _etl_service = ETLService()
    return _etl_service

@router.get("/test-etl-streaming")
async def test_etl_streaming() -> Dict[str, Any]:
    """
    Test endpoint for ETL streaming.
    
    Returns the last processed xAPI statement and triggers a new processing cycle.
    """
    try:
        etl_service = get_etl_service()
        
        # Start streaming ETL
        result = await etl_service.start_streaming_etl()
        
        return {
            "status": "success",
            "module": "b.02_streaming_etl",
            "message": "ETL streaming test completed successfully",
            "result": result
        }
        
    except ExternalServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ETL streaming test failed: {str(e)}"
        )

@router.get("/etl-status")
async def get_etl_status() -> Dict[str, Any]:
    """
    Get current ETL processing status.
    """
    try:
        etl_service = get_etl_service()
        status = await etl_service.get_etl_status()
        
        return {
            "status": "success",
            "etl_status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ExternalServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ETL status check failed: {str(e)}"
        )

@router.get("/etl-metrics")
async def get_etl_metrics() -> Dict[str, Any]:
    """
    Get detailed ETL processing metrics.
    """
    try:
        etl_service = get_etl_service()
        metrics = await etl_service.get_processing_metrics()
        
        return {
            "status": "success",
            "metrics": metrics
        }
        
    except ExternalServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ETL metrics retrieval failed: {str(e)}"
        )

@router.post("/etl/process-statement")
async def process_single_statement(statement: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single xAPI statement through the ETL pipeline.
    """
    try:
        etl_service = get_etl_service()
        result = await etl_service.process_xapi_statement(statement)
        
        return {
            "status": "success",
            "result": result
        }
        
    except ExternalServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Statement processing failed: {str(e)}"
        )

@router.post("/etl/process-batch")
async def process_batch_statements(statements: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process multiple xAPI statements through the ETL pipeline.
    """
    try:
        etl_service = get_etl_service()
        result = await etl_service.process_batch(statements)
        
        return {
            "status": "success",
            "result": result
        }
        
    except ExternalServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch processing failed: {str(e)}"
        )

@router.get("/test-etl-incremental")
async def test_etl_incremental() -> Dict[str, Any]:
    """
    Test endpoint for incremental ETL.
    
    Triggers an incremental ETL run and returns processing results.
    """
    try:
        etl_service = get_etl_service()
        
        # Start incremental ETL
        result = await etl_service.start_incremental_etl()
        
        return {
            "status": "success",
            "module": "b.03_incremental_etl",
            "message": "Incremental ETL test completed successfully",
            "result": result
        }
        
    except ExternalServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Incremental ETL test failed: {str(e)}"
        ) 