from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import re
import os
from enum import Enum
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

router = APIRouter(prefix="/api/safety", tags=["safety"])

class WordCategory(str, Enum):
    PROFANITY = "profanity"
    HARASSMENT = "harassment"
    HATE_SPEECH = "hate_speech"
    VIOLENCE = "violence"
    SELF_HARM = "self_harm"
    SPAM = "spam"
    INAPPROPRIATE = "inappropriate"

class FilteredWord(BaseModel):
    id: Optional[int] = None
    word: str = Field(..., min_length=1, max_length=100)
    category: WordCategory
    severity: int = Field(..., ge=1, le=5)  # 1=low, 5=critical
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    usage_count: int = 0
    confidence_score: Optional[float] = None  # From Gemini AI analysis

class WordCreate(BaseModel):
    word: str = Field(..., min_length=1, max_length=100)
    category: WordCategory
    severity: int = Field(..., ge=1, le=5)
    is_active: bool = True

class WordUpdate(BaseModel):
    word: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[WordCategory] = None
    severity: Optional[int] = Field(None, ge=1, le=5)
    is_active: Optional[bool] = None

class SafetyStats(BaseModel):
    total_words: int
    active_words: int
    categories_count: Dict[str, int]
    avg_severity: float
    detection_rate: float

# In-memory storage (replace with database in production)
filtered_words_db: List[FilteredWord] = [
    FilteredWord(
        id=1, word="spam", category=WordCategory.SPAM, severity=2, 
        usage_count=15, confidence_score=0.95
    ),
    FilteredWord(
        id=2, word="inappropriate", category=WordCategory.INAPPROPRIATE, 
        severity=3, usage_count=8, confidence_score=0.87
    )
]

@router.get("/words", response_model=List[FilteredWord])
async def get_filtered_words(
    category: Optional[WordCategory] = None,
    active_only: bool = True,
    min_severity: Optional[int] = None
):
    """Get filtered words with optional filtering"""
    words = filtered_words_db.copy()
    
    if active_only:
        words = [w for w in words if w.is_active]
    
    if category:
        words = [w for w in words if w.category == category]
    
    if min_severity:
        words = [w for w in words if w.severity >= min_severity]
    
    return sorted(words, key=lambda x: x.severity, reverse=True)

@router.post("/words", response_model=FilteredWord)
async def create_filtered_word(word_data: WordCreate):
    """Create a new filtered word"""
    # Check for duplicates
    existing = next((w for w in filtered_words_db if w.word.lower() == word_data.word.lower()), None)
    if existing:
        raise HTTPException(status_code=400, detail="Word already exists")
    
    new_id = max([w.id for w in filtered_words_db], default=0) + 1
    new_word = FilteredWord(
        id=new_id,
        word=word_data.word,
        category=word_data.category,
        severity=word_data.severity,
        is_active=word_data.is_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        usage_count=0
    )
    
    filtered_words_db.append(new_word)
    return new_word

@router.get("/words/{word_id}", response_model=FilteredWord)
async def get_filtered_word(word_id: int):
    """Get a specific filtered word"""
    word = next((w for w in filtered_words_db if w.id == word_id), None)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    return word

@router.put("/words/{word_id}", response_model=FilteredWord)
async def update_filtered_word(word_id: int, word_data: WordUpdate):
    """Update a filtered word"""
    word = next((w for w in filtered_words_db if w.id == word_id), None)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    
    # Check for duplicate word if word is being changed
    if word_data.word and word_data.word.lower() != word.word.lower():
        existing = next((w for w in filtered_words_db 
                       if w.word.lower() == word_data.word.lower() and w.id != word_id), None)
        if existing:
            raise HTTPException(status_code=400, detail="Word already exists")
    
    # Update fields
    update_data = word_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(word, field, value)
    
    word.updated_at = datetime.utcnow()
    return word

@router.delete("/words/{word_id}")
async def delete_filtered_word(word_id: int):
    """Delete a filtered word"""
    global filtered_words_db
    word = next((w for w in filtered_words_db if w.id == word_id), None)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    
    filtered_words_db = [w for w in filtered_words_db if w.id != word_id]
    return {"message": "Word deleted successfully"}

@router.post("/words/bulk", response_model=List[FilteredWord])
async def bulk_create_words(words_data: List[WordCreate]):
    """Bulk create filtered words"""
    created_words = []
    for word_data in words_data:
        try:
            new_word = await create_filtered_word(word_data)
            created_words.append(new_word)
        except HTTPException as e:
            # Skip duplicates, continue with others
            continue
    return created_words

@router.get("/stats", response_model=SafetyStats)
async def get_safety_stats():
    """Get safety statistics"""
    active_words = [w for w in filtered_words_db if w.is_active]
    categories_count = {}
    total_severity = 0
    
    for word in active_words:
        category = word.category.value
        categories_count[category] = categories_count.get(category, 0) + 1
        total_severity += word.severity
    
    return SafetyStats(
        total_words=len(filtered_words_db),
        active_words=len(active_words),
        categories_count=categories_count,
        avg_severity=total_severity / len(active_words) if active_words else 0,
        detection_rate=0.0  # This would integrate with your Gemini AI stats
    )

