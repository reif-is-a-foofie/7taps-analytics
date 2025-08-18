"""
CSV to xAPI API for 7taps Analytics

This module provides API endpoints for converting focus group CSV data
to xAPI statements and ingesting them through the standard xAPI pipeline.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
import asyncio
import httpx

from app.csv_to_xapi_converter import (
    convert_csv_to_xapi_statements, 
    get_conversion_stats, 
    validate_xapi_statements
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class CSVToXAPIRequest(BaseModel):
    """Request model for CSV to xAPI conversion."""
    csv_data: str
    base_timestamp: Optional[str] = None  # ISO format timestamp
    dry_run: bool = False

class ConversionResult(BaseModel):
    """Result model for conversion operations."""
    success: bool
    total_statements: int
    valid_statements: int
    invalid_statements: int
    conversion_stats: Dict[str, Any]
    validation_results: Dict[str, Any]
    message: str
    ingested_count: Optional[int] = None

class IngestionResult(BaseModel):
    """Result model for ingestion operations."""
    success: bool
    ingested_count: int
    error_count: int
    message: str

async def ingest_xapi_statements(statements: List[Dict[str, Any]]) -> IngestionResult:
    """Ingest xAPI statements through the standard xAPI endpoint."""
    
    try:
        # Get the xAPI endpoint URL
        xapi_endpoint = os.getenv("XAPI_ENDPOINT", "https://seventaps-analytics-5135b3a0701a.herokuapp.com/api/xapi/statements")
        
        # Use HTTP client for batch ingestion
        async with httpx.AsyncClient(timeout=30.0) as client:
            ingested_count = 0
            error_count = 0
            
            # Process statements in batches of 10
            batch_size = 10
            for i in range(0, len(statements), batch_size):
                batch = statements[i:i + batch_size]
                
                try:
                    # Send batch to xAPI endpoint
                    response = await client.post(
                        xapi_endpoint,
                        json={"statements": batch},
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        ingested_count += len(batch)
                        logger.info(f"Successfully ingested batch {i//batch_size + 1}")
                    else:
                        error_count += len(batch)
                        logger.error(f"Failed to ingest batch {i//batch_size + 1}: {response.status_code}")
                        
                except Exception as e:
                    error_count += len(batch)
                    logger.error(f"Error ingesting batch {i//batch_size + 1}: {e}")
                    continue
            
            return IngestionResult(
                success=error_count == 0,
                ingested_count=ingested_count,
                error_count=error_count,
                message=f"Ingested {ingested_count} statements, {error_count} errors"
            )
            
    except Exception as e:
        logger.error(f"Error in batch ingestion: {e}")
        return IngestionResult(
            success=False,
            ingested_count=0,
            error_count=len(statements),
            message=f"Ingestion failed: {str(e)}"
        )

@router.post("/csv-to-xapi/convert", response_model=ConversionResult)
async def convert_csv_to_xapi(request: CSVToXAPIRequest):
    """Convert CSV data to xAPI statements."""
    
    try:
        # Parse base timestamp if provided
        base_timestamp = None
        if request.base_timestamp:
            try:
                base_timestamp = datetime.fromisoformat(request.base_timestamp.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid timestamp format. Use ISO format.")
        
        # Convert CSV to xAPI statements
        logger.info("Converting CSV data to xAPI statements...")
        xapi_statements = convert_csv_to_xapi_statements(request.csv_data, base_timestamp)
        
        # Get conversion statistics
        conversion_stats = get_conversion_stats(xapi_statements)
        
        # Validate statements
        validation_results = validate_xapi_statements(xapi_statements)
        
        # If dry run, return without ingesting
        if request.dry_run:
            return ConversionResult(
                success=True,
                total_statements=len(xapi_statements),
                valid_statements=validation_results["valid"],
                invalid_statements=validation_results["invalid"],
                conversion_stats=conversion_stats,
                validation_results=validation_results,
                message=f"Dry run completed. {len(xapi_statements)} statements converted and validated.",
                ingested_count=0
            )
        
        # Ingest statements through xAPI pipeline
        logger.info("Ingesting converted statements through xAPI pipeline...")
        ingestion_result = await ingest_xapi_statements(xapi_statements)
        
        return ConversionResult(
            success=ingestion_result.success,
            total_statements=len(xapi_statements),
            valid_statements=validation_results["valid"],
            invalid_statements=validation_results["invalid"],
            conversion_stats=conversion_stats,
            validation_results=validation_results,
            message=f"Conversion and ingestion completed. {ingestion_result.ingested_count} statements ingested.",
            ingested_count=ingestion_result.ingested_count
        )
        
    except Exception as e:
        logger.error(f"Error converting CSV to xAPI: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/csv-to-xapi/convert-file")
async def convert_csv_file_to_xapi(
    file: UploadFile = File(...),
    base_timestamp: Optional[str] = Form(None),
    dry_run: bool = Form(False)
):
    """Convert uploaded CSV file to xAPI statements."""
    
    try:
        # Read CSV file content
        csv_content = await file.read()
        csv_data = csv_content.decode('utf-8')
        
        # Create request object
        request = CSVToXAPIRequest(
            csv_data=csv_data,
            base_timestamp=base_timestamp,
            dry_run=dry_run
        )
        
        # Use the existing conversion endpoint
        return await convert_csv_to_xapi(request)
        
    except Exception as e:
        logger.error(f"Error processing CSV file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/csv-to-xapi/template")
async def get_csv_template():
    """Get CSV template and conversion information."""
    
    template_data = {
        "csv_template": {
            "columns": [
                "Learner",
                "Card", 
                "Card type",
                "Lesson Number",
                "Global Q#",
                "PDF Page #",
                "Response"
            ],
            "example_row": [
                "Audrey Todd",
                "Card 6 (Form): 🧠 Quick pulse check...",
                "Form",
                "1",
                "1",
                "6",
                "Screen time Productivity Stress management Sleep Real life connection"
            ],
            "description": "Upload CSV file with focus group data. All columns are required."
        },
        "conversion_info": {
            "process": "CSV → xAPI statements → Standard xAPI pipeline → Normalized tables",
            "preserved_metadata": [
                "Lesson names and URLs",
                "Card types and numbers", 
                "Question text and descriptions",
                "PDF page references",
                "Global question numbering",
                "Cohort information"
            ],
            "xapi_structure": {
                "actor": "Learner name and normalized ID",
                "verb": "http://adlnet.gov/expapi/verbs/answered",
                "object": "Activity with card information",
                "result": "Learner response",
                "context": "All metadata preserved in extensions"
            }
        },
        "lesson_mapping": {
            "1": "Digital Wellness Foundations",
            "2": "Screen Habits Awareness", 
            "3": "Device Relationship",
            "4": "Productivity Focus",
            "5": "Connection Balance",
            "6": "Digital Mindfulness",
            "7": "Technology Boundaries",
            "8": "Digital Detox",
            "9": "Intentional Tech Use",
            "10": "Digital Wellness Integration"
        }
    }
    
    return template_data

@router.post("/csv-to-xapi/batch-ingest")
async def batch_ingest_csv_data(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    base_timestamp: Optional[str] = Form(None)
):
    """Background batch ingestion of CSV data."""
    
    try:
        # Read CSV file content
        csv_content = await file.read()
        csv_data = csv_content.decode('utf-8')
        
        # Convert to xAPI statements
        logger.info("Converting CSV to xAPI statements for background ingestion...")
        
        # Parse base timestamp if provided
        base_timestamp_dt = None
        if base_timestamp:
            try:
                base_timestamp_dt = datetime.fromisoformat(base_timestamp.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid timestamp format.")
        
        xapi_statements = convert_csv_to_xapi_statements(csv_data, base_timestamp_dt)
        
        # Add background task for ingestion
        background_tasks.add_task(ingest_xapi_statements, xapi_statements)
        
        return {
            "success": True,
            "message": f"Background ingestion started for {len(xapi_statements)} statements",
            "statements_count": len(xapi_statements),
            "task_id": f"batch_ingest_{datetime.utcnow().isoformat()}"
        }
        
    except Exception as e:
        logger.error(f"Error starting background ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))
