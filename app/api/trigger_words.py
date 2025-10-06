"""
Trigger word management API for safety monitoring.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json
import os

from app.logging_config import get_logger

logger = get_logger("trigger_words")
router = APIRouter()

# In-memory storage for trigger words (in production, use a database)
TRIGGER_WORDS_FILE = "data/trigger_words.json"

def load_trigger_words() -> List[Dict[str, Any]]:
    """Load trigger words from file."""
    try:
        if os.path.exists(TRIGGER_WORDS_FILE):
            with open(TRIGGER_WORDS_FILE, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Error loading trigger words: {e}")
        return []

def save_trigger_words(words: List[Dict[str, Any]]) -> None:
    """Save trigger words to file."""
    try:
        os.makedirs(os.path.dirname(TRIGGER_WORDS_FILE), exist_ok=True)
        with open(TRIGGER_WORDS_FILE, 'w') as f:
            json.dump(words, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving trigger words: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save trigger words: {str(e)}")

@router.get("/api/trigger-words")
async def get_trigger_words() -> Dict[str, Any]:
    """Get all trigger words."""
    try:
        words = load_trigger_words()
        return {
            "success": True,
            "trigger_words": words,
            "total_count": len(words),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting trigger words: {e}")
        return {
            "success": False,
            "error": str(e),
            "trigger_words": [],
            "total_count": 0
        }

@router.post("/api/trigger-words")
async def add_trigger_word(
    word: str = Query(..., description="Trigger word to add"),
    severity: str = Query("medium", description="Severity level: low, medium, high"),
    description: Optional[str] = Query(None, description="Description of the trigger word")
) -> Dict[str, Any]:
    """Add a new trigger word."""
    try:
        words = load_trigger_words()
        
        # Check if word already exists
        for existing_word in words:
            if existing_word["word"].lower() == word.lower():
                raise HTTPException(status_code=400, detail=f"Trigger word '{word}' already exists")
        
        new_word = {
            "id": len(words) + 1,
            "word": word,
            "severity": severity,
            "description": description or "",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active": True
        }
        
        words.append(new_word)
        save_trigger_words(words)
        
        logger.info(f"Added trigger word: {word} (severity: {severity})")
        
        return {
            "success": True,
            "message": f"Trigger word '{word}' added successfully",
            "trigger_word": new_word,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding trigger word: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add trigger word: {str(e)}")

@router.put("/api/trigger-words/{word_id}")
async def update_trigger_word(
    word_id: int,
    word: Optional[str] = Query(None, description="Updated trigger word"),
    severity: Optional[str] = Query(None, description="Updated severity level"),
    description: Optional[str] = Query(None, description="Updated description"),
    active: Optional[bool] = Query(None, description="Whether the trigger word is active")
) -> Dict[str, Any]:
    """Update an existing trigger word."""
    try:
        words = load_trigger_words()
        
        # Find the word to update
        word_to_update = None
        for i, w in enumerate(words):
            if w["id"] == word_id:
                word_to_update = i
                break
        
        if word_to_update is None:
            raise HTTPException(status_code=404, detail=f"Trigger word with ID {word_id} not found")
        
        # Update fields if provided
        if word is not None:
            words[word_to_update]["word"] = word
        if severity is not None:
            words[word_to_update]["severity"] = severity
        if description is not None:
            words[word_to_update]["description"] = description
        if active is not None:
            words[word_to_update]["active"] = active
        
        words[word_to_update]["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        save_trigger_words(words)
        
        logger.info(f"Updated trigger word ID {word_id}")
        
        return {
            "success": True,
            "message": f"Trigger word ID {word_id} updated successfully",
            "trigger_word": words[word_to_update],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating trigger word: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update trigger word: {str(e)}")

@router.delete("/api/trigger-words/{word_id}")
async def delete_trigger_word(word_id: int) -> Dict[str, Any]:
    """Delete a trigger word."""
    try:
        words = load_trigger_words()
        
        # Find and remove the word
        original_count = len(words)
        words = [w for w in words if w["id"] != word_id]
        
        if len(words) == original_count:
            raise HTTPException(status_code=404, detail=f"Trigger word with ID {word_id} not found")
        
        save_trigger_words(words)
        
        logger.info(f"Deleted trigger word ID {word_id}")
        
        return {
            "success": True,
            "message": f"Trigger word ID {word_id} deleted successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting trigger word: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete trigger word: {str(e)}")

@router.get("/api/trigger-words/alerts")
async def get_trigger_word_alerts() -> Dict[str, Any]:
    """Get recent trigger word alerts (placeholder for now)."""
    try:
        # This would integrate with the actual trigger word detection system
        # For now, return empty alerts
        return {
            "success": True,
            "alerts": [],
            "total_alerts": 0,
            "active_alerts": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting trigger word alerts: {e}")
        return {
            "success": False,
            "error": str(e),
            "alerts": []
        }
