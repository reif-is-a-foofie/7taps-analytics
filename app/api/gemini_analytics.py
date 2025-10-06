"""
Gemini AI Analytics for 7taps Learning Data

This module provides AI-powered analysis of learning patterns using Google's Gemini API.
Perfect for analyzing xAPI statements, learning progress, and generating insights.
"""

import os
import json
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("gemini_analytics")


class GeminiAnalysisRequest(BaseModel):
    """Request model for Gemini analysis."""
    analysis_type: str  # "learning_patterns", "engagement_insights", "progress_analysis"
    data_context: Dict[str, Any]
    specific_questions: Optional[List[str]] = None


class GeminiInsightResponse(BaseModel):
    """Response model for Gemini insights."""
    insights: List[str]
    recommendations: List[str]
    confidence_score: float
    analysis_metadata: Dict[str, Any]


async def call_gemini_api(prompt: str, context_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Call Google Gemini API for learning analytics.
    
    Args:
        prompt: The analysis prompt for Gemini
        context_data: Additional context about the learning data
        
    Returns:
        Gemini API response with insights
    """
    try:
        import google.generativeai as genai
        
        # Configure Gemini API
        if not settings.GOOGLE_AI_API_KEY:
            raise HTTPException(
                status_code=500,
                detail="Google AI API key not configured. Set GOOGLE_AI_API_KEY environment variable."
            )
        
        genai.configure(api_key=settings.GOOGLE_AI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        
        # Build enhanced prompt with context
        enhanced_prompt = f"""
        You are an expert learning analytics AI analyzing 7taps digital wellness course data.
        
        CONTEXT: {json.dumps(context_data or {}, indent=2)}
        
        ANALYSIS REQUEST: {prompt}
        
        Please provide:
        1. Key insights about learning patterns
        2. Actionable recommendations for course improvement
        3. Confidence level (0.0-1.0) in your analysis
        4. Specific metrics or patterns you identified
        
        Format your response as JSON with keys: insights, recommendations, confidence_score, analysis_metadata
        """
        
        response = model.generate_content(enhanced_prompt)
        
        # Parse JSON response
        try:
            result = json.loads(response.text)
        except json.JSONDecodeError:
            # Fallback if Gemini doesn't return valid JSON
            result = {
                "insights": [response.text],
                "recommendations": ["Review the analysis manually"],
                "confidence_score": 0.7,
                "analysis_metadata": {"raw_response": response.text}
            }
        
        return result
        
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Google Generative AI library not installed. Run: pip install google-generativeai"
        )
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Gemini analysis failed: {str(e)}"
        )


async def get_learning_data_context(days: int = 7) -> Dict[str, Any]:
    """
    Get recent learning data context for Gemini analysis.
    
    Args:
        days: Number of days of data to include
        
    Returns:
        Context data about recent learning activity
    """
    try:
        from app.config.gcp_config import gcp_config
        from google.cloud import bigquery
        
        client = gcp_config.bigquery_client
        dataset_id = f"{gcp_config.project_id}.{gcp_config.bigquery_dataset}"
        
        # Get recent learning activity summary
        query = f"""
        SELECT 
            COUNT(*) as total_statements,
            COUNT(DISTINCT actor_name) as unique_learners,
            COUNTIF(verb_display LIKE '%completed%') as completion_statements,
            COUNTIF(result_success = true) as successful_activities,
            COUNTIF(result_success = false) as failed_activities,
            AVG(result_score_scaled) as avg_score,
            object_name,
            verb_display
        FROM `{dataset_id}.raw_xapi_statements`
        WHERE DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
        GROUP BY object_name, verb_display
        ORDER BY total_statements DESC
        LIMIT 20
        """
        
        query_job = client.query(query)
        results = query_job.result()
        
        learning_data = []
        total_stats = {
            "total_statements": 0,
            "unique_learners": 0,
            "completion_statements": 0,
            "successful_activities": 0,
            "failed_activities": 0,
            "avg_score": 0
        }
        
        for row in results:
            learning_data.append({
                "lesson": row.object_name,
                "activity_type": row.verb_display,
                "count": row.total_statements,
                "unique_learners": row.unique_learners,
                "completions": row.completion_statements,
                "success_rate": row.successful_activities / max(row.total_statements, 1),
                "avg_score": row.avg_score
            })
            
            total_stats["total_statements"] += row.total_statements
            total_stats["unique_learners"] = max(total_stats["unique_learners"], row.unique_learners)
            total_stats["completion_statements"] += row.completion_statements
            total_stats["successful_activities"] += row.successful_activities
            total_stats["failed_activities"] += row.failed_activities
        
        return {
            "period_days": days,
            "total_stats": total_stats,
            "lesson_activity": learning_data,
            "course_context": {
                "course_name": "7taps Digital Wellness",
                "lessons": [
                    "Digital Wellness Foundations",
                    "Screen Habits Awareness", 
                    "Device Relationship",
                    "Productivity Focus",
                    "Connection Balance"
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get learning data context: {e}")
        return {"error": str(e)}


@router.post("/api/gemini/analyze-learning-patterns")
async def analyze_learning_patterns(request: GeminiAnalysisRequest) -> GeminiInsightResponse:
    """
    Analyze learning patterns using Gemini AI.
    
    Perfect for understanding:
    - Learning engagement trends
    - Drop-off points in lessons
    - Success/failure patterns
    - Learner behavior insights
    """
    try:
        # Get recent learning data context
        data_context = await get_learning_data_context(days=7)
        
        # Build analysis prompt based on type
        if request.analysis_type == "learning_patterns":
            prompt = """
            Analyze these learning patterns and identify:
            1. Which lessons have the highest/lowest completion rates and why
            2. Common drop-off points or difficulty spikes
            3. Learner engagement patterns across different activities
            4. Correlations between lesson order and success rates
            """
        elif request.analysis_type == "engagement_insights":
            prompt = """
            Analyze learner engagement and provide insights on:
            1. Peak learning times and patterns
            2. Activity types that drive the most engagement
            3. Signs of learner motivation vs. disengagement
            4. Recommendations for improving course flow
            """
        elif request.analysis_type == "progress_analysis":
            prompt = """
            Analyze learning progress and success metrics:
            1. Overall course completion trends
            2. Success rate patterns across different lesson types
            3. Score distribution and learning effectiveness
            4. Predictions about learner outcomes
            """
        else:
            prompt = request.analysis_type
        
        # Add specific questions if provided
        if request.specific_questions:
            prompt += f"\n\nSpecific questions to address:\n" + "\n".join(f"- {q}" for q in request.specific_questions)
        
        # Call Gemini API
        result = await call_gemini_api(prompt, data_context)
        
        return GeminiInsightResponse(
            insights=result.get("insights", []),
            recommendations=result.get("recommendations", []),
            confidence_score=result.get("confidence_score", 0.7),
            analysis_metadata=result.get("analysis_metadata", {})
        )
        
    except Exception as e:
        logger.error(f"Learning pattern analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@router.get("/api/gemini/quick-insights")
async def get_quick_insights(days: int = 7) -> Dict[str, Any]:
    """
    Get quick AI insights about recent learning activity.
    
    Perfect for daily standups or quick course health checks.
    """
    try:
        data_context = await get_learning_data_context(days)
        
        prompt = f"""
        Provide a concise analysis of the last {days} days of learning activity.
        Focus on:
        1. Top 3 key insights about learner behavior
        2. Any concerning trends or patterns
        3. One actionable recommendation for the course team
        
        Keep it brief and actionable for a daily standup meeting.
        """
        
        result = await call_gemini_api(prompt, data_context)
        
        return {
            "period_days": days,
            "insights": result.get("insights", []),
            "recommendations": result.get("recommendations", []),
            "confidence_score": result.get("confidence_score", 0.7),
            "data_summary": data_context.get("total_stats", {}),
            "timestamp": data_context.get("timestamp")
        }
        
    except Exception as e:
        logger.error(f"Quick insights failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Quick insights failed: {str(e)}"
        )


@router.get("/api/gemini/status")
async def get_gemini_status() -> Dict[str, Any]:
    """Check Gemini API configuration and connectivity."""
    try:
        api_key_configured = bool(settings.GOOGLE_AI_API_KEY)
        
        if not api_key_configured:
            return {
                "status": "not_configured",
                "message": "Set GOOGLE_AI_API_KEY environment variable to enable Gemini analytics",
                "setup_required": True
            }
        
        # Test API connectivity
        test_result = await call_gemini_api(
            "Test connectivity. Respond with: 'Gemini API is working'",
            {"test": True}
        )
        
        return {
            "status": "configured",
            "message": "Gemini API is ready for learning analytics",
            "api_key_configured": True,
            "connectivity_test": "passed",
            "available_endpoints": [
                "/api/gemini/analyze-learning-patterns",
                "/api/gemini/quick-insights"
            ]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Gemini API error: {str(e)}",
            "api_key_configured": bool(settings.GOOGLE_AI_API_KEY),
            "setup_required": True
        }
