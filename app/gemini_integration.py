"""
Integration with Gemini AI for intelligent word suggestions and analysis
This extends your existing Gemini AI setup with smart filtering capabilities
"""

from typing import List, Dict, Any, Optional
import json
import requests
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

class GeminiAnalysisType(str, Enum):
    CONTENT_MODERATION = "content_moderation"
    WORD_SUGGESTION = "word_suggestion"
    PATTERN_ANALYSIS = "pattern_analysis"

@dataclass
class GeminiWordSuggestion:
    word: str
    category: str
    confidence: float
    reason: str
    context_examples: List[str]
    severity_recommendation: int

class GeminiSafetyIntegration:
    """
    Integrates with your existing Gemini AI to provide intelligent word suggestions
    and enhanced safety analysis
    """
    
    def __init__(self, api_key: str, base_url: str = None):
        self.api_key = api_key
        self.base_url = base_url or "https://generativelanguage.googleapis.com/v1beta"
        
    async def analyze_content_for_patterns(self, content_samples: List[str]) -> Dict[str, Any]:
        """
        Analyze content samples to identify patterns and suggest new filtered words
        This works with your existing Gemini AI to find emerging threats
        """
        prompt = f"""
        Analyze the following content samples for safety patterns and potential filtered words.
        Focus on identifying new threats, variations of existing words, and contextual issues.
        
        Content samples: {json.dumps(content_samples[:10])}  # Limit to prevent token overflow
        
        Return a JSON response with:
        1. suggested_words: List of new words to filter
        2. patterns: Emerging patterns or themes
        3. risk_assessment: Overall risk level
        4. recommendations: Specific actions to take
        
        Format as JSON only.
        """
        
        try:
            # This would integrate with your existing Gemini API calls
            # Replace with your actual Gemini API implementation
            response = await self._call_gemini_api(prompt, GeminiAnalysisType.PATTERN_ANALYSIS)
            return self._parse_gemini_response(response)
        except Exception as e:
            print(f"Error analyzing content patterns: {e}")
            return {"suggested_words": [], "patterns": [], "risk_assessment": "unknown"}
    
    async def suggest_words_from_flagged_content(self, flagged_content: List[Dict]) -> List[GeminiWordSuggestion]:
        """
        Use Gemini AI to suggest new filtered words based on previously flagged content
        This helps you stay ahead of emerging threats
        """
        if not flagged_content:
            return []
            
        prompt = f"""
        Analyze these flagged content examples and suggest new words to add to the filter list.
        Consider variations, synonyms, misspellings, and contextual threats.
        
        Flagged content examples: {json.dumps(flagged_content[:5])}
        
        For each suggested word, provide:
        - word: The actual word/phrase to filter
        - category: profanity, harassment, hate_speech, violence, self_harm, spam, inappropriate
        - confidence: 0.0-1.0 confidence score
        - reason: Why this word should be filtered
        - context_examples: Examples of how it appears in content
        - severity_recommendation: 1-5 severity level
        
        Return as JSON array.
        """
        
        try:
            response = await self._call_gemini_api(prompt, GeminiAnalysisType.WORD_SUGGESTION)
            suggestions_data = self._parse_gemini_response(response)
            
            suggestions = []
            for item in suggestions_data.get("suggested_words", []):
                suggestions.append(GeminiWordSuggestion(
                    word=item.get("word", ""),
                    category=item.get("category", "inappropriate"),
                    confidence=item.get("confidence", 0.5),
                    reason=item.get("reason", ""),
                    context_examples=item.get("context_examples", []),
                    severity_recommendation=item.get("severity_recommendation", 2)
                ))
            
            return suggestions
        except Exception as e:
            print(f"Error getting word suggestions: {e}")
            return []
    
    async def analyze_content_safety(self, content: str, existing_filters: List[str]) -> Dict[str, Any]:
        """
        Enhanced content analysis that works with your existing filters
        and provides Gemini-powered insights
        """
        prompt = f"""
        Analyze this content for safety issues, considering both the content itself
        and the existing filtered words list.
        
        Content: "{content}"
        Existing filtered words: {existing_filters[:20]}  # Limit for token efficiency
        
        Provide analysis including:
        1. safety_score: 0.0-1.0 (1.0 = completely safe)
        2. flagged_issues: List of specific issues found
        3. confidence: Analysis confidence level
        4. recommendations: Suggested actions
        5. new_threats: Any new threats not covered by existing filters
        
        Return as JSON.
        """
        
        try:
            response = await self._call_gemini_api(prompt, GeminiAnalysisType.CONTENT_MODERATION)
            analysis = self._parse_gemini_response(response)
            
            # Enhance with existing filter matching
            analysis["existing_filter_matches"] = self._check_existing_filters(content, existing_filters)
            
            return analysis
        except Exception as e:
            print(f"Error analyzing content safety: {e}")
            return {"safety_score": 0.5, "flagged_issues": [], "confidence": 0.0}
    
    async def get_contextual_word_suggestions(self, current_words: List[Dict]) -> List[GeminiWordSuggestion]:
        """
        Get contextual suggestions for expanding your current word list
        Based on your existing words, suggest related terms, variations, and gaps
        """
        if not current_words:
            return []
            
        prompt = f"""
        Based on this current list of filtered words, suggest additional words to improve coverage.
        Consider synonyms, variations, misspellings, and related terms.
        
        Current words: {json.dumps(current_words[:30])}  # Limit for token efficiency
        
        For each suggestion, provide:
        - word: The suggested word/phrase
        - category: Most appropriate category
        - confidence: How confident you are this should be filtered
        - reason: Why this word should be added
        - context_examples: How it might appear
        - severity_recommendation: Recommended severity (1-5)
        
        Focus on high-impact additions that will significantly improve safety coverage.
        Return as JSON array.
        """
        
        try:
            response = await self._call_gemini_api(prompt, GeminiAnalysisType.WORD_SUGGESTION)
            suggestions_data = self._parse_gemini_response(response)
            
            suggestions = []
            for item in suggestions_data.get("suggestions", []):
                suggestions.append(GeminiWordSuggestion(
                    word=item.get("word", ""),
                    category=item.get("category", "inappropriate"),
                    confidence=item.get("confidence", 0.5),
                    reason=item.get("reason", ""),
                    context_examples=item.get("context_examples", []),
                    severity_recommendation=item.get("severity_recommendation", 2)
                ))
            
            return suggestions
        except Exception as e:
            print(f"Error getting contextual suggestions: {e}")
            return []
    
    def _check_existing_filters(self, content: str, existing_filters: List[str]) -> List[str]:
        """Check content against existing filters"""
        content_lower = content.lower()
        matches = []
        
        for word in existing_filters:
            if word.lower() in content_lower:
                matches.append(word)
        
        return matches
    
    async def _call_gemini_api(self, prompt: str, analysis_type: GeminiAnalysisType) -> Dict[str, Any]:
        """
        Call Gemini AI API - integrate this with your existing Gemini setup
        Replace this with your actual Gemini API implementation
        """
        # This is a placeholder - integrate with your existing Gemini API calls
        # Your existing implementation likely looks something like:
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.1,  # Low temperature for consistent results
                "maxOutputTokens": 1000
            }
        }
        
        # Replace with your actual Gemini API endpoint
        url = f"{self.base_url}/models/gemini-pro:generateContent"
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Gemini API error: {e}")
            return {}
    
    def _parse_gemini_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Gemini API response"""
        try:
            if "candidates" in response and response["candidates"]:
                content = response["candidates"][0]["content"]["parts"][0]["text"]
                # Try to extract JSON from the response
                if content.startswith("{") or content.startswith("["):
                    return json.loads(content)
                else:
                    # If not pure JSON, try to extract JSON from the text
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group())
            
            return {"error": "Could not parse Gemini response"}
        except Exception as e:
            print(f"Error parsing Gemini response: {e}")
            return {"error": str(e)}

# Usage example for integrating with your existing system
async def enhance_safety_with_gemini():
    """
    Example of how to integrate this with your existing safety system
    """
    # Initialize with your existing Gemini API key
    gemini_integration = GeminiSafetyIntegration(
        api_key=os.getenv("GEMINI_API_KEY"),  # From environment variable
        base_url=os.getenv("GEMINI_BASE_URL")  # From environment variable
    )
    
    # Get intelligent word suggestions based on your current setup
    current_words = [
        {"word": "spam", "category": "spam", "severity": 2},
        {"word": "inappropriate", "category": "inappropriate", "severity": 3}
    ]
    
    suggestions = await gemini_integration.get_contextual_word_suggestions(current_words)
    
    return suggestions
