"""
CSV Upload UI for importing user data with normalization.
"""

from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, Optional
import csv
import io
from app.logging_config import get_logger
from app.services.csv_import_service import csv_import_service

router = APIRouter()
logger = get_logger("csv_upload")
templates = Jinja2Templates(directory="templates")


@router.get("/csv-upload", response_class=HTMLResponse)
async def csv_upload_page(request: Request) -> HTMLResponse:
    """CSV upload page."""
    context = {
        "request": request,
        "active_page": "csv_upload",
        "title": "CSV Upload"
    }
    return templates.TemplateResponse("csv_upload.html", context)


@router.post("/csv-upload/upload")
async def upload_csv(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None)
) -> JSONResponse:
    """Upload and process CSV file with user normalization."""
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are allowed")
        
        # Read file content
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        # Process CSV with user normalization
        result = await csv_import_service.import_csv_data(csv_content, file.filename)
        
        if result["success"]:
            logger.info(f"Successfully imported CSV: {file.filename}")
            return JSONResponse({
                "success": True,
                "message": f"Successfully imported {result['imported_count']} rows from {file.filename}",
                "details": result
            })
        else:
            logger.error(f"Failed to import CSV: {result.get('error', 'Unknown error')}")
            return JSONResponse({
                "success": False,
                "message": f"Failed to import CSV: {result.get('error', 'Unknown error')}",
                "details": result
            }, status_code=400)
            
    except Exception as e:
        logger.error(f"Error uploading CSV: {e}")
        return JSONResponse({
            "success": False,
            "message": f"Error uploading CSV: {str(e)}"
        }, status_code=500)


@router.get("/csv-upload/status")
async def get_upload_status() -> JSONResponse:
    """Get status of CSV uploads and user normalization."""
    try:
        # Get user merge report
        report = await csv_import_service.get_user_merge_report()
        
        return JSONResponse({
            "success": True,
            "report": report
        })
        
    except Exception as e:
        logger.error(f"Error getting upload status: {e}")
        return JSONResponse({
            "success": False,
            "message": f"Error getting status: {str(e)}"
        }, status_code=500)


@router.get("/csv-upload/sample")
async def download_sample_csv() -> JSONResponse:
    """Download a sample CSV template."""
    sample_data = [
        {
            "email": "john.doe@example.com",
            "name": "John Doe",
            "feedback": "Great course! Learned a lot.",
            "completion_date": "2025-09-22",
            "rating": "5"
        },
        {
            "email": "jane.smith@example.com", 
            "name": "Jane Smith",
            "feedback": "Very helpful content.",
            "completion_date": "2025-09-22",
            "rating": "4"
        }
    ]
    
    # Convert to CSV
    output = io.StringIO()
    fieldnames = ["email", "name", "feedback", "completion_date", "rating"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(sample_data)
    
    csv_content = output.getvalue()
    output.close()
    
    return JSONResponse({
        "success": True,
        "csv_content": csv_content,
        "filename": "sample_user_data.csv"
    })

