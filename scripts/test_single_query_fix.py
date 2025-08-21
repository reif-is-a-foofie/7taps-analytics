#!/usr/bin/env python3
"""
Test fixing a single query with ROUND function error
"""
import requests
import json

# SQLPad Configuration
SQLPAD_URL = "http://localhost:3000"
ADMIN_EMAIL = "admin@7taps.com"
ADMIN_PASSWORD = "admin123"

def main():
    print("🧪 Testing Single Query Fix")
    print("=" * 40)
    
    # Login
    print("🔐 Logging in...")
    session = requests.Session()
    response = session.post(
        f"{SQLPAD_URL}/api/signin",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Login status: {response.status_code}")
    if response.status_code != 200:
        print("❌ Login failed")
        return
    
    # Get queries
    print("📋 Getting queries...")
    response = session.get(f"{SQLPAD_URL}/api/queries")
    print(f"Get queries status: {response.status_code}")
    
    if response.status_code != 200:
        print("❌ Failed to get queries")
        return
    
    queries = response.json()
    print(f"Found {len(queries)} queries")
    
    # Find the specific query to fix
    target_query = None
    for query in queries:
        if query.get('name') == '01 - Lesson Completion Funnel':
            target_query = query
            break
    
    if not target_query:
        print("❌ Target query not found")
        return
    
    print(f"Found target query: {target_query['name']} (ID: {target_query['id']})")
    
    # Fixed query with proper ROUND function
    fixed_query = """
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
        END as completion_rate
    FROM lessons l
    LEFT JOIN user_activities ua ON l.id = ua.lesson_id
    GROUP BY l.id, l.lesson_name, l.lesson_number
    ORDER BY l.lesson_number;
    """
    
    # Update the query
    print("🔧 Updating query...")
    response = session.put(
        f"{SQLPAD_URL}/api/queries/{target_query['id']}",
        json={
            "queryText": fixed_query,
            "name": target_query['name']
        },
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Update status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Query updated successfully!")
    else:
        print(f"❌ Update failed: {response.text}")

if __name__ == "__main__":
    main()
