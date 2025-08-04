"""
ETL API endpoints for testing and monitoring ETL processes.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import asyncio

from app.etl_streaming import etl_processor
from app.etl_incremental import incremental_processor

router = APIRouter()

@router.get("/test-etl-streaming")
async def test_etl_streaming() -> Dict[str, Any]:
    """
    Test endpoint for ETL streaming.
    
    Returns the last processed xAPI statement and triggers a new processing cycle.
    """
    try:
        # Process up to 5 messages from the stream
        processed_statements = await etl_processor.process_stream(max_messages=5)
        
        # Get last processed statement
        last_statement = await etl_processor.get_last_processed_statement()
        
        return {
            "status": "success",
            "module": "b.02_streaming_etl",
            "processed_count": len(processed_statements),
            "last_processed_statement": last_statement,
            "message": "ETL streaming test completed successfully"
        }
        
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
        last_statement = await etl_processor.get_last_processed_statement()
        
        return {
            "status": "active",
            "module": "b.02_streaming_etl",
            "last_processed_statement": last_statement,
            "mcp_servers": {
                "python": etl_processor.mcp_python_url,
                "postgres": etl_processor.mcp_postgres_url
            },
            "redis_stream": etl_processor.stream_name
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get ETL status: {str(e)}"
        )

@router.get("/test-etl-incremental")
async def test_etl_incremental() -> Dict[str, Any]:
    """
    Test endpoint for incremental ETL.
    
    Triggers an incremental ETL run and returns processing results.
    """
    try:
        # Run incremental ETL for last 24 hours
        result = await incremental_processor.run_incremental_etl(hours_back=24)
        
        # Get processing stats
        stats = await incremental_processor.get_processing_stats()
        
        return {
            "status": "success",
            "module": "b.03_incremental_etl",
            "incremental_result": result,
            "processing_stats": stats,
            "message": "Incremental ETL test completed successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Incremental ETL test failed: {str(e)}"
        )

@router.get("/incremental-status")
async def get_incremental_status() -> Dict[str, Any]:
    """
    Get incremental ETL processing status and statistics.
    """
    try:
        stats = await incremental_processor.get_processing_stats()
        
        return {
            "status": "active",
            "module": "b.03_incremental_etl",
            "processing_stats": stats,
            "mcp_servers": {
                "python": incremental_processor.mcp_python_url,
                "postgres": incremental_processor.mcp_postgres_url
            },
            "redis_stream": incremental_processor.stream_name
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get incremental ETL status: {str(e)}"
        ) 