#!/usr/bin/env python3
"""
Test and fix ROUND function errors in SQLPad queries
"""
import psycopg2
import os
from psycopg2.extras import RealDictCursor

def get_db_connection():
    """Get database connection"""
    try:
        conn = psycopg2.connect(
            os.getenv("DATABASE_URL"),
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        print(f"Database connection failed: {str(e)}")
        return None

def test_query(query_name, sql):
    """Test a query and report any errors"""
    print(f"\n🧪 Testing: {query_name}")
    print("-" * 50)
    
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            results = cur.fetchall()
            print(f"✅ Query executed successfully!")
            print(f"📊 Results: {len(results)} rows")
            if results:
                print(f"📋 Sample row: {dict(results[0])}")
            return True
    except Exception as e:
        print(f"❌ Query failed: {str(e)}")
        return False
    finally:
        conn.close()

def main():
    """Test all queries and identify issues"""
    print("🔧 Testing SQLPad Queries for ROUND Function Errors")
    print("=" * 60)
    
    # Test queries with potential ROUND issues
    test_queries = [
        {
            "name": "Lesson Completion Funnel (Fixed)",
            "sql": """
            SELECT 
                l.lesson_number,
                l.lesson_name,
                COUNT(DISTINCT ua.user_id) as users_started,
                COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END) as users_completed,
                CASE 
                    WHEN COUNT(DISTINCT ua.user_id) > 0 THEN 
                        ROUND(
                            (COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END)::numeric / 
                             COUNT(DISTINCT ua.user_id)::numeric) * 100, 1
                        )
                    ELSE 0
                END as completion_rate,
                CASE 
                    WHEN (SELECT COUNT(DISTINCT id) FROM users) > 0 THEN
                        ROUND(
                            (COUNT(DISTINCT ua.user_id)::numeric / 
                             (SELECT COUNT(DISTINCT id) FROM users)::numeric) * 100, 1
                        )
                    ELSE 0
                END as engagement_rate
            FROM lessons l
            LEFT JOIN user_activities ua ON l.id = ua.lesson_id
            GROUP BY l.id, l.lesson_name, l.lesson_number
            ORDER BY l.lesson_number;
            """
        },
        {
            "name": "Activity Type Distribution (Fixed)",
            "sql": """
            SELECT 
                activity_type,
                COUNT(*) as activity_count,
                COUNT(DISTINCT user_id) as unique_users,
                CASE 
                    WHEN (SELECT COUNT(*) FROM user_activities) > 0 THEN
                        ROUND(
                            (COUNT(*)::numeric / (SELECT COUNT(*) FROM user_activities)::numeric) * 100, 1
                        )
                    ELSE 0
                END as percentage_of_total
            FROM user_activities 
            GROUP BY activity_type
            ORDER BY activity_count DESC;
            """
        },
        {
            "name": "Question Response Analysis (Fixed)",
            "sql": """
            SELECT 
                q.question_text,
                q.question_type,
                l.lesson_name,
                COUNT(ur.id) as response_count,
                COUNT(DISTINCT ur.user_id) as unique_respondents,
                AVG(ur.score_scaled) as avg_score,
                CASE 
                    WHEN (SELECT COUNT(DISTINCT id) FROM users) > 0 THEN
                        ROUND(
                            (COUNT(ur.id)::numeric / (SELECT COUNT(DISTINCT id) FROM users)::numeric) * 100, 1
                        )
                    ELSE 0
                END as response_rate
            FROM questions q
            JOIN lessons l ON q.lesson_id = l.id
            LEFT JOIN user_responses ur ON q.id = ur.question_id
            GROUP BY q.id, q.question_text, q.question_type, l.lesson_name
            ORDER BY response_count DESC
            LIMIT 15;
            """
        },
        {
            "name": "Response Quality Analysis (Fixed)",
            "sql": """
            SELECT 
                CASE 
                    WHEN score_scaled >= 0.8 THEN 'Excellent (80-100%)'
                    WHEN score_scaled >= 0.6 THEN 'Good (60-79%)'
                    WHEN score_scaled >= 0.4 THEN 'Fair (40-59%)'
                    WHEN score_scaled >= 0.2 THEN 'Poor (20-39%)'
                    WHEN score_scaled >= 0 THEN 'Very Poor (0-19%)'
                    ELSE 'No Score'
                END as score_range,
                COUNT(*) as response_count,
                COUNT(DISTINCT user_id) as unique_users,
                CASE 
                    WHEN (SELECT COUNT(*) FROM user_responses WHERE score_scaled IS NOT NULL) > 0 THEN
                        ROUND(
                            (COUNT(*)::numeric / (SELECT COUNT(*) FROM user_responses WHERE score_scaled IS NOT NULL)::numeric) * 100, 1
                        )
                    ELSE 0
                END as percentage
            FROM user_responses 
            WHERE score_scaled IS NOT NULL
            GROUP BY score_range
            ORDER BY MIN(score_scaled);
            """
        },
        {
            "name": "Daily Engagement Trends (Fixed)",
            "sql": """
            SELECT 
                DATE(ua.timestamp) as activity_date,
                COUNT(*) as total_activities,
                COUNT(DISTINCT ua.user_id) as active_users,
                COUNT(DISTINCT ua.lesson_id) as lessons_accessed,
                CASE 
                    WHEN (SELECT COUNT(DISTINCT id) FROM users) > 0 THEN
                        ROUND(
                            (COUNT(DISTINCT ua.user_id)::numeric / (SELECT COUNT(DISTINCT id) FROM users)::numeric) * 100, 1
                        )
                    ELSE 0
                END as daily_engagement_rate
            FROM user_activities ua
            WHERE ua.timestamp >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY DATE(ua.timestamp)
            ORDER BY activity_date;
            """
        },
        {
            "name": "User Retention Analysis (Fixed)",
            "sql": """
            WITH user_activity_days AS (
                SELECT 
                    user_id,
                    COUNT(DISTINCT DATE(timestamp)) as active_days,
                    MIN(timestamp) as first_activity,
                    MAX(timestamp) as last_activity,
                    EXTRACT(DAYS FROM MAX(timestamp) - MIN(timestamp)) as days_span
                FROM user_activities
                GROUP BY user_id
            )
            SELECT 
                CASE 
                    WHEN active_days >= 7 THEN '7+ Days'
                    WHEN active_days >= 5 THEN '5-6 Days'
                    WHEN active_days >= 3 THEN '3-4 Days'
                    WHEN active_days >= 2 THEN '2 Days'
                    ELSE '1 Day'
                END as engagement_duration,
                COUNT(*) as user_count,
                CASE 
                    WHEN (SELECT COUNT(*) FROM user_activity_days) > 0 THEN
                        ROUND(
                            (COUNT(*)::numeric / (SELECT COUNT(*) FROM user_activity_days)::numeric) * 100, 1
                        )
                    ELSE 0
                END as percentage,
                AVG(active_days) as avg_active_days,
                AVG(days_span) as avg_days_span
            FROM user_activity_days
            GROUP BY engagement_duration
            ORDER BY MIN(active_days) DESC;
            """
        },
        {
            "name": "Content Engagement by Type (Fixed)",
            "sql": """
            SELECT 
                q.question_type,
                COUNT(ur.id) as total_responses,
                COUNT(DISTINCT ur.user_id) as unique_users,
                AVG(ur.score_scaled) as avg_score,
                AVG(ur.duration_seconds) as avg_duration_seconds,
                CASE 
                    WHEN (SELECT COUNT(*) FROM user_responses) > 0 THEN
                        ROUND(
                            (COUNT(ur.id)::numeric / (SELECT COUNT(*) FROM user_responses)::numeric) * 100, 1
                        )
                    ELSE 0
                END as response_percentage
            FROM questions q
            LEFT JOIN user_responses ur ON q.id = ur.question_id
            GROUP BY q.question_type
            ORDER BY total_responses DESC;
            """
        },
        {
            "name": "Cohort Performance Comparison (Fixed)",
            "sql": """
            SELECT 
                COALESCE(u.cohort, 'No Cohort') as cohort,
                COUNT(DISTINCT u.id) as cohort_size,
                COUNT(ua.id) as total_activities,
                COUNT(DISTINCT ua.lesson_id) as lessons_accessed,
                COUNT(ur.id) as total_responses,
                AVG(ur.score_scaled) as avg_score,
                CASE 
                    WHEN (SELECT COUNT(*) FROM lessons) > 0 THEN
                        ROUND(
                            (COUNT(DISTINCT ua.lesson_id)::numeric / (SELECT COUNT(*) FROM lessons)::numeric), 1
                        )
                    ELSE 0
                END as avg_lessons_per_user,
                CASE 
                    WHEN COUNT(DISTINCT u.id) > 0 THEN
                        ROUND(
                            (COUNT(ua.id)::numeric / COUNT(DISTINCT u.id)::numeric), 1
                        )
                    ELSE 0
                END as avg_activities_per_user
            FROM users u
            LEFT JOIN user_activities ua ON u.id = ua.user_id
            LEFT JOIN user_responses ur ON u.id = ur.user_id
            GROUP BY u.cohort
            ORDER BY cohort_size DESC;
            """
        },
        {
            "name": "Weekly Engagement Patterns (Fixed)",
            "sql": """
            SELECT 
                EXTRACT(DOW FROM ua.timestamp) as day_of_week,
                CASE EXTRACT(DOW FROM ua.timestamp)
                    WHEN 0 THEN 'Sunday'
                    WHEN 1 THEN 'Monday'
                    WHEN 2 THEN 'Tuesday'
                    WHEN 3 THEN 'Wednesday'
                    WHEN 4 THEN 'Thursday'
                    WHEN 5 THEN 'Friday'
                    WHEN 6 THEN 'Saturday'
                END as day_name,
                COUNT(*) as total_activities,
                COUNT(DISTINCT ua.user_id) as active_users,
                COUNT(DISTINCT ua.lesson_id) as lessons_accessed,
                CASE 
                    WHEN (SELECT COUNT(*) FROM user_activities) > 0 THEN
                        ROUND(
                            (COUNT(*)::numeric / (SELECT COUNT(*) FROM user_activities)::numeric) * 100, 1
                        )
                    ELSE 0
                END as activity_percentage
            FROM user_activities ua
            GROUP BY EXTRACT(DOW FROM ua.timestamp)
            ORDER BY day_of_week;
            """
        },
        {
            "name": "Dashboard Summary Metrics (Fixed)",
            "sql": """
            SELECT 
                (SELECT COUNT(DISTINCT id) FROM users) as total_users,
                (SELECT COUNT(*) FROM user_activities) as total_activities,
                (SELECT COUNT(*) FROM user_responses) as total_responses,
                (SELECT COUNT(DISTINCT lesson_id) FROM user_activities) as active_lessons,
                (SELECT COUNT(*) FROM lessons) as total_lessons,
                (SELECT AVG(score_scaled) FROM user_responses WHERE score_scaled IS NOT NULL) as avg_score,
                (SELECT COUNT(DISTINCT user_id) FROM user_activities WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days') as active_users_7d,
                (SELECT COUNT(DISTINCT user_id) FROM user_activities WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days') as active_users_30d,
                CASE 
                    WHEN (SELECT COUNT(DISTINCT id) FROM users) > 0 THEN
                        ROUND(
                            ((SELECT COUNT(DISTINCT user_id) FROM user_activities WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days')::numeric / 
                             (SELECT COUNT(DISTINCT id) FROM users)::numeric) * 100, 1
                        )
                    ELSE 0
                END as weekly_engagement_rate;
            """
        }
    ]
    
    success_count = 0
    total_queries = len(test_queries)
    
    for query in test_queries:
        if test_query(query["name"], query["sql"]):
            success_count += 1
    
    print(f"\n🎯 Test Results: {success_count}/{total_queries} queries passed")
    
    if success_count == total_queries:
        print("✅ All queries are working correctly!")
        print("🚀 Ready to update SQLPad with fixed queries")
    else:
        print("❌ Some queries still have issues")
        print("🔧 Need to fix remaining problems")

if __name__ == "__main__":
    main()
