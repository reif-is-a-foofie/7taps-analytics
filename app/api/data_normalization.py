"""
Data Normalization API endpoints for 7taps xAPI analytics.

This module provides API endpoints for data normalization, including table creation,
statement processing, and statistics retrieval.
"""

import os
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import asyncio

from app.data_normalization import DataNormalizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class NormalizationRequest(BaseModel):
    """Request model for statement normalization."""
    statement: Dict[str, Any]
    
class BatchNormalizationRequest(BaseModel):
    """Request model for batch statement normalization."""
    statements: List[Dict[str, Any]]
    
class NormalizationResponse(BaseModel):
    """Response model for normalization operations."""
    success: bool
    message: str
    statement_id: str = None
    processed_count: int = 0
    error_count: int = 0
    timestamp: datetime = datetime.utcnow()
    
class NormalizationStats(BaseModel):
    """Response model for normalization statistics."""
    actors: int
    activities: int
    verbs: int
    statements: int
    processed_count: int
    error_count: int
    timestamp: datetime = datetime.utcnow()

# Global normalizer instance
normalizer = DataNormalizer()

@router.post("/normalize/statement", response_model=NormalizationResponse)
async def normalize_statement(request: NormalizationRequest):
    """Normalize a single xAPI statement."""
    try:
        await normalizer.process_statement_normalization(request.statement)
        
        return NormalizationResponse(
            success=True,
            message="Statement normalized successfully",
            statement_id=request.statement.get('id'),
            processed_count=1,
            error_count=0
        )
        
    except Exception as e:
        logger.error(f"Error normalizing statement: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/normalize/batch", response_model=NormalizationResponse)
async def normalize_batch_statements(request: BatchNormalizationRequest):
    """Normalize a batch of xAPI statements."""
    try:
        processed_count = 0
        error_count = 0
        
        for statement in request.statements:
            try:
                await normalizer.process_statement_normalization(statement)
                processed_count += 1
            except Exception as e:
                logger.error(f"Error normalizing statement {statement.get('id')}: {e}")
                error_count += 1
        
        return NormalizationResponse(
            success=True,
            message=f"Batch normalization completed. Processed: {processed_count}, Errors: {error_count}",
            processed_count=processed_count,
            error_count=error_count
        )
        
    except Exception as e:
        logger.error(f"Error in batch normalization: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/normalize/setup", response_model=NormalizationResponse)
async def setup_normalization_tables():
    """Create normalized tables for analytics."""
    try:
        await normalizer.create_normalized_tables()
        
        return NormalizationResponse(
            success=True,
            message="Normalization tables created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error setting up normalization tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/normalize/stats", response_model=NormalizationStats)
async def get_normalization_stats():
    """Get normalization statistics."""
    try:
        stats = await normalizer.get_normalization_stats()
        
        return NormalizationStats(**stats)
        
    except Exception as e:
        logger.error(f"Error getting normalization stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/normalize/process-existing", response_model=NormalizationResponse)
async def process_existing_statements(background_tasks: BackgroundTasks):
    """Process existing statements from the flat table for normalization."""
    try:
        # This would process existing statements from statements_flat table
        # For now, we'll return a placeholder response
        background_tasks.add_task(process_existing_statements_task)
        
        return NormalizationResponse(
            success=True,
            message="Background processing of existing statements started"
        )
        
    except Exception as e:
        logger.error(f"Error starting existing statement processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_existing_statements_task():
    """Background task to process existing statements."""
    try:
        # This would query the statements_flat table and process each statement
        # through the normalization pipeline
        logger.info("Starting background processing of existing statements")
        
        # Placeholder for actual implementation
        # async with normalizer.get_db_connection() as conn:
        #     with conn.cursor() as cursor:
        #         cursor.execute("SELECT raw_statement FROM statements_flat WHERE normalized = false")
        #         statements = cursor.fetchall()
        #         
        #         for statement_row in statements:
        #             statement = json.loads(statement_row['raw_statement'])
        #             await normalizer.process_statement_normalization(statement)
        
        logger.info("Background processing of existing statements completed")
        
    except Exception as e:
        logger.error(f"Error in background statement processing: {e}")

@router.get("/normalize/health")
async def normalization_health_check():
    """Health check for normalization service."""
    try:
        # Test database connection
        stats = await normalizer.get_normalization_stats()
        
        return {
            "status": "healthy",
            "database_connected": True,
            "tables_available": len([k for k, v in stats.items() if isinstance(v, int)]),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Normalization health check failed: {e}")
        return {
            "status": "unhealthy",
            "database_connected": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
