"""
AI-Powered Flagged Content Detection using Gemini

Replaces hardcoded trigger words with intelligent content analysis.
Analyzes learner inputs for safety concerns, harmful content, and flagged language.
"""

import json
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("ai_flagged_content")


class ContentAnalysisRequest(BaseModel):
    """Request model for content analysis."""
    content: str
    context: Optional[str] = None  # "reflection", "response", "feedback", etc.
    user_id: Optional[str] = None


class FlaggedContentResponse(BaseModel):
    """Response model for flagged content analysis."""
    is_flagged: bool
    severity: str  # "low", "medium", "high", "critical"
    flagged_reasons: List[str]
    confidence_score: float
    suggested_actions: List[str]
    analysis_metadata: Dict[str, Any]


async def analyze_content_with_gemini(content: str, context: str = "general") -> Dict[str, Any]:
    """
    Use improved batch AI analysis for flagged language and safety concerns.
    
    Args:
        content: The text content to analyze
        context: Context of the content (reflection, response, etc.)
        
    Returns:
        Analysis results with flagged status and details
    """
    try:
        # Use batch processor which includes obvious flag detection
        from app.api.batch_ai_safety import batch_processor
        
        # Process through batch processor (checks obvious flags first, then AI)
        result = await batch_processor.process_content(
            content=content,
            context=context,
            statement_id="unknown",
            user_id="unknown"
        )
        
        # Convert batch processor result to expected format
        if result.get("status") == "flagged":
            return {
                "is_flagged": result.get("is_flagged", False),
                "severity": result.get("severity", "medium"),
                "flagged_reasons": result.get("flagged_reasons", []),
                "confidence_score": result.get("confidence_score", 0.0),
                "suggested_actions": result.get("suggested_actions", []),
                "analysis_metadata": result.get("analysis_metadata", {})
            }
        else:
            # Queued or not flagged
            return {
                "is_flagged": False,
                "severity": "low",
                "flagged_reasons": [],
                "confidence_score": 0.0,
                "suggested_actions": [],
                "analysis_metadata": result.get("analysis_metadata", {})
            }
        
    except Exception as e:
        logger.error(f"Batch processor analysis failed: {e}")
        # Fallback to keyword analysis
        return _fallback_keyword_analysis(content)


def _fallback_keyword_analysis(content: str) -> Dict[str, Any]:
    """
    Fallback keyword-based analysis when Gemini is not available.
    
    Uses the original hardcoded trigger words as backup.
    """
    # Original trigger words from trigger_word_alerts.py
    DEFAULT_TRIGGER_WORDS = [
        "suicide", "self harm", "self-harm", "kill myself", "hurting myself"
    ]
    
    content_lower = content.lower()
    flagged_reasons = []
    
    for word in DEFAULT_TRIGGER_WORDS:
        if word in content_lower:
            flagged_reasons.append(f"Contains trigger word: {word}")
    
    is_flagged = len(flagged_reasons) > 0
    
    return {
        "is_flagged": is_flagged,
        "severity": "high" if is_flagged else "low",
        "flagged_reasons": flagged_reasons,
        "confidence_score": 0.8 if is_flagged else 1.0,
        "suggested_actions": ["Manual review recommended"] if is_flagged else [],
        "analysis_metadata": {
            "analysis_method": "fallback_keywords",
            "gemini_available": False
        }
    }