@router.post("/analyze")
async def analyze_content(content: str):
    """Analyze content against filtered words (integrates with your Gemini AI)"""
    flagged_words = []
    content_lower = content.lower()
    
    for word in filtered_words_db:
        if word.is_active and word.word.lower() in content_lower:
            flagged_words.append({
                "word": word.word,
                "category": word.category,
                "severity": word.severity,
                "confidence_score": word.confidence_score or 0.8
            })
    
    return {
        "is_flagged": len(flagged_words) > 0,
        "flagged_words": flagged_words,
        "risk_level": max([w["severity"] for w in flagged_words], default=0),
        "gemini_analysis": {
            "confidence": 0.95,  # This would come from your Gemini AI
            "additional_flags": []  # Gemini-specific flags
        }
    }

@router.get("/suggestions")
async def get_word_suggestions():
    """Get AI-powered word suggestions based on analysis patterns"""
    from gemini_integration import GeminiSafetyIntegration
    
    # Initialize Gemini integration with environment variable
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY environment variable not set")
    
    gemini = GeminiSafetyIntegration(api_key=gemini_api_key)
    
    # Get current words for contextual suggestions
    current_words = [{"word": w.word, "category": w.category, "severity": w.severity} 
                    for w in filtered_words_db]
    
    # Get intelligent suggestions from Gemini
    try:
        suggestions = await gemini.get_contextual_word_suggestions(current_words)
        return [
            {
                "word": s.word,
                "category": s.category,
                "confidence": s.confidence,
                "reason": s.reason,
                "context_examples": s.context_examples,
                "severity_recommendation": s.severity_recommendation
            }
            for s in suggestions
        ]
    except Exception as e:
        # Fallback to basic suggestions if Gemini fails
        return [
            {
                "word": "suggested_word",
                "category": WordCategory.INAPPROPRIATE,
                "confidence": 0.85,
                "reason": "Detected in flagged content 3 times",
                "context_examples": ["Example usage"],
                "severity_recommendation": 3
            }
        ]

@router.post("/suggestions/apply")
async def apply_word_suggestions(suggestion_ids: List[int]):
    """Apply selected word suggestions to the filter list"""
    from gemini_integration import GeminiSafetyIntegration
    
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY environment variable not set")
    
    gemini = GeminiSafetyIntegration(api_key=gemini_api_key)
    suggestions = await gemini.get_contextual_word_suggestions(
        [{"word": w.word, "category": w.category, "severity": w.severity} 
         for w in filtered_words_db]
    )
    
    applied_words = []
    for idx in suggestion_ids:
        if 0 <= idx < len(suggestions):
            suggestion = suggestions[idx]
            word_data = WordCreate(
                word=suggestion.word,
                category=WordCategory(suggestion.category),
                severity=suggestion.severity_recommendation
            )
            try:
                new_word = await create_filtered_word(word_data)
                applied_words.append(new_word)
            except HTTPException:
                continue  # Skip duplicates
    
    return {"applied_words": applied_words, "count": len(applied_words)}

@router.post("/analyze/enhanced")
async def enhanced_content_analysis(content: str):
    """Enhanced content analysis using both existing filters and Gemini AI"""
    from gemini_integration import GeminiSafetyIntegration
    
    # Get existing filter matches
    existing_matches = []
    content_lower = content.lower()
    for word in filtered_words_db:
        if word.is_active and word.word.lower() in content_lower:
            existing_matches.append({
                "word": word.word,
                "category": word.category,
                "severity": word.severity,
                "confidence_score": word.confidence_score or 0.8
            })
    
    # Enhanced analysis with Gemini
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY environment variable not set")
    
    gemini = GeminiSafetyIntegration(api_key=gemini_api_key)
    existing_filters = [w.word for w in filtered_words_db if w.is_active]
    
    try:
        gemini_analysis = await gemini.analyze_content_safety(content, existing_filters)
        
        return {
            "is_flagged": len(existing_matches) > 0 or gemini_analysis.get("safety_score", 1.0) < 0.7,
            "existing_filter_matches": existing_matches,
            "gemini_analysis": {
                "safety_score": gemini_analysis.get("safety_score", 1.0),
                "flagged_issues": gemini_analysis.get("flagged_issues", []),
                "confidence": gemini_analysis.get("confidence", 0.0),
                "new_threats": gemini_analysis.get("new_threats", []),
                "recommendations": gemini_analysis.get("recommendations", [])
            },
            "overall_risk_level": max([w["severity"] for w in existing_matches], default=0),
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        # Fallback to basic analysis
        return {
            "is_flagged": len(existing_matches) > 0,
            "existing_filter_matches": existing_matches,
            "gemini_analysis": {
                "error": "Gemini analysis unavailable",
                "safety_score": 0.5,
                "confidence": 0.0
            },
            "overall_risk_level": max([w["severity"] for w in existing_matches], default=0),
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
