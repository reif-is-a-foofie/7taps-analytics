"""
Daily Course Analytics Dashboard UI.

Provides automated daily stats for course management team to support
the 7pm progress email workflow discussed in the data call.
"""

from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, List, Optional
import httpx
import json
import csv
import io
from datetime import datetime, timezone, date, timedelta
import os

from app.logging_config import get_logger
from app.api.bigquery_analytics import execute_bigquery_query

router = APIRouter()
logger = get_logger("daily_analytics")
templates = Jinja2Templates(directory="app/templates")


class DailyAnalyticsManager:
    """Manager for daily course analytics and progress tracking."""

    def __init__(self):
        api_base_url = os.getenv("API_BASE_URL", "")
        if api_base_url:
            self.api_base = api_base_url.rstrip("/") + "/api"
        else:
            # Use proper base URL for environment
            if os.getenv("ENVIRONMENT") == "development":
                self.api_base = "http://localhost:8000/api"
            else:
                self.api_base = "https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app/api"

    def _get_lesson_mapping(self) -> Dict[str, Dict[str, str]]:
        """Get lesson mapping for email templates."""
        return {
            "1": {
                "title": "You're Here: Start Strong",
                "quote": "Change starts with small, intentional steps — and you've already taken the first one by showing up.",
                "crazy_stat": "Your group spends 56+ hours a week on screens — more than sleeping.",
                "next_lesson": "Where Is Your Attention Going?"
            },
            "2": {
                "title": "Where Is Your Attention Going?",
                "quote": "What you pay attention to grows — so if you give most of it to your phone, that's what will dominate your day.",
                "crazy_stat": "One day, your group picked up phones 176 times — that's 3+ times every 10 minutes.",
                "next_lesson": "Own Your Mindset, Own Your Life"
            },
            "3": {
                "title": "Own Your Mindset, Own Your Life",
                "quote": "Your thoughts drive your actions, and your actions create your outcomes.",
                "crazy_stat": "7 out of 10 in your group say mental habits, not grades, are their top goal this semester.",
                "next_lesson": "Future-Proof Your Health"
            },
            "4": {
                "title": "Future-Proof Your Health",
                "quote": "The habits you practice now are the foundation for your future health and happiness.",
                "crazy_stat": "Your group's screen time adds up to 50+ full days every year.",
                "next_lesson": "Reclaim Your Rest"
            },
            "5": {
                "title": "Reclaim Your Rest",
                "quote": "Your phone can wait — your sleep cannot.",
                "crazy_stat": "81% of your group's heaviest phone use happens in the hour before bed.",
                "next_lesson": "Focus = Superpower"
            },
            "6": {
                "title": "Focus = Superpower",
                "quote": "Every distraction steals a piece of your focus, and with it, a piece of your potential.",
                "crazy_stat": "Before 10 a.m., your group checks phones more than some do all day.",
                "next_lesson": "Social Media + You"
            },
            "7": {
                "title": "Social Media + You",
                "quote": "Social media is a tool — it's up to you whether it works for you or against you.",
                "crazy_stat": "99% in your group say social scrolling has cost them sleep.",
                "next_lesson": "Less Stress. More Calm"
            },
            "8": {
                "title": "Less Stress. More Calm",
                "quote": "Calm is not something you find — it's something you create with your choices.",
                "crazy_stat": "Taking a phone break works for 2 out of 3 in your group almost every time.",
                "next_lesson": "Boost IRL Connection"
            },
            "9": {
                "title": "Boost IRL Connection",
                "quote": "Real connection happens in person, not through a screen.",
                "crazy_stat": "Your group spends more weekly hours on screens than face-to-face.",
                "next_lesson": "Celebrate Your Wins"
            },
            "10": {
                "title": "Celebrate Your Wins",
                "quote": "Noticing your progress is how you lock in your gains and keep moving forward.",
                "crazy_stat": "In two weeks, your group cut daily phone pickups by double digits.",
                "next_lesson": None
            }
        }

    def _get_available_groups(self) -> Dict[str, Any]:
        """Get available groups from the cohort mapping."""
        try:
            import json
            from pathlib import Path
            
            mapping_file = Path("reports/smart_cohort_mapping.json")
            if not mapping_file.exists():
                return {"groups": [], "error": "No group mapping found"}
            
            with open(mapping_file, 'r', encoding='utf-8') as f:
                cohort_data = json.load(f)
            
            groups = []
            for group_name, group_info in cohort_data.items():
                user_count = len(group_info.get("users", []))
                groups.append({
                    "name": group_name,
                    "user_count": user_count,
                    "display_name": f"{group_name} ({user_count} learners)"
                })
            
            # Add "Unmapped Users" option for users not yet assigned to groups
            groups.append({
                "name": "Unmapped Users",
                "user_count": 0,  # Will be calculated dynamically
                "display_name": "Unmapped Users (users not yet assigned to groups)"
            })
            
            return {"groups": groups, "success": True}
            
        except Exception as e:
            logger.error(f"Error getting available groups: {e}")
            return {"groups": [], "error": str(e)}

    def _get_user_group_mapping(self) -> Dict[str, str]:
        """Get mapping of users to groups from the cohort mapping file."""
        try:
            import json
            from pathlib import Path
            
            mapping_file = Path("reports/smart_cohort_mapping.json")
            if not mapping_file.exists():
                return {}
            
            with open(mapping_file, 'r', encoding='utf-8') as f:
                cohort_data = json.load(f)
            
            user_to_group = {}
            for group_name, group_info in cohort_data.items():
                for user in group_info.get("users", []):
                    user_name = user.get("name", "")
                    if user_name:
                        user_to_group[user_name] = group_name
            
            return user_to_group
            
        except Exception as e:
            logger.error(f"Error getting user group mapping: {e}")
            return {}

    def _get_lesson_response_data(self, target_date: str, group: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed lesson and response data for email templates."""
        try:
            # Filter by 7taps platform
            platform_filter = "AND context_platform = '7taps'"
            
            # Get user to group mapping
            user_group_mapping = self._get_user_group_mapping()
            
            query = f"""
            WITH lesson_responses AS (
                SELECT 
                    actor_id,
                    actor_name,
                    context_platform,
                    object_name as lesson_name,
                    verb_display,
                    result_response,
                    result_success,
                    result_completion,
                    timestamp,
                    statement_id
                FROM taps_data.statements 
                WHERE DATE(timestamp) = '{target_date}'
                {platform_filter}
                AND verb_display IN ('completed', 'answered')
                ORDER BY actor_id, lesson_name, timestamp
            )
            SELECT 
                actor_id,
                actor_name,
                context_platform,
                lesson_name,
                verb_display,
                result_response,
                result_success,
                result_completion,
                timestamp,
                statement_id
            FROM lesson_responses
            ORDER BY actor_id, lesson_name, timestamp
            """
            
            result = execute_bigquery_query(query)
            
            if result["success"]:
                responses = result["data"]["rows"]
                
                # Group by user and lesson, filtering by group if specified
                user_lessons = {}
                filtered_responses = []
                
                for response in responses:
                    user_name = response["actor_name"]
                    user_group = user_group_mapping.get(user_name, "Unmapped Users")
                    
                    # Filter by group if specified
                    if group and user_group != group:
                        continue
                    
                    filtered_responses.append(response)
                    user_id = response["actor_id"]
                    lesson = response["lesson_name"]
                    
                    if user_id not in user_lessons:
                        user_lessons[user_id] = {}
                    
                    if lesson not in user_lessons[user_id]:
                        user_lessons[user_id][lesson] = {
                            "user_name": response["actor_name"],
                            "group": user_group,  # Use mapped group instead of context_platform
                            "completed": False,
                            "responses": []
                        }
                    
                    if response["verb_display"] == "completed":
                        user_lessons[user_id][lesson]["completed"] = True
                    elif response["verb_display"] == "answered":
                        user_lessons[user_id][lesson]["responses"].append({
                            "response": response["result_response"],
                            "success": response["result_success"],
                            "timestamp": response["timestamp"]
                        })
                
                return {
                    "success": True,
                    "user_lessons": user_lessons,
                    "total_responses": len(filtered_responses),
                    "group_filter": group,
                    "user_group_mapping": user_group_mapping
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Failed to fetch response data"),
                    "user_lessons": {},
                    "total_responses": 0
                }
                
        except Exception as e:
            logger.error(f"Error getting lesson response data: {e}")
            return {
                "success": False,
                "error": str(e),
                "user_lessons": {},
                "total_responses": 0
            }

    def get_daily_completion_data(self, target_date: str, group: Optional[str] = None) -> Dict[str, Any]:
        """Get completion data for a specific date and group."""
        try:
            from app.utils.cohort_filtering import build_cohort_filter_sql
            
            # Filter by cohort if specified (group parameter is now cohort_id)
            cohort_filter = build_cohort_filter_sql(cohort_id=group) if group else ""
            
            # Also filter by 7taps platform
            platform_filter = "AND context_platform = '7taps'"
            
            # Get user to group mapping
            user_group_mapping = self._get_user_group_mapping()
            
            query = f"""
            WITH daily_activity AS (
                SELECT 
                    COALESCE(normalized_user_id, actor_id) as user_id,
                    actor_id,
                    actor_name,
                    verb_display,
                    object_name,
                    result_completion,
                    result_success,
                    result_score_scaled,
                    result_response,
                    context_platform,
                    timestamp,
                    DATE(timestamp) as activity_date
                FROM taps_data.statements 
                WHERE DATE(timestamp) = '{target_date}'
                {platform_filter}
                {cohort_filter}
            ),
            user_completions AS (
                SELECT 
                    user_id,
                    actor_id,
                    COALESCE(actor_name, actor_id) as user_name,
                    context_platform,
                    COUNT(*) as total_activities,
                    COUNT(CASE WHEN result_completion = true THEN 1 END) as completed_activities,
                    COUNT(CASE WHEN result_success = true THEN 1 END) as successful_activities,
                    AVG(result_score_scaled) as avg_score,
                    MAX(timestamp) as last_activity,
                    STRING_AGG(DISTINCT object_name, ', ') as activities_attempted
                FROM daily_activity
                GROUP BY user_id, actor_id, actor_name, context_platform
            )
            SELECT 
                user_id,
                actor_id,
                user_name,
                context_platform,
                total_activities,
                completed_activities,
                successful_activities,
                ROUND(avg_score, 2) as avg_score,
                last_activity,
                activities_attempted,
                CASE 
                    WHEN completed_activities >= total_activities THEN 'Completed'
                    WHEN completed_activities > 0 THEN 'Partial'
                    ELSE 'Not Started'
                END as completion_status
            FROM user_completions
            ORDER BY completed_activities DESC, total_activities DESC
            """
            
            result = execute_bigquery_query(query)
            
            if result["success"]:
                users = result["data"]["rows"]
                
                # Filter by group if specified
                if group:
                    filtered_users = []
                    for user in users:
                        user_name = user.get("user_name", "")
                        user_group = user_group_mapping.get(user_name, "Unmapped Users")
                        if user_group == group:
                            # Add group info to user data
                            user["group"] = user_group
                            filtered_users.append(user)
                    users = filtered_users
                else:
                    # Add group info to all users
                    for user in users:
                        user_name = user.get("user_name", "")
                        user_group = user_group_mapping.get(user_name, "Unmapped Users")
                        user["group"] = user_group
                
                return {
                    "success": True,
                    "users": users,
                    "total_users": len(users),
                    "query_time": result["execution_time"],
                    "group_filter": group
                }
            else:
                return {"success": False, "error": result["error"], "users": []}
                
        except Exception as e:
            logger.error(f"Failed to get daily completion data: {e}")
            return {"success": False, "error": str(e), "users": []}

    def get_daily_insights(self, target_date: str, cohort: Optional[str] = None) -> Dict[str, Any]:
        """Generate 5 actionable insights from the day's course feedback data for 7pm email strategy."""
        try:
            from app.utils.cohort_filtering import build_cohort_filter_sql
            
            cohort_filter = build_cohort_filter_sql(cohort_id=cohort) if cohort else ""
            
            insights_query = f"""
            WITH daily_feedback AS (
                SELECT 
                    COUNT(DISTINCT COALESCE(normalized_user_id, actor_id)) as unique_respondents,
                    COUNT(*) as total_responses,
                    COUNT(CASE WHEN result_response IS NOT NULL AND result_response != '' THEN 1 END) as text_responses,
                    COUNT(CASE WHEN result_success = true THEN 1 END) as positive_responses,
                    COUNT(CASE WHEN result_success = false THEN 1 END) as negative_responses,
                    AVG(result_score_scaled) as avg_sentiment_score,
                    STRING_AGG(DISTINCT object_name, ', ') as poll_questions
                FROM taps_data.statements 
                WHERE DATE(timestamp) = '{target_date}'
                {cohort_filter}
                AND (object_name LIKE '%poll%' OR object_name LIKE '%form%' OR object_name LIKE '%survey%' 
                     OR verb_display = 'answered' OR verb_display = 'responded')
            ),
            sentiment_analysis AS (
                SELECT 
                    CASE 
                        WHEN result_score_scaled >= 0.8 THEN 'very_positive'
                        WHEN result_score_scaled >= 0.6 THEN 'positive' 
                        WHEN result_score_scaled >= 0.4 THEN 'neutral'
                        WHEN result_score_scaled >= 0.2 THEN 'negative'
                        ELSE 'very_negative'
                    END as sentiment_category,
                    COUNT(*) as response_count,
                    STRING_AGG(DISTINCT result_response, ' | ') as sample_responses
                FROM taps_data.statements 
                WHERE DATE(timestamp) = '{target_date}'
                {cohort_filter}
                AND result_response IS NOT NULL 
                AND result_response != ''
                AND LENGTH(result_response) > 10
                GROUP BY sentiment_category
                ORDER BY response_count DESC
            ),
            top_concerns AS (
                SELECT 
                    result_response,
                    COUNT(*) as mention_count,
                    AVG(result_score_scaled) as avg_sentiment
                FROM taps_data.statements 
                WHERE DATE(timestamp) = '{target_date}'
                {cohort_filter}
                AND result_response IS NOT NULL 
                AND result_response != ''
                AND LENGTH(result_response) > 15
                AND (result_response ILIKE '%stress%' OR result_response ILIKE '%overwhelm%' 
                     OR result_response ILIKE '%difficult%' OR result_response ILIKE '%hard%'
                     OR result_response ILIKE '%confused%' OR result_response ILIKE '%help%')
                GROUP BY result_response
                ORDER BY mention_count DESC, avg_sentiment ASC
                LIMIT 3
            ),
            engagement_insights AS (
                SELECT 
                    COUNT(DISTINCT CASE WHEN result_completion = true THEN actor_id END) as engaged_learners,
                    COUNT(DISTINCT actor_id) as total_learners,
                    AVG(CASE WHEN result_completion = true THEN result_score_scaled END) as engaged_avg_score
                FROM taps_data.statements 
                WHERE DATE(timestamp) = '{target_date}'
                {cohort_filter}
            ),
            quote_worthy_responses AS (
                SELECT 
                    result_response,
                    result_score_scaled,
                    actor_id
                FROM taps_data.statements 
                WHERE DATE(timestamp) = '{target_date}'
                {cohort_filter}
                AND result_response IS NOT NULL 
                AND result_response != ''
                AND LENGTH(result_response) > 20
                AND result_score_scaled >= 0.7
                ORDER BY result_score_scaled DESC, LENGTH(result_response) DESC
                LIMIT 5
            )
            SELECT 
                df.*,
                ei.engaged_learners,
                ei.total_learners,
                ei.engaged_avg_score,
                (SELECT COUNT(*) FROM sentiment_analysis WHERE sentiment_category IN ('very_positive', 'positive')) as positive_sentiment_count,
                (SELECT COUNT(*) FROM sentiment_analysis WHERE sentiment_category IN ('negative', 'very_negative')) as negative_sentiment_count,
                (SELECT STRING_AGG(CONCAT(sentiment_category, ' (', response_count, ')'), ', ') FROM sentiment_analysis) as sentiment_breakdown,
                (SELECT COUNT(*) FROM top_concerns) as concern_count,
                (SELECT STRING_AGG(CONCAT(LEFT(result_response, 50), '...'), ' | ') FROM top_concerns LIMIT 2) as top_concerns_text,
                (SELECT COUNT(*) FROM quote_worthy_responses) as quote_count,
                (SELECT STRING_AGG(CONCAT('"', LEFT(result_response, 60), '..."'), ' | ') FROM quote_worthy_responses LIMIT 2) as sample_quotes
            FROM daily_feedback df
            CROSS JOIN engagement_insights ei
            """
            
            result = execute_bigquery_query(insights_query)
            
            if result["success"] and result["data"]["rows"]:
                stats = result["data"]["rows"][0]
                insights = []
                
                # 1. Student Sentiment & Energy Level
                positive_count = stats.get("positive_sentiment_count", 0)
                negative_count = stats.get("negative_sentiment_count", 0)
                total_responses = stats.get("total_responses", 1)
                
                if positive_count > negative_count * 2:
                    insights.append(f"🎉 HIGH ENERGY DAY: {positive_count} positive responses vs {negative_count} negative - perfect for celebrating wins and sharing success stories with leadership!")
                elif positive_count > negative_count:
                    insights.append(f"📈 STEADY MOMENTUM: {positive_count} positive responses vs {negative_count} negative - good foundation for encouraging messaging")
                elif negative_count > 0:
                    insights.append(f"⚠️ SUPPORT NEEDED: {negative_count} negative responses detected - focus on encouragement and addressing concerns in 7pm email")
                else:
                    insights.append(f"📊 MIXED FEEDBACK: Balanced responses - use neutral, supportive tone in tonight's communication")
                
                # 2. Content Impact & Student Insights
                text_responses = stats.get("text_responses", 0)
                if text_responses > 0:
                    avg_sentiment = stats.get("avg_sentiment_score", 0)
                    if avg_sentiment and avg_sentiment > 0.7:
                        insights.append(f"✨ CONTENT HIT: {text_responses} detailed responses with {round(avg_sentiment * 100, 1)}% average sentiment - students are deeply engaged and finding value!")
                    else:
                        insights.append(f"💭 STUDENT VOICE: {text_responses} detailed responses captured - rich feedback for understanding student experience and course effectiveness")
                else:
                    insights.append(f"📝 GATHERING INSIGHTS: Limited text responses today - consider encouraging more detailed feedback in future lessons")
                
                # 3. Student Concerns & Support Needs
                concern_count = stats.get("concern_count", 0)
                top_concerns_text = stats.get("top_concerns_text", "")
                if concern_count > 0:
                    insights.append(f"🚨 STUDENT CONCERNS: {concern_count} responses mention stress/difficulty - {top_concerns_text} - address these in 7pm email with support resources")
                else:
                    insights.append(f"👍 SMOOTH SAILING: No major concerns detected in feedback - students are navigating the content well")
                
                # 4. Quote-Worthy Testimonials for Leadership
                quote_count = stats.get("quote_count", 0)
                sample_quotes = stats.get("sample_quotes", "")
                if quote_count > 0:
                    insights.append(f"🌟 LEADERSHIP GOLD: {quote_count} quote-worthy responses found - {sample_quotes} - perfect for sharing with leadership and future marketing")
                else:
                    insights.append(f"💪 BUILDING MOMENTUM: Students are engaged but no standout quotes yet - focus on encouraging deeper reflection")
                
                # 5. 7pm Email Strategy Recommendation
                engaged_learners = stats.get("engaged_learners", 0)
                total_learners = stats.get("total_learners", 1)
                engagement_rate = round((engaged_learners / total_learners) * 100, 1)
                
                if engagement_rate >= 80:
                    insights.append(f"🚀 CELEBRATION EMAIL: {engagement_rate}% engagement rate ({engaged_learners}/{total_learners}) - lead with wins, share success stories, and build momentum!")
                elif engagement_rate >= 60:
                    insights.append(f"📧 ENCOURAGEMENT EMAIL: {engagement_rate}% engagement rate ({engaged_learners}/{total_learners}) - acknowledge progress, address any concerns, and motivate continued participation")
                else:
                    insights.append(f"💌 SUPPORT EMAIL: {engagement_rate}% engagement rate ({engaged_learners}/{total_learners}) - focus on support, resources, and removing barriers to participation")
                
                return {
                    "success": True,
                    "insights": insights[:5],  # Top 5 actionable insights for 7pm email
                    "raw_stats": stats
                }
            else:
                return {"success": False, "error": "No data found for insights", "insights": []}
                
        except Exception as e:
            logger.error(f"Failed to generate daily insights: {e}")
            return {"success": False, "error": str(e), "insights": []}

    def generate_daily_csv(self, target_date: str, cohort: Optional[str] = None) -> str:
        """Generate CSV data for daily progress report."""
        try:
            completion_data = self.get_daily_completion_data(target_date, cohort)
            
            if not completion_data["success"]:
                return ""
            
            # Create CSV content
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Headers
            writer.writerow([
                'User ID', 'User Name', 'Platform/Cohort', 'Completion Status',
                'Total Activities', 'Completed Activities', 'Success Rate',
                'Average Score', 'Last Activity', 'Activities Attempted'
            ])
            
            # Data rows
            for user in completion_data["users"]:
                writer.writerow([
                    user.get("actor_id", ""),
                    user.get("user_name", ""),
                    user.get("context_platform", ""),
                    user.get("completion_status", ""),
                    user.get("total_activities", 0),
                    user.get("completed_activities", 0),
                    f"{round((user.get('successful_activities', 0) / max(user.get('total_activities', 1), 1)) * 100, 1)}%",
                    f"{round((user.get('avg_score', 0) or 0) * 100, 1)}%" if user.get('avg_score') else "N/A",
                    user.get("last_activity", ""),
                    user.get("activities_attempted", "")
                ])
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to generate CSV: {e}")
            return ""


# Global manager instance
daily_manager = DailyAnalyticsManager()


@router.get("/daily-analytics", response_class=HTMLResponse)
async def daily_analytics_dashboard(
    request: Request,
    target_date: Optional[str] = Query(None, description="Target date for analytics (YYYY-MM-DD)"),
    cohort: Optional[str] = Query(None, description="Cohort/platform filter")
):
    """Serve the daily analytics dashboard for course management."""
    try:
        # Default to today if no date provided
        if not target_date:
            target_date = date.today().strftime("%Y-%m-%d")
        
        # Get analytics data
        analytics_manager = DailyAnalyticsManager()
        analytics_data = analytics_manager.get_daily_completion_data(target_date, cohort)
        
        # Get available groups
        available_groups = analytics_manager._get_available_groups()
        
        # Calculate metrics
        total_users = analytics_data.get("total_users", 0)
        all_users = analytics_data.get("users", [])
        
        # Separate completed vs incomplete users
        completed_users = [user for user in all_users if user.get("completion_status") == "Completed"]
        need_followup_users = [user for user in all_users if user.get("completion_status") != "Completed"]
        
        completed_count = len(completed_users)
        need_followup_count = len(need_followup_users)
        
        # Calculate completion rate
        completion_rate = "0%"
        if total_users > 0:
            completion_rate = f"{(completed_count / total_users * 100):.1f}%"
        
        context = {
            "request": request,
            "active_page": "daily_analytics",
            "title": "Daily Analytics",
            "target_date": target_date,
            "group": cohort,  # Changed from cohort to group
            "available_groups": available_groups.get("groups", []),
            "total_users": total_users,
            "completed_count": completed_count,
            "need_followup_count": need_followup_count,
            "completion_rate": completion_rate,
            "completed_users": completed_users,
            "need_followup_users": need_followup_users,
            "analytics_data": analytics_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        return templates.TemplateResponse("daily_analytics_modern.html", context)

    except Exception as e:
        logger.error(f"Failed to render daily analytics dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")


@router.get("/api/daily-analytics/email-data")
async def get_email_workflow_data(
    target_date: str = Query(..., description="Target date for analytics (YYYY-MM-DD)"),
    group: Optional[str] = Query(None, description="Group/cohort filter (e.g., 7taps)")
):
    """Get data specifically formatted for the 7pm email workflow."""
    try:
        analytics_manager = DailyAnalyticsManager()
        
        # Get lesson mapping
        lesson_mapping = analytics_manager._get_lesson_mapping()
        
        # Get detailed lesson and response data
        lesson_data = analytics_manager._get_lesson_response_data(target_date, group)
        
        # Get completion data
        completion_data = analytics_manager.get_daily_completion_data(target_date, group)
        
        # Structure data for email templates
        email_data = {
            "date": target_date,
            "group": group or "All Groups",
            "lesson_mapping": lesson_mapping,
            "completion_summary": {
                "total_users": completion_data.get("total_users", 0),
                "completed_users": completion_data.get("completed_users", []),
                "need_followup_users": completion_data.get("need_followup_users", []),
                "completion_rate": completion_data.get("completion_rate", "0%")
            },
            "lesson_data": lesson_data.get("user_lessons", {}),
            "email_ready": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return {
            "success": True,
            "data": email_data
        }
        
    except Exception as e:
        logger.error(f"Failed to get email workflow data: {e}")
        raise HTTPException(status_code=500, detail=f"Email data error: {str(e)}")


@router.get("/daily-analytics/download")
async def download_daily_analytics_csv(
    target_date: str = Query(..., description="Target date for analytics (YYYY-MM-DD)"),
    cohort: Optional[str] = Query(None, description="Cohort/platform filter"),
    format: str = Query("csv", description="Export format")
):
    """Download daily analytics data as CSV."""
    try:
        # Get analytics data
        analytics_manager = DailyAnalyticsManager()
        analytics_data = analytics_manager.get_daily_completion_data(target_date, cohort)
        
        if format.lower() == "csv":
            # Generate CSV content
            csv_content = analytics_manager.generate_daily_csv(target_date, cohort)
            
            if not csv_content:
                raise HTTPException(status_code=404, detail="No data found for the specified date/cohort")
            
            # Create filename
            cohort_suffix = f"_{cohort}" if cohort else ""
            filename = f"daily_progress_{target_date}{cohort_suffix}.csv"
            
            # Return as streaming response
            return StreamingResponse(
                io.StringIO(csv_content),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported format. Use 'csv'.")
            
    except Exception as e:
        logger.error(f"Failed to download daily analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Download error: {str(e)}")


@router.get("/api/daily-analytics/data")
async def get_daily_analytics_data(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    cohort: Optional[str] = Query(None, description="Filter by cohort/platform")
):
    """Get daily analytics data for the specified date and cohort."""
    try:
        completion_data = daily_manager.get_daily_completion_data(date, cohort)
        insights_data = daily_manager.get_daily_insights(date, cohort)
        
        # Separate completed vs incomplete users
        completed_users = []
        incomplete_users = []
        
        if completion_data["success"]:
            for user in completion_data["users"]:
                if user.get("completion_status") == "Completed":
                    completed_users.append(user)
                else:
                    incomplete_users.append(user)
        
        return {
            "success": True,
            "date": date,
            "cohort": cohort,
            "summary": {
                "total_users": completion_data.get("total_users", 0),
                "completed_users": len(completed_users),
                "incomplete_users": len(incomplete_users),
                "completion_rate": round((len(completed_users) / max(completion_data.get("total_users", 1), 1)) * 100, 1)
            },
            "completed_users": completed_users,
            "incomplete_users": incomplete_users,
            "insights": insights_data.get("insights", []),
            "query_time": completion_data.get("query_time", 0)
        }
        
    except Exception as e:
        logger.error(f"Failed to get daily analytics data: {e}")
        return {"success": False, "error": str(e)}


@router.get("/api/daily-analytics/csv")
async def download_daily_csv(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    cohort: Optional[str] = Query(None, description="Filter by cohort/platform")
):
    """Download CSV of daily progress data."""
    try:
        csv_content = daily_manager.generate_daily_csv(date, cohort)
        
        if not csv_content:
            raise HTTPException(status_code=404, detail="No data found for the specified date/cohort")
        
        # Create filename
        cohort_suffix = f"_{cohort}" if cohort else ""
        filename = f"daily_progress_{date}{cohort_suffix}.csv"
        
        # Return as streaming response
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Failed to generate CSV download: {e}")
        raise HTTPException(status_code=500, detail=f"CSV generation failed: {str(e)}")


@router.get("/api/daily-analytics/cohorts")
async def get_available_cohorts():
    """Get list of available cohorts/platforms for filtering."""
    try:
        from app.utils.cohort_filtering import get_all_available_cohorts
        
        cohorts = await get_all_available_cohorts()
        
        return {
            "success": True,
            "cohorts": cohorts
        }
            
    except Exception as e:
        logger.error(f"Failed to get cohorts: {e}")
        return {"success": False, "error": str(e), "cohorts": []}
