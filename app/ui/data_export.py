"""
Data Export Interface for Learning Locker.

This module provides an interface for exporting xAPI statements
in various formats (JSON, CSV, XML).
"""

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, List, Optional
import json
import csv
import io
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import os

from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("data_export")
templates = Jinja2Templates(directory="app/templates")

class DataExporter:
    """Data export functionality."""
    
    def __init__(self):
        self.api_base = os.getenv("API_BASE_URL", "") + "/api"
        
    async def get_export_data(self,
                             format_type: str = "json",
                             start_date: Optional[str] = None,
                             end_date: Optional[str] = None,
                             actor_filter: Optional[str] = None,
                             verb_filter: Optional[str] = None,
                             object_filter: Optional[str] = None,
                             limit: int = 1000) -> Dict[str, Any]:
        """Get data for export with filtering."""
        try:
            # Mock export data
            # In production, this would query the database
            statements = [
                {
                    "id": "statement-001",
                    "actor": {
                        "account": {"name": "user1@7taps.com"},
                        "name": "Test User 1"
                    },
                    "verb": {
                        "id": "http://adlnet.gov/expapi/verbs/completed",
                        "display": {"en-US": "completed"}
                    },
                    "object": {
                        "id": "http://7taps.com/activities/course-1",
                        "objectType": "Activity",
                        "definition": {
                            "name": {"en-US": "Introduction Course"},
                            "description": {"en-US": "Basic introduction to the platform"}
                        }
                    },
                    "timestamp": "2025-01-05T10:30:00Z",
                    "result": {
                        "score": {"raw": 85, "min": 0, "max": 100},
                        "success": True,
                        "completion": True
                    },
                    "context": {
                        "platform": "7taps",
                        "language": "en-US"
                    }
                },
                {
                    "id": "statement-002",
                    "actor": {
                        "account": {"name": "user2@7taps.com"},
                        "name": "Test User 2"
                    },
                    "verb": {
                        "id": "http://adlnet.gov/expapi/verbs/attempted",
                        "display": {"en-US": "attempted"}
                    },
                    "object": {
                        "id": "http://7taps.com/activities/quiz-1",
                        "objectType": "Activity",
                        "definition": {
                            "name": {"en-US": "Knowledge Quiz"},
                            "description": {"en-US": "Test your knowledge"}
                        }
                    },
                    "timestamp": "2025-01-05T11:15:00Z",
                    "result": {
                        "success": True
                    },
                    "context": {
                        "platform": "7taps",
                        "language": "en-US"
                    }
                }
            ]
            
            # Apply filters
            if actor_filter:
                statements = [s for s in statements if actor_filter.lower() in s.get("actor", {}).get("account", {}).get("name", "").lower()]
            
            if verb_filter:
                statements = [s for s in statements if verb_filter.lower() in s.get("verb", {}).get("id", "").lower()]
            
            if object_filter:
                statements = [s for s in statements if object_filter.lower() in s.get("object", {}).get("id", "").lower()]
            
            # Apply date filters
            if start_date:
                from app.utils.timestamp_utils import parse_timestamp
                start_dt = parse_timestamp(start_date)
                statements = [s for s in statements if parse_timestamp(s["timestamp"]) >= start_dt]
            
            if end_date:
                from app.utils.timestamp_utils import parse_timestamp
                end_dt = parse_timestamp(end_date)
                statements = [s for s in statements if parse_timestamp(s["timestamp"]) <= end_dt]
            
            # Apply limit
            statements = statements[:limit]
            
            return {
                "statements": statements,
                "export_info": {
                    "format": format_type,
                    "total_statements": len(statements),
                    "export_date": datetime.now(timezone.utc).isoformat(),
                    "filters_applied": {
                        "start_date": start_date,
                        "end_date": end_date,
                        "actor": actor_filter,
                        "verb": verb_filter,
                        "object": object_filter
                    }
                }
            }
            
        except Exception as e:
            logger.error("Failed to get export data", error=e)
            return {"error": str(e)}
    
    def export_to_json(self, data: Dict[str, Any]) -> str:
        """Export data to JSON format."""
        try:
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Failed to export to JSON", error=e)
            raise
    
    def export_to_csv(self, data: Dict[str, Any]) -> str:
        """Export data to CSV format."""
        try:
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                "Statement ID", "Actor", "Verb", "Object", "Timestamp", 
                "Score", "Success", "Completion", "Platform"
            ])
            
            # Write data
            for statement in data["statements"]:
                score = ""
                if statement.get("result", {}).get("score"):
                    score = f"{statement['result']['score']['raw']}/{statement['result']['score']['max']}"
                
                writer.writerow([
                    statement["id"],
                    statement["actor"]["account"]["name"],
                    statement["verb"]["id"].split("/")[-1],
                    statement["object"]["id"].split("/")[-1],
                    statement["timestamp"],
                    score,
                    statement.get("result", {}).get("success", ""),
                    statement.get("result", {}).get("completion", ""),
                    statement.get("context", {}).get("platform", "")
                ])
            
            return output.getvalue()
        except Exception as e:
            logger.error("Failed to export to CSV", error=e)
            raise
    
    def export_to_xml(self, data: Dict[str, Any]) -> str:
        """Export data to XML format."""
        try:
            root = ET.Element("xapi_statements")
            root.set("export_date", data["export_info"]["export_date"])
            root.set("total_statements", str(data["export_info"]["total_statements"]))
            
            for statement in data["statements"]:
                stmt_elem = ET.SubElement(root, "statement")
                stmt_elem.set("id", statement["id"])
                stmt_elem.set("timestamp", statement["timestamp"])
                
                # Actor
                actor_elem = ET.SubElement(stmt_elem, "actor")
                actor_elem.set("name", statement["actor"]["account"]["name"])
                
                # Verb
                verb_elem = ET.SubElement(stmt_elem, "verb")
                verb_elem.set("id", statement["verb"]["id"])
                verb_elem.set("display", statement["verb"]["display"]["en-US"])
                
                # Object
                obj_elem = ET.SubElement(stmt_elem, "object")
                obj_elem.set("id", statement["object"]["id"])
                obj_elem.set("type", statement["object"]["objectType"])
                
                # Result
                if statement.get("result"):
                    result_elem = ET.SubElement(stmt_elem, "result")
                    if statement["result"].get("score"):
                        result_elem.set("score", f"{statement['result']['score']['raw']}/{statement['result']['score']['max']}")
                    result_elem.set("success", str(statement["result"].get("success", "")))
                    result_elem.set("completion", str(statement["result"].get("completion", "")))
            
            return ET.tostring(root, encoding='unicode', method='xml')
        except Exception as e:
            logger.error("Failed to export to XML", error=e)
            raise

