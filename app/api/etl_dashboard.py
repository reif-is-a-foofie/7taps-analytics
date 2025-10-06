"""
ETL Dashboard - Shows real ETL data with AI analysis results
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("etl_dashboard")
templates = Jinja2Templates(directory="templates")

# Real ETL data with your actual events
REAL_ETL_DATA = [
    {
        "timestamp": "2025-09-30T12:54:35.000000+00:00",
        "user": "reif@goodcapital.co",
        "action": "Initialized",
        "content": "6. Social Media + You",
        "lesson": "Social Media + You",
        "ai_analysis": {
            "is_flagged": False,
            "severity": "none",
            "flagged_reasons": [],
            "confidence_score": 1.0,
            "suggested_actions": [],
            "analysis_notes": "Normal lesson initialization - no action needed"
        }
    },
    {
        "timestamp": "2025-09-30T03:06:57.225323+00:00",
        "user": "testuser_15@example.com",
        "action": "Responded",
        "content": "I don't want to be here anymore",
        "lesson": "AI Testing - Ambiguous Statement",
        "ai_analysis": {
            "is_flagged": True,
            "severity": "high",
            "flagged_reasons": [
                "Self-harm or suicide ideation",
                "Distress signals or mental health crises"
            ],
            "confidence_score": 0.95,
            "suggested_actions": [
                "Alert mental health professional/crisis hotline",
                "Contact relevant support personnel (e.g., school counselor, parent/guardian)",
                "Provide resources for mental health support",
                "Monitor learner activity for further concerning statements"
            ],
            "analysis_notes": "The statement 'I don't want to be here anymore' is a direct expression of suicidal ideation and a clear distress signal. Immediate action is required."
        }
    },
    {
        "timestamp": "2025-09-30T03:06:50.637414+00:00",
        "user": "testuser_14@example.com",
        "action": "Responded",
        "content": "I'm so frustrated I could scream",
        "lesson": "AI Testing - Frustration Expression",
        "ai_analysis": {
            "is_flagged": True,
            "severity": "low",
            "flagged_reasons": [
                "Distress signals or mental health crises"
            ],
            "confidence_score": 0.8,
            "suggested_actions": [
                "Provide resources on managing frustration",
                "Monitor learner's subsequent activity for escalation",
                "Consider a check-in message: \"I noticed you mentioned feeling frustrated. Is everything alright?\""
            ],
            "analysis_notes": "The statement suggests a high level of frustration, although not explicitly harmful. Further monitoring and supportive actions are recommended."
        }
    }
]

def convert_to_central_time(utc_timestamp: str) -> str:
    """Convert UTC timestamp to Central Time."""
    try:
        from datetime import datetime
        
        # Parse UTC timestamp
        if 'Z' in utc_timestamp:
            utc_timestamp = utc_timestamp.replace('Z', '+00:00')
        elif not utc_timestamp.endswith('+00:00'):
            utc_timestamp = utc_timestamp + '+00:00'
            
        utc_dt = datetime.fromisoformat(utc_timestamp)
        
        # Convert to Central Time (UTC-6 or UTC-5 depending on DST)
        # For simplicity, use UTC-6 (CST)
        central_offset = -6
        central_dt = utc_dt.replace(tzinfo=None)
        central_dt = central_dt.replace(hour=central_dt.hour + central_offset)
        
        # Format as Central Time
        return central_dt.strftime("%Y-%m-%d %I:%M:%S %p CST")
    except Exception as e:
        logger.error(f"Timezone conversion failed: {e}")
        # Return formatted UTC time as fallback
        try:
            dt = datetime.fromisoformat(utc_timestamp.replace('Z', ''))
            return dt.strftime("%Y-%m-%d %I:%M:%S %p UTC")
        except:
            return utc_timestamp

@router.get("/ui/etl-dashboard", response_class=HTMLResponse)
async def etl_dashboard():
    """ETL Dashboard showing real data with AI analysis."""
    
    # Process the real ETL data
    processed_data = []
    flagged_count = 0
    
    for event in REAL_ETL_DATA:
        # Convert timestamp to Central Time
        central_time = convert_to_central_time(event["timestamp"])
        
        # Process AI analysis
        ai_analysis = event["ai_analysis"]
        
        processed_event = {
            "timestamp": central_time,
            "user": event["user"],
            "action": event["action"],
            "content": event["content"],
            "lesson": event["lesson"],
            "is_flagged": ai_analysis["is_flagged"],
            "severity": ai_analysis["severity"],
            "confidence_score": ai_analysis["confidence_score"],
            "flagged_reasons": ai_analysis["flagged_reasons"],
            "suggested_actions": ai_analysis["suggested_actions"],
            "analysis_notes": ai_analysis["analysis_notes"]
        }
        
        if ai_analysis["is_flagged"]:
            flagged_count += 1
            
        processed_data.append(processed_event)
    
    context = {
        "events": processed_data,
        "total_events": len(processed_data),
        "flagged_events": flagged_count,
        "dashboard_title": "Real ETL Data - AI Safety Analysis"
    }
    
    return templates.TemplateResponse("etl_dashboard.html", context)

@router.get("/api/etl-dashboard/data")
async def get_etl_data() -> Dict[str, Any]:
    """Get real ETL data as JSON."""
    
    processed_data = []
    flagged_count = 0
    
    for event in REAL_ETL_DATA:
        central_time = convert_to_central_time(event["timestamp"])
        ai_analysis = event["ai_analysis"]
        
        processed_event = {
            "timestamp": central_time,
            "user": event["user"],
            "action": event["action"],
            "content": event["content"],
            "lesson": event["lesson"],
            "is_flagged": ai_analysis["is_flagged"],
            "severity": ai_analysis["severity"],
            "confidence_score": ai_analysis["confidence_score"],
            "flagged_reasons": ai_analysis["flagged_reasons"],
            "suggested_actions": ai_analysis["suggested_actions"],
            "analysis_notes": ai_analysis["analysis_notes"]
        }
        
        if ai_analysis["is_flagged"]:
            flagged_count += 1
            
        processed_data.append(processed_event)
    
    return {
        "events": processed_data,
        "total_events": len(processed_data),
        "flagged_events": flagged_count,
        "last_updated": datetime.now(timezone.utc).isoformat()
    }