async def analyze_xapi_statement_content(statement: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze xAPI statement content for flagged language.
    
    Args:
        statement: xAPI statement to analyze
        
    Returns:
        Analysis results with flagged status
    """
    try:
        # Extract text content from xAPI statement
        content_parts = []
        
        # Check result.response (common for reflection responses)
        result = statement.get("result", {})
        if result.get("response"):
            content_parts.append(f"Response: {result['response']}")
        
        # Check object definition name/description
        obj_def = statement.get("object", {}).get("definition", {})
        if obj_def.get("name", {}).get("en-US"):
            content_parts.append(f"Activity: {obj_def['name']['en-US']}")
        
        # Check extensions for additional text
        extensions = statement.get("result", {}).get("extensions", {})
        for ext_key, ext_value in extensions.items():
            if isinstance(ext_value, str) and len(ext_value) > 10:
                content_parts.append(f"Extension {ext_key}: {ext_value}")
        
        # Combine all content
        full_content = " | ".join(content_parts)
        
        # Extract just the response text for obvious flag detection (without prefixes)
        response_text = result.get("response", "") if result.get("response") else ""
        
        if not full_content.strip():
            return {
                "is_flagged": False,
                "severity": "low",
                "flagged_reasons": [],
                "confidence_score": 1.0,
                "suggested_actions": [],
                "analysis_metadata": {"no_text_content": True}
            }
        
        # Determine context
        verb_id = statement.get("verb", {}).get("id", "")
        if "responded" in verb_id or "answered" in verb_id:
            context = "response"
        elif "completed" in verb_id:
            context = "completion"
        else:
            context = "general"
        
        # Analyze with Gemini - use response_text for obvious flag detection, full_content for AI analysis
        # The batch processor will check obvious flags on the content we pass
        # So pass the raw response text (without "Response: " prefix) for better pattern matching
        analysis = await analyze_content_with_gemini(response_text if response_text else full_content, context)
        
        # Add statement metadata
        analysis["analysis_metadata"] = {
            **analysis.get("analysis_metadata", {}),
            "statement_id": statement.get("id"),
            "verb_id": verb_id,
            "actor_name": statement.get("actor", {}).get("name"),
            "timestamp": statement.get("timestamp"),
            "content_length": len(full_content)
        }
        
        return analysis
        
    except Exception as e:
        logger.error(f"Failed to analyze xAPI statement content: {e}")
        return {
            "is_flagged": False,
            "severity": "low",
            "flagged_reasons": ["Analysis failed"],
            "confidence_score": 0.0,
            "suggested_actions": ["Manual review recommended"],
            "analysis_metadata": {"error": str(e)}
        }


@router.post("/api/ai-content/analyze", response_model=FlaggedContentResponse)
async def analyze_content_for_flags(request: ContentAnalysisRequest) -> FlaggedContentResponse:
    """
    Analyze content for flagged language using AI.
    
    Replaces hardcoded trigger word matching with intelligent analysis.
    """
    try:
        analysis = await analyze_content_with_gemini(
            request.content, 
            request.context or "general"
        )
        
        return FlaggedContentResponse(
            is_flagged=analysis.get("is_flagged", False),
            severity=analysis.get("severity", "low"),
            flagged_reasons=analysis.get("flagged_reasons", []),
            confidence_score=analysis.get("confidence_score", 0.5),
            suggested_actions=analysis.get("suggested_actions", []),
            analysis_metadata={
                **analysis.get("analysis_metadata", {}),
                "user_id": request.user_id,
                "context": request.context,
                "analyzed_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Content analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Content analysis failed: {str(e)}"
        )


@router.post("/api/ai-content/analyze-xapi")
async def analyze_xapi_for_flags(statement: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze xAPI statement for flagged content.
    
    Drop-in replacement for trigger word detection in xAPI processing.
    """
    try:
        analysis = await analyze_xapi_statement_content(statement)
        
        # Add processing metadata
        analysis["processing_metadata"] = {
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "analysis_method": "gemini_ai",
            "statement_processed": True
        }
        
        return analysis
        
    except Exception as e:
        logger.error(f"xAPI content analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"xAPI analysis failed: {str(e)}"
        )


@router.get("/api/ai-content/status")
async def get_ai_content_status() -> Dict[str, Any]:
    """Check AI content analysis configuration and status."""
    try:
        api_key_configured = bool(settings.GOOGLE_AI_API_KEY)
        
        # Test with a safe example
        test_analysis = await analyze_content_with_gemini(
            "I'm feeling great about my progress!", 
            "test"
        )
        
        if not api_key_configured:
            return {
                "status": "fallback_mode",
                "message": "Using fallback keyword analysis. Set GOOGLE_AI_API_KEY for Gemini AI analysis",
                "setup_required": False,
                "replaces": "hardcoded trigger words",
                "current_method": "keyword_matching",
                "test_analysis": test_analysis
            }
        
        return {
            "status": "configured",
            "message": "AI content analysis is ready for flagged language detection",
            "api_key_configured": True,
            "current_method": "gemini_ai",
            "test_analysis": test_analysis,
            "available_endpoints": [
                "/api/ai-content/analyze",
                "/api/ai-content/analyze-xapi"
            ],
            "replaces": "hardcoded trigger words with intelligent analysis"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"AI content analysis error: {str(e)}",
            "api_key_configured": bool(settings.GOOGLE_AI_API_KEY),
            "setup_required": True
        }


# Integration helper for existing trigger word system
async def check_content_for_flags(content: str, context: str = "general") -> Tuple[bool, Dict[str, Any]]:
    """
    Helper function to check content for flags.
    
    Returns:
        Tuple of (is_flagged, analysis_details)
    """
    try:
        analysis = await analyze_content_with_gemini(content, context)
        is_flagged = analysis.get("is_flagged", False)
        return is_flagged, analysis
    except Exception as e:
        logger.error(f"Flag check failed: {e}")
        return False, {"error": str(e)}
