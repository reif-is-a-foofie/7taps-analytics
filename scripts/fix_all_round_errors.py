#!/usr/bin/env python3
"""
Fix all ROUND function errors in SQLPad queries
"""
import requests
import json
import time

# SQLPad Configuration
SQLPAD_URL = "http://localhost:3000"
ADMIN_EMAIL = "admin@7taps.com"
ADMIN_PASSWORD = "admin123"

# All fixed queries with proper ROUND function usage
FIXED_QUERIES = [
    {
        "name": "01 - Lesson Completion Funnel",
        "query": """
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
        "name": "03 - Activity Type Distribution",
        "query": """
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
        "name": "04 - Question Response Analysis",
        "query": """
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
        "name": "06 - Response Quality Analysis",
        "query": """
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
        "name": "07 - Daily Engagement Trends",
        "query": """
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
        "name": "08 - User Retention Analysis",
        "query": """
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
        "name": "09 - Content Engagement by Type",
        "query": """
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
        "name": "11 - Lesson Drop-off Analysis",
        "query": """
        WITH lesson_progression AS (
            SELECT 
                ua.user_id,
                l.lesson_number,
                l.lesson_name,
                ROW_NUMBER() OVER (PARTITION BY ua.user_id ORDER BY l.lesson_number) as lesson_order,
                COUNT(*) as activities_in_lesson
            FROM user_activities ua
            JOIN lessons l ON ua.lesson_id = l.id
            GROUP BY ua.user_id, l.lesson_number, l.lesson_name
        )
        SELECT 
            lesson_number,
            lesson_name,
            COUNT(DISTINCT user_id) as users_reached,
            COUNT(DISTINCT CASE WHEN lesson_order = 1 THEN user_id END) as first_time_users,
            CASE 
                WHEN (SELECT COUNT(DISTINCT id) FROM users) > 0 THEN
                    ROUND(
                        (COUNT(DISTINCT user_id)::numeric / 
                         (SELECT COUNT(DISTINCT id) FROM users)::numeric) * 100, 1
                    )
                ELSE 0
            END as reach_percentage,
            AVG(activities_in_lesson) as avg_activities_per_user
        FROM lesson_progression
        GROUP BY lesson_number, lesson_name
        ORDER BY lesson_number;
        """
    },
    {
        "name": "13 - Cohort Performance Comparison",
        "query": """
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
        "name": "14 - Weekly Engagement Patterns",
        "query": """
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
        "name": "15 - Dashboard Summary Metrics",
        "query": """
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

def main():
    print("🔧 Fixing All ROUND Function Errors in SQLPad Queries")
    print("=" * 60)
    
    # Login
    print("🔐 Logging in...")
    session = requests.Session()
    response = session.post(
        f"{SQLPAD_URL}/api/signin",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code != 200:
        print("❌ Login failed")
        return
    
    print("✅ Login successful!")
    
    # Get queries
    print("📋 Getting queries...")
    response = session.get(f"{SQLPAD_URL}/api/queries")
    
    if response.status_code != 200:
        print("❌ Failed to get queries")
        return
    
    queries = response.json()
    print(f"Found {len(queries)} queries")
    
    # Update queries with fixes
    print("\n🔧 Updating queries with ROUND function fixes...")
    success_count = 0
    total_queries = len(FIXED_QUERIES)
    
    for i, fixed_query in enumerate(FIXED_QUERIES, 1):
        print(f"\n[{i}/{total_queries}] Fixing: {fixed_query['name']}")
        
        # Find matching query by name
        matching_query = None
        for existing_query in queries:
            if existing_query.get('name') == fixed_query['name']:
                matching_query = existing_query
                break
        
        if matching_query:
            print(f"  Found query ID: {matching_query['id']}")
            
            # Update the query
            response = session.put(
                f"{SQLPAD_URL}/api/queries/{matching_query['id']}",
                json={
                    "queryText": fixed_query["query"],
                    "name": fixed_query["name"]
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                print(f"  ✅ Updated successfully!")
                success_count += 1
            else:
                print(f"  ❌ Update failed: {response.status_code}")
        else:
            print(f"  ⚠️  Query not found")
    
    print(f"\n🎉 ROUND Function Fix Complete!")
    print(f"✅ Successfully updated: {success_count}/{total_queries} queries")
    print(f"📊 Access SQLPad: {SQLPAD_URL}")
    print(f"🔗 Login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print()
    print("💡 All queries now use proper numeric casting for ROUND functions")

if __name__ == "__main__":
    main()
