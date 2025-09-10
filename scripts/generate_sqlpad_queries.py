#!/usr/bin/env python3
"""
Generate SQLPad Queries from Database Overview
"""
import requests
import json
import time

# SQLPad Configuration
SQLPAD_URL = "http://localhost:3000"
ADMIN_EMAIL = "admin@7taps.com"
ADMIN_PASSWORD = "admin123"

# Sample queries from DATABASE_OVERVIEW.md
SAMPLE_QUERIES = [
    {
        "name": "01 - Total Users",
        "query": "SELECT COUNT(DISTINCT id) as total_users FROM users;"
    },
    {
        "name": "02 - Most Active Users",
        "query": """
SELECT 
    u.user_id,
    COUNT(ua.id) as activity_count,
    COUNT(DISTINCT ua.lesson_id) as lessons_accessed,
    MIN(ua.timestamp) as first_activity,
    MAX(ua.timestamp) as last_activity
FROM users u
LEFT JOIN user_activities ua ON u.id = ua.user_id
GROUP BY u.id, u.user_id
ORDER BY activity_count DESC
LIMIT 10;
"""
    },
    {
        "name": "03 - Lesson Completion Rates",
        "query": """
SELECT 
    l.lesson_name,
    l.lesson_number,
    COUNT(DISTINCT ua.user_id) as users_started,
    COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END) as users_completed,
    ROUND(
        (COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END)::float / 
         NULLIF(COUNT(DISTINCT ua.user_id), 0) * 100), 2
    ) as completion_rate
FROM lessons l
LEFT JOIN user_activities ua ON l.id = ua.lesson_id
GROUP BY l.id, l.lesson_name, l.lesson_number
ORDER BY l.lesson_number;
"""
    },
    {
        "name": "04 - Daily Activity (Last 30 Days)",
        "query": """
SELECT 
    DATE(ua.timestamp) as activity_date,
    COUNT(*) as activity_count,
    COUNT(DISTINCT ua.user_id) as unique_users
FROM user_activities ua
WHERE ua.timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(ua.timestamp)
ORDER BY activity_date;
"""
    },
    {
        "name": "05 - Most Answered Questions",
        "query": """
SELECT 
    q.question_text,
    q.question_type,
    COUNT(ur.id) as response_count,
    AVG(ur.score_scaled) as avg_score
FROM questions q
LEFT JOIN user_responses ur ON q.id = ur.question_id
GROUP BY q.id, q.question_text, q.question_type
ORDER BY response_count DESC
LIMIT 10;
"""
    },
    {
        "name": "06 - Common Response Patterns",
        "query": """
SELECT 
    response_text,
    COUNT(*) as frequency,
    COUNT(DISTINCT user_id) as unique_users
FROM user_responses 
WHERE response_text IS NOT NULL
GROUP BY response_text
ORDER BY frequency DESC
LIMIT 15;
"""
    },
    {
        "name": "07 - Cohort Performance",
        "query": """
SELECT 
    u.cohort,
    COUNT(DISTINCT u.id) as cohort_size,
    COUNT(ua.id) as total_activities,
    COUNT(DISTINCT ua.lesson_id) as lessons_accessed,
    AVG(ur.score_scaled) as avg_score
FROM users u
LEFT JOIN user_activities ua ON u.id = ua.user_id
LEFT JOIN user_responses ur ON u.id = ur.user_id
WHERE u.cohort IS NOT NULL
GROUP BY u.cohort
ORDER BY cohort_size DESC;
"""
    },
    {
        "name": "08 - User Learning Progression",
        "query": """
WITH user_progress AS (
    SELECT 
        ua.user_id,
        l.lesson_number,
        l.lesson_name,
        MIN(ua.timestamp) as first_access,
        MAX(ua.timestamp) as last_access,
        COUNT(*) as activity_count
    FROM user_activities ua
    JOIN lessons l ON ua.lesson_id = l.id
    GROUP BY ua.user_id, l.lesson_number, l.lesson_name
)
SELECT 
    lesson_number,
    lesson_name,
    COUNT(DISTINCT user_id) as users_reached,
    AVG(activity_count) as avg_activities,
    AVG(EXTRACT(EPOCH FROM (last_access - first_access))/3600) as avg_hours_spent
FROM user_progress
GROUP BY lesson_number, lesson_name
ORDER BY lesson_number;
"""
    },
    {
        "name": "09 - User Engagement Score",
        "query": """
SELECT 
    u.user_id,
    COUNT(ua.id) as total_activities,
    COUNT(DISTINCT ua.lesson_id) as lessons_accessed,
    COUNT(ur.id) as total_responses,
    AVG(ur.score_scaled) as avg_score,
    CASE 
        WHEN COUNT(ua.id) > 50 THEN 'High'
        WHEN COUNT(ua.id) > 20 THEN 'Medium'
        ELSE 'Low'
    END as engagement_level
FROM users u
LEFT JOIN user_activities ua ON u.id = ua.user_id
LEFT JOIN user_responses ur ON u.id = ur.user_id
GROUP BY u.id, u.user_id
ORDER BY total_activities DESC;
"""
    },
    {
        "name": "10 - Dashboard Key Metrics",
        "query": """
SELECT 
    (SELECT COUNT(DISTINCT id) FROM users) as total_users,
    (SELECT COUNT(*) FROM user_activities) as total_activities,
    (SELECT COUNT(*) FROM user_responses) as total_responses,
    (SELECT COUNT(DISTINCT lesson_id) FROM user_activities) as active_lessons,
    (SELECT AVG(score_scaled) FROM user_responses WHERE score_scaled IS NOT NULL) as avg_score;
"""
    },
    {
        "name": "11 - Recent Activity",
        "query": """
SELECT 
    u.user_id,
    ua.activity_type,
    l.lesson_name,
    ua.timestamp
FROM user_activities ua
JOIN users u ON ua.user_id = u.id
LEFT JOIN lessons l ON ua.lesson_id = l.id
ORDER BY ua.timestamp DESC
LIMIT 20;
"""
    },
    {
        "name": "12 - Activity Types Summary",
        "query": """
SELECT 
    activity_type, 
    COUNT(*) as count,
    COUNT(DISTINCT user_id) as unique_users
FROM user_activities 
GROUP BY activity_type
ORDER BY count DESC;
"""
    },
    {
        "name": "13 - Lesson Overview",
        "query": """
SELECT 
    l.lesson_number,
    l.lesson_name,
    COUNT(DISTINCT ua.user_id) as users_accessed,
    COUNT(ua.id) as total_activities,
    COUNT(ur.id) as total_responses
FROM lessons l
LEFT JOIN user_activities ua ON l.id = ua.lesson_id
LEFT JOIN user_responses ur ON l.lesson_number = ur.lesson_number
GROUP BY l.id, l.lesson_number, l.lesson_name
ORDER BY l.lesson_number;
"""
    },
    {
        "name": "14 - Response Score Distribution",
        "query": """
SELECT 
    CASE 
        WHEN score_scaled >= 0.8 THEN 'Excellent (80-100%)'
        WHEN score_scaled >= 0.6 THEN 'Good (60-79%)'
        WHEN score_scaled >= 0.4 THEN 'Fair (40-59%)'
        WHEN score_scaled >= 0.2 THEN 'Poor (20-39%)'
        ELSE 'Very Poor (0-19%)'
    END as score_range,
    COUNT(*) as response_count,
    COUNT(DISTINCT user_id) as unique_users
FROM user_responses 
WHERE score_scaled IS NOT NULL
GROUP BY score_range
ORDER BY MIN(score_scaled);
"""
    },
    {
        "name": "15 - Table Row Counts",
        "query": """
SELECT 
    'users' as table_name, COUNT(*) as row_count FROM users
UNION ALL
SELECT 'lessons', COUNT(*) FROM lessons
UNION ALL
SELECT 'questions', COUNT(*) FROM questions
UNION ALL
SELECT 'user_activities', COUNT(*) FROM user_activities
UNION ALL
SELECT 'user_responses', COUNT(*) FROM user_responses
ORDER BY row_count DESC;
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
    
    if response.status_code == 200:
        print("✅ Login successful!")
        return session
    else:
        print(f"❌ Login failed: {response.status_code}")
        return None

def get_connection(session):
    """Get the analytics connection"""
    response = session.get(f"{SQLPAD_URL}/api/connections")
    if response.status_code == 200:
        connections = response.json()
        for conn in connections:
            if "7taps Analytics" in conn.get('name', ''):
                return conn
    return None

def create_query(session, connection_id, query_data):
    """Create a query in SQLPad"""
    try:
        response = session.post(
            f"{SQLPAD_URL}/api/queries",
            json={
                "connectionId": connection_id,
                "queryText": query_data["query"],
                "name": query_data["name"]
            },
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Created: {query_data['name']} (ID: {result.get('id', 'Unknown')})")
            return True
        else:
            print(f"❌ Failed to create: {query_data['name']} - {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating: {query_data['name']} - {e}")
        return False

def main():
    """Main function to generate all queries"""
    print("📊 Generating SQLPad Queries from Database Overview")
    print("=" * 60)
    
    # Step 1: Login
    session = login_to_sqlpad()
    if not session:
        return
    
    # Step 2: Get connection
    connection = get_connection(session)
    if not connection:
        print("❌ No 7taps Analytics connection found!")
        return
    
    print(f"📋 Found connection: {connection['name']} (ID: {connection['id']})")
    print()
    
    # Step 3: Create all queries
    print("🔧 Creating sample queries...")
    success_count = 0
    total_queries = len(SAMPLE_QUERIES)
    
    for i, query_data in enumerate(SAMPLE_QUERIES, 1):
        print(f"\n[{i}/{total_queries}] Creating: {query_data['name']}")
        
        if create_query(session, connection['id'], query_data):
            success_count += 1
        
        # Small delay to avoid overwhelming the API
        time.sleep(0.5)
    
    print(f"\n🎉 Query Generation Complete!")
    print(f"✅ Successfully created: {success_count}/{total_queries} queries")
    print(f"📊 Access SQLPad: {SQLPAD_URL}")
    print(f"🔗 Login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print()
    print("📋 Available Queries:")
    for query in SAMPLE_QUERIES:
        print(f"   - {query['name']}")
    print()
    print("💡 You can now run these queries in SQLPad to explore your data!")

if __name__ == "__main__":
    main()