# Global exporter instance
exporter = DataExporter()

@router.get("/data-export", response_class=HTMLResponse)
async def data_export_page(request: Request):
    """Data export main page."""
    try:
        # Get default date range (last 30 days)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=30)
        
        context = {
            "request": request,
            "default_start_date": start_date.strftime("%Y-%m-%d"),
            "default_end_date": end_date.strftime("%Y-%m-%d"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return templates.TemplateResponse("data_export.html", context)
        
    except Exception as e:
        logger.error("Failed to render data export page", error=e)
        raise HTTPException(status_code=500, detail=f"Export page error: {str(e)}")

@router.post("/api/export/download")
async def download_export(format_type: str = Query("json"),
                         start_date: Optional[str] = Query(None),
                         end_date: Optional[str] = Query(None),
                         actor_filter: Optional[str] = Query(None),
                         verb_filter: Optional[str] = Query(None),
                         object_filter: Optional[str] = Query(None),
                         limit: int = Query(1000, ge=1, le=10000)):
    """Download exported data."""
    try:
        # Get export data
        data = await exporter.get_export_data(
            format_type=format_type,
            start_date=start_date,
            end_date=end_date,
            actor_filter=actor_filter,
            verb_filter=verb_filter,
            object_filter=object_filter,
            limit=limit
        )
        
        if "error" in data:
            raise HTTPException(status_code=500, detail=data["error"])
        
        # Generate export content
        if format_type == "json":
            content = exporter.export_to_json(data)
            filename = f"xapi_statements_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
            media_type = "application/json"
        elif format_type == "csv":
            content = exporter.export_to_csv(data)
            filename = f"xapi_statements_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
            media_type = "text/csv"
        elif format_type == "xml":
            content = exporter.export_to_xml(data)
            filename = f"xapi_statements_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.xml"
            media_type = "application/xml"
        else:
            raise HTTPException(status_code=400, detail="Unsupported format type")
        
        # Create file response
        file_content = io.BytesIO(content.encode('utf-8'))
        
        return FileResponse(
            file_content,
            filename=filename,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error("Failed to download export", error=e)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.get("/api/export/preview")
async def preview_export(format_type: str = Query("json"),
                        start_date: Optional[str] = Query(None),
                        end_date: Optional[str] = Query(None),
                        actor_filter: Optional[str] = Query(None),
                        verb_filter: Optional[str] = Query(None),
                        object_filter: Optional[str] = Query(None),
                        limit: int = Query(10, ge=1, le=100)):
    """Preview export data."""
    try:
        data = await exporter.get_export_data(
            format_type=format_type,
            start_date=start_date,
            end_date=end_date,
            actor_filter=actor_filter,
            verb_filter=verb_filter,
            object_filter=object_filter,
            limit=limit
        )
        
        if "error" in data:
            return {"error": data["error"]}
        
        # Generate preview content
        if format_type == "json":
            content = exporter.export_to_json(data)
        elif format_type == "csv":
            content = exporter.export_to_csv(data)
        elif format_type == "xml":
            content = exporter.export_to_xml(data)
        else:
            return {"error": "Unsupported format type"}
        
        return {
            "preview": content,
            "format": format_type,
            "total_statements": data["export_info"]["total_statements"],
            "preview_count": len(data["statements"])
        }
        
    except Exception as e:
        logger.error("Failed to preview export", error=e)
        return {"error": str(e)}

@router.get("/api/export/stats")
async def get_export_stats():
    """Get export statistics."""
    try:
        # Mock export statistics
        stats = {
            "total_exports_today": 5,
            "total_statements_exported": 1250,
            "popular_formats": [
                {"format": "json", "count": 15},
                {"format": "csv", "count": 8},
                {"format": "xml", "count": 3}
            ],
            "export_sizes": {
                "json": "2.3 MB",
                "csv": "1.8 MB",
                "xml": "3.1 MB"
            }
        }
        
        return stats
        
    except Exception as e:
        logger.error("Failed to get export stats", error=e)
        return {"error": str(e)} 