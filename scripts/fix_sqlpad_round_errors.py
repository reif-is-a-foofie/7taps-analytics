#!/usr/bin/env python3
"""
Fix ROUND function errors in SQLPad queries
"""
import requests
import json
import time

# SQLPad Configuration
SQLPAD_URL = "http://localhost:3000"
ADMIN_EMAIL = "admin@7taps.com"
ADMIN_PASSWORD = "admin123"

# Fixed queries with proper ROUND function usage
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
        "name": "02 - User Engagement Levels",
        "query": """
        SELECT 
            u.user_id,
            COUNT(ua.id) as total_activities,
            COUNT(DISTINCT ua.lesson_id) as lessons_accessed,
            COUNT(ur.id) as total_responses,
            AVG(ur.score_scaled) as avg_score,
            MIN(ua.timestamp) as first_activity,
            MAX(ua.timestamp) as last_activity,
            CASE 
                WHEN COUNT(ua.id) >= 50 THEN 'High Engagement'
                WHEN COUNT(ua.id) >= 20 THEN 'Medium Engagement'
                WHEN COUNT(ua.id) >= 5 THEN 'Low Engagement'
                ELSE 'Inactive'
            END as engagement_level
        FROM users u
        LEFT JOIN user_activities ua ON u.id = ua.user_id
        LEFT JOIN user_responses ur ON u.id = ur.user_id
        GROUP BY u.id, u.user_id
        ORDER BY total_activities DESC;
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
        "name": "05 - Learning Progression Timeline",
        "query": """
        WITH user_progress AS (
            SELECT 
                ua.user_id,
                l.lesson_number,
                l.lesson_name,
                MIN(ua.timestamp) as first_access,
                MAX(ua.timestamp) as last_access,
                COUNT(*) as activity_count,
                COUNT(DISTINCT ur.id) as response_count
            FROM user_activities ua
            JOIN lessons l ON ua.lesson_id = l.id
            LEFT JOIN user_responses ur ON ua.user_id = ur.user_id AND l.lesson_number = ur.lesson_number
            GROUP BY ua.user_id, l.lesson_number, l.lesson_name
        )
        SELECT 
            lesson_number,
            lesson_name,
            COUNT(DISTINCT user_id) as users_reached,
            AVG(activity_count) as avg_activities,
            AVG(response_count) as avg_responses,
            AVG(EXTRACT(EPOCH FROM (last_access - first_access))/3600) as avg_hours_spent
        FROM user_progress
        GROUP BY lesson_number, lesson_name
        ORDER BY lesson_number;
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
        "name": "10 - Top Performing Users",
        "query": """
        SELECT 
            u.user_id,
            COUNT(ua.id) as total_activities,
            COUNT(DISTINCT ua.lesson_id) as lessons_accessed,
            COUNT(ur.id) as total_responses,
            AVG(ur.score_scaled) as avg_score,
            MIN(ua.timestamp) as first_activity,
            MAX(ua.timestamp) as last_activity,
            EXTRACT(DAYS FROM MAX(ua.timestamp) - MIN(ua.timestamp)) as days_active
        FROM users u
        LEFT JOIN user_activities ua ON u.id = ua.user_id
        LEFT JOIN user_responses ur ON u.id = ur.user_id
        GROUP BY u.id, u.user_id
        HAVING COUNT(ua.id) >= 10
        ORDER BY total_activities DESC, avg_score DESC
        LIMIT 20;
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
        "name": "12 - Response Time Analysis",
        "query": """
        SELECT 
            q.question_type,
            l.lesson_name,
            COUNT(ur.id) as response_count,
            AVG(ur.duration_seconds) as avg_duration_seconds,
            MIN(ur.duration_seconds) as min_duration,
            MAX(ur.duration_seconds) as max_duration,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ur.duration_seconds) as median_duration
        FROM user_responses ur
        JOIN questions q ON ur.question_id = q.id
        JOIN lessons l ON q.lesson_id = l.id
        WHERE ur.duration_seconds IS NOT NULL AND ur.duration_seconds > 0
        GROUP BY q.question_type, l.lesson_name
        ORDER BY avg_duration_seconds DESC;
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

def login_to_sqlpad():
    """Login to SQLPad and get session"""
    print("🔐 Logging into SQLPad...")
    
    login_data = {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }
    
    session = requests.Session()
    response = session.post(
        f"{SQLPAD_URL}/api/signin",
        json=login_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Login response status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Login successful!")
        return session
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def get_queries(session):
    """Get all existing queries"""
    print("📋 Getting existing queries...")
    response = session.get(f"{SQLPAD_URL}/api/queries")
    print(f"Get queries response status: {response.status_code}")
    
    if response.status_code == 200:
        queries = response.json()
        print(f"Found {len(queries)} queries")
        return queries
    else:
        print(f"❌ Failed to get queries: {response.status_code}")
        print(f"Response: {response.text}")
        return []

def update_query(session, query_id, query_data):
    """Update an existing query"""
    print(f"🔧 Updating query {query_id}...")
    try:
        response = session.put(
            f"{SQLPAD_URL}/api/queries/{query_id}",
            json={
                "queryText": query_data["query"],
                "name": query_data["name"]
            },
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Update response status: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ Updated: {query_data['name']}")
            return True
        else:
            print(f"❌ Failed to update: {query_data['name']} - {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating: {query_data['name']} - {e}")
        return False

def main():
    """Main function to fix ROUND errors"""
    print("🔧 Fixing ROUND Function Errors in SQLPad Queries")
    print("=" * 60)
    
    # Step 1: Login
    session = login_to_sqlpad()
    if not session:
        print("❌ Failed to login, exiting")
        return
    
    # Step 2: Get existing queries
    existing_queries = get_queries(session)
    if not existing_queries:
        print("❌ No queries found!")
        return
    
    # Step 3: Update queries with fixes
    print("\n🔧 Updating queries with ROUND function fixes...")
    success_count = 0
    total_queries = len(FIXED_QUERIES)
    
    for i, fixed_query in enumerate(FIXED_QUERIES, 1):
        print(f"\n[{i}/{total_queries}] Fixing: {fixed_query['name']}")
        
        # Find matching query by name
        matching_query = None
        for existing_query in existing_queries:
            if existing_query.get('name') == fixed_query['name']:
                matching_query = existing_query
                break
        
        if matching_query:
            print(f"Found matching query with ID: {matching_query['id']}")
            if update_query(session, matching_query['id'], fixed_query):
                success_count += 1
        else:
            print(f"⚠️  Query not found: {fixed_query['name']}")
    
    print(f"\n🎉 ROUND Function Fix Complete!")
    print(f"✅ Successfully updated: {success_count}/{total_queries} queries")
    print(f"📊 Access SQLPad: {SQLPAD_URL}")
    print(f"🔗 Login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")

if __name__ == "__main__":
    main()
