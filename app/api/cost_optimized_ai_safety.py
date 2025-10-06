"""
Cost-Optimized AI Safety System

Maximizes accuracy while minimizing Gemini API costs through:
1. Smart pre-filtering to avoid unnecessary API calls
2. Enhanced single prompt with all context
3. Local rule-based fallbacks
4. Caching and batching
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass

from app.config import settings
from app.logging_config import get_logger

logger = get_logger("cost_optimized_ai_safety")

@dataclass
class SafetyConfig:
    """Runtime configuration for safety analysis."""
    sensitivity_level: str = "medium"  # low, medium, high, critical
    enable_ai_analysis: bool = True
    cache_duration_hours: int = 24
    max_content_length: int = 500  # Skip AI for very long content
    confidence_threshold: float = 0.7

# Global configuration
SAFETY_CONFIG = SafetyConfig()

# Local rule-based patterns (no API cost)
CRITICAL_PATTERNS = [
    r"\b(kill|kill myself|suicide|end my life|end it all)\b",
    r"\b(hurt myself|self harm|self-harm)\b",
    r"\b(want to die|don't want to live)\b"
]

HIGH_PATTERNS = [
    r"\b(rape|raped|abuse|abused|violence|violent)\b",
    r"\b(hurt you|kill you|threaten)\b",
    r"\b(overdose|cut myself|bleeding)\b"
]

MEDIUM_PATTERNS = [
    r"\b(depressed|depression|hopeless|hopelessness)\b",
    r"\b(empty inside|nothing matters|pointless)\b",
    r"\b(isolated|alone|disconnected)\b"
]

# Common metaphors that should NOT be flagged (save API costs)
METAPHOR_PATTERNS = [
    r"killing me with (work|assignments|homework)",
    r"driving me crazy",
    r"stressed to death",
    r"frustrated I could scream",
    r"overwhelmed by everything",
    r"drowning in (work|responsibilities)",
    r"going insane from"
]

# Content cache to avoid duplicate API calls
CONTENT_CACHE = {}
CACHE_TIMESTAMP = {}

def is_metaphorical_expression(content: str) -> bool:
    """Check if content contains common metaphorical expressions."""
    content_lower = content.lower()
    for pattern in METAPHOR_PATTERNS:
        if re.search(pattern, content_lower):
            return True
    return False

def analyze_with_local_rules(content: str) -> Tuple[bool, str, float, List[str]]:
    """
    Fast local rule-based analysis (no API cost).
    Returns: (is_flagged, severity, confidence, reasons)
    """
    content_lower = content.lower()
    flagged_reasons = []
    
    # Check for metaphors first (avoid false positives)
    if is_metaphorical_expression(content):
        return False, "low", 0.9, ["Metaphorical expression detected"]
    
    # Check critical patterns
    for pattern in CRITICAL_PATTERNS:
        if re.search(pattern, content_lower):
            flagged_reasons.append("Critical safety concern")
            return True, "critical", 0.95, flagged_reasons
    
    # Check high patterns
    for pattern in HIGH_PATTERNS:
        if re.search(pattern, content_lower):
            flagged_reasons.append("High-risk content")
            return True, "high", 0.9, flagged_reasons
    
    # Check medium patterns
    for pattern in MEDIUM_PATTERNS:
        if re.search(pattern, content_lower):
            flagged_reasons.append("Mental health concern")
            return True, "medium", 0.8, flagged_reasons
    
    return False, "low", 0.95, []

def should_use_ai_analysis(content: str) -> bool:
    """Determine if content needs AI analysis (cost optimization)."""
    if not SAFETY_CONFIG.enable_ai_analysis:
        return False
    
    # Skip very long content
    if len(content) > SAFETY_CONFIG.max_content_length:
        logger.info(f"Skipping AI analysis for long content ({len(content)} chars)")
        return False
    
    # Check cache first
    content_hash = hash(content.lower().strip())
    if content_hash in CONTENT_CACHE:
        cache_age = datetime.now(timezone.utc) - CACHE_TIMESTAMP[content_hash]
        if cache_age.total_seconds() < SAFETY_CONFIG.cache_duration_hours * 3600:
            logger.info("Using cached AI analysis result")
            return False
    
    # Use local rules for obvious cases
    is_flagged, severity, confidence, _ = analyze_with_local_rules(content)
    
    # Only use AI for ambiguous cases or when local rules aren't confident
    if severity in ["critical", "high"]:
        # Local rules are confident for obvious threats
        return False
    
    if severity == "medium" and confidence > 0.8:
        # Local rules are confident for medium cases
        return False
    
    # Use AI for nuanced cases, low confidence, or unclear content
    return True

async def analyze_content_with_ai(content: str, context: str = "general") -> Dict[str, Any]:
    """Enhanced AI analysis with cost optimization."""
    try:
        import google.generativeai as genai
        
        if not settings.GOOGLE_AI_API_KEY:
            return _fallback_analysis(content)
        
        genai.configure(api_key=settings.GOOGLE_AI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Enhanced prompt with all context and examples
        prompt = f"""
        You are analyzing learner content from a digital wellness course. 
        Be precise and cost-conscious - only flag genuine concerns.
        
        CONTEXT: {context} (wellness/learning course)
        CONTENT: "{content}"
        
        ANALYSIS FRAMEWORK:
        
        1. IMMEDIATE DANGER (Critical - flag immediately):
           - Direct suicide threats: "kill myself", "end my life", "want to die"
           - Active self-harm: "hurt myself", "cut myself", "overdose"
           - Abuse disclosure: "raped", "abuse", "partner hits me"
        
        2. MENTAL HEALTH CONCERNS (Medium/High):
           - Severe depression: "empty inside", "nothing matters", "hopeless"
           - Isolation: "alone", "disconnected", "no one cares"
           - Escalating distress: patterns of worsening mental state
        
        3. NOT CONCERNING (Do not flag):
           - Learning struggles: "challenging", "difficult", "struggling with"
           - Normal emotions: "frustrated", "overwhelmed", "stressed"
           - Metaphors: "killing me with work", "driving me crazy"
           - Seeking help: "need support", "looking for guidance"
        
        SEVERITY SCALE:
        - critical: Immediate danger, direct threats, active self-harm
        - high: Serious mental health crisis, threats to others
        - medium: Depression signs, hopelessness, concerning patterns
        - low: General distress, mild concerns
        
        Respond with JSON only:
        {{
            "is_flagged": true/false,
            "severity": "low/medium/high/critical",
            "flagged_reasons": ["specific reason"],
            "confidence_score": 0.0-1.0,
            "suggested_actions": ["action if flagged"],
            "analysis_notes": "brief explanation"
        }}
        """
        
        response = model.generate_content(prompt)
        
        # Parse response
        try:
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            result = json.loads(response_text)
            
            # Cache the result
            content_hash = hash(content.lower().strip())
            CONTENT_CACHE[content_hash] = result
            CACHE_TIMESTAMP[content_hash] = datetime.now(timezone.utc)
            
            return result
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse AI response: {response.text}")
            return _fallback_analysis(content)
        
    except Exception as e:
        logger.error(f"AI analysis failed: {e}")
        return _fallback_analysis(content)

def _fallback_analysis(content: str) -> Dict[str, Any]:
    """Fallback analysis using local rules."""
    is_flagged, severity, confidence, reasons = analyze_with_local_rules(content)
    
    return {
        "is_flagged": is_flagged,
        "severity": severity,
        "flagged_reasons": reasons,
        "confidence_score": confidence,
        "suggested_actions": ["Manual review recommended"] if is_flagged else [],
        "analysis_notes": "Local rule-based analysis",
        "analysis_metadata": {
            "analysis_method": "local_rules",
            "ai_available": False
        }
    }

async def analyze_content_optimized(content: str, context: str = "general") -> Dict[str, Any]:
    """
    Cost-optimized content analysis.
    Uses local rules when possible, AI only when necessary.
    """
    logger.info(f"Analyzing content: {content[:50]}...")
    
    # Step 1: Check if we should use AI
    if should_use_ai_analysis(content):
        logger.info("Using AI analysis for nuanced content")
        result = await analyze_content_with_ai(content, context)
        result["analysis_metadata"] = {
            "analysis_method": "ai_enhanced",
            "cost_optimized": True,
            "ai_available": True
        }
    else:
        logger.info("Using local rule-based analysis (cost optimized)")
        result = _fallback_analysis(content)
        result["analysis_metadata"] = {
            "analysis_method": "local_rules",
            "cost_optimized": True,
            "ai_available": True  # Available but not used for cost savings
        }
    
    # Add processing metadata
    result["analysis_metadata"].update({
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "content_length": len(content),
        "sensitivity_level": SAFETY_CONFIG.sensitivity_level
    })
    
    return result

def update_safety_config(**kwargs) -> None:
    """Update safety configuration at runtime."""
    global SAFETY_CONFIG
    for key, value in kwargs.items():
        if hasattr(SAFETY_CONFIG, key):
            setattr(SAFETY_CONFIG, key, value)
            logger.info(f"Updated safety config: {key} = {value}")

def get_safety_config() -> Dict[str, Any]:
    """Get current safety configuration."""
    return {
        "sensitivity_level": SAFETY_CONFIG.sensitivity_level,
        "enable_ai_analysis": SAFETY_CONFIG.enable_ai_analysis,
        "cache_duration_hours": SAFETY_CONFIG.cache_duration_hours,
        "max_content_length": SAFETY_CONFIG.max_content_length,
        "confidence_threshold": SAFETY_CONFIG.confidence_threshold,
        "cache_size": len(CONTENT_CACHE)
    }

def clear_cache() -> None:
    """Clear the content analysis cache."""
    global CONTENT_CACHE, CACHE_TIMESTAMP
    CONTENT_CACHE.clear()
    CACHE_TIMESTAMP.clear()
    logger.info("Safety analysis cache cleared")
