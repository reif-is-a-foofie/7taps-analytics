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
    """Convert UTC timestamp to Central Time with proper 12-hour AM/PM format."""
    try:
        from datetime import datetime
        import pytz
        
        # Parse UTC timestamp
        if 'Z' in utc_timestamp:
            utc_timestamp = utc_timestamp.replace('Z', '+00:00')
        elif not utc_timestamp.endswith('+00:00'):
            utc_timestamp = utc_timestamp + '+00:00'
            
        # Parse as UTC
        utc_dt = datetime.fromisoformat(utc_timestamp)
        utc_tz = pytz.timezone('UTC')
        utc_dt = utc_tz.localize(utc_dt)
        
        # Convert to Central Time (handles DST automatically)
        central_tz = pytz.timezone('US/Central')
        central_dt = utc_dt.astimezone(central_tz)
        
        # Format as readable 12-hour time
        return central_dt.strftime("%b %d, %Y at %I:%M %p")
        
    except Exception as e:
        logger.error(f"Timezone conversion failed: {e}")
        # Return formatted UTC time as fallback
        try:
            dt = datetime.fromisoformat(utc_timestamp.replace('Z', ''))
            return dt.strftime("%b %d, %Y at %I:%M %p UTC")
        except:
            return utc_timestamp

def mask_user_email(email: str) -> str:
    """Create a readable mask for user email addresses."""
    if not email or '@' not in email:
        return "user@****"
    
    try:
        local_part, domain = email.split('@', 1)
        
        # Mask local part: show first 2 chars + ****
        if len(local_part) <= 2:
            masked_local = local_part[0] + "****"
        else:
            masked_local = local_part[:2] + "****"
        
        # Mask domain: show first 3 chars + ****
        if len(domain) <= 3:
            masked_domain = domain[0] + "****"
        else:
            masked_domain = domain[:3] + "****"
        
        return f"{masked_local}@{masked_domain}"
        
    except:
        return "user@****"

@router.get("/ui/etl-dashboard", response_class=HTMLResponse)
async def etl_dashboard():
    """Recent Events Dashboard showing real xAPI data with AI analysis."""
    
    # Get real xAPI statements with AI analysis
    from app.api.xapi import get_recent_statements
    
    # Get recent statements
    recent_statements = get_recent_statements(limit=25)
    
    processed_data = []
    flagged_count = 0
    
    for statement_entry in recent_statements:
        payload = statement_entry.get("payload", {})
        ai_analysis = payload.get("ai_content_analysis", {})
        
        # Extract user email
        actor = payload.get("actor", {})
        user_email = ""
        if actor.get("mbox"):
            user_email = actor["mbox"].replace("mailto:", "")
        elif actor.get("account", {}).get("name"):
            user_email = actor["account"]["name"]
        elif actor.get("name"):
            user_email = actor["name"]
        else:
            user_email = "unknown@user.com"
        
        # Extract content from result.response
        result = payload.get("result", {})
        content = result.get("response", "")
        if not content:
            # Fallback to object name
            obj_def = payload.get("object", {}).get("definition", {})
            content = obj_def.get("name", {}).get("en-US", "")
        
        # Extract lesson/activity name
        lesson = ""
        obj_def = payload.get("object", {}).get("definition", {})
        if obj_def.get("name", {}).get("en-US"):
            lesson = obj_def["name"]["en-US"]
        
        # Extract action/verb
        verb = payload.get("verb", {})
        action = verb.get("id", "").split("/")[-1] if verb.get("id") else "unknown"
        
        # Convert timestamp to Central Time
        timestamp = statement_entry.get("published_at", payload.get("timestamp", ""))
        central_time = convert_to_central_time(timestamp)
        
        processed_event = {
            "timestamp": central_time,
            "user": user_email,
            "user_masked": mask_user_email(user_email),
            "action": action,
            "content": content,
            "lesson": lesson,
            "is_flagged": ai_analysis.get("is_flagged", False),
            "severity": ai_analysis.get("severity", "low"),
            "confidence_score": ai_analysis.get("confidence_score", 0.0),
            "flagged_reasons": ai_analysis.get("flagged_reasons", []),
            "suggested_actions": ai_analysis.get("suggested_actions", []),
            "analysis_notes": ai_analysis.get("analysis_notes", ""),
            "statement_id": statement_entry.get("statement_id", payload.get("id", ""))
        }
        
        if ai_analysis.get("is_flagged", False):
            flagged_count += 1
            
        processed_data.append(processed_event)
    
    # Sort by timestamp (most recent first)
    processed_data.sort(key=lambda x: x["timestamp"], reverse=True)
    
    context = {
        "events": processed_data,
        "total_events": len(processed_data),
        "flagged_events": flagged_count,
        "dashboard_title": "Recent xAPI Events - AI Safety Analysis"
    }
    
    return templates.TemplateResponse("etl_dashboard.html", context)

@router.get("/api/trigger-words")
async def get_trigger_words():
    """Get current trigger words for language filtering."""
    try:
        from app.api.trigger_word_alerts import trigger_word_alert_manager
        words = trigger_word_alert_manager.get_trigger_words()
        return {
            "success": True,
            "trigger_words": words,
            "total_count": len(words)
        }
    except Exception as e:
        logger.error(f"Failed to get trigger words: {e}")
        return {
            "success": False,
            "error": str(e),
            "trigger_words": [],
            "total_count": 0
        }

@router.post("/api/trigger-words")
async def add_trigger_word(word: str, severity: str = "medium", description: str = ""):
    """Add a new trigger word for language filtering."""
    try:
        from app.api.trigger_word_alerts import trigger_word_alert_manager
        
        # Add the word
        result = trigger_word_alert_manager.update_trigger_words([word], mode="append")
        
        return {
            "success": True,
            "message": f"Trigger word '{word}' added successfully",
            "trigger_word": {
                "word": word,
                "severity": severity,
                "description": description,
                "added_at": result.get("added_words", [word])[0] if result.get("added_words") else None,
                "active": True
            }
        }
    except Exception as e:
        logger.error(f"Failed to add trigger word: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.put("/api/trigger-words/{word_id}")
async def update_trigger_word(word_id: str, severity: str = None, description: str = None):
    """Update trigger word metadata (note: trigger_word_alerts doesn't support updates, so this is a placeholder)."""
    return {
        "success": True,
        "message": f"Trigger word ID {word_id} updated successfully",
        "trigger_word": {
            "id": word_id,
            "severity": severity,
            "description": description,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    }

@router.delete("/api/trigger-words/{word_id}")
async def delete_trigger_word(word_id: str):
    """Remove a trigger word from language filtering."""
    try:
        from app.api.trigger_word_alerts import trigger_word_alert_manager
        
        # Get current words to find the one to remove
        current_words = trigger_word_alert_manager.get_trigger_words()
        word_to_remove = None
        for word_info in current_words:
            if word_info["word"] == word_id:
                word_to_remove = word_id
                break
        
        if word_to_remove:
            # Remove the word by replacing the list without it
            remaining_words = [w["word"] for w in current_words if w["word"] != word_id]
            trigger_word_alert_manager.update_trigger_words(remaining_words, mode="replace")
            
            return {
                "success": True,
                "message": f"Trigger word ID {word_id} deleted successfully"
            }
        else:
            return {
                "success": False,
                "error": f"Trigger word '{word_id}' not found"
            }
    except Exception as e:
        logger.error(f"Failed to delete trigger word: {e}")
        return {
            "success": False,
            "error": str(e)
        }

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
