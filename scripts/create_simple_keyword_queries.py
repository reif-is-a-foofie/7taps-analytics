#!/usr/bin/env python3
"""
Create simple keyword search queries for demo
"""
import requests
import json

# SQLPad Configuration
SQLPAD_URL = "http://localhost:3000"
ADMIN_EMAIL = "admin@7taps.com"
ADMIN_PASSWORD = "admin123"

# Simple keyword search queries
SIMPLE_QUERIES = [
    {
        "name": "All Stress Mentions",
        "query": """
        SELECT 
            u.user_id,
            ur.response_text,
            l.lesson_name,
            ur.timestamp,
            q.question_text
        FROM user_responses ur
        JOIN users u ON ur.user_id = u.id
        JOIN questions q ON ur.question_id = q.id
        JOIN lessons l ON q.lesson_id = l.id
        WHERE LOWER(ur.response_text) LIKE '%stress%'
        ORDER BY ur.timestamp DESC;
        """
    },
    {
        "name": "All Sleep Mentions",
        "query": """
        SELECT 
            u.user_id,
            ur.response_text,
            l.lesson_name,
            ur.timestamp,
            q.question_text
        FROM user_responses ur
        JOIN users u ON ur.user_id = u.id
        JOIN questions q ON ur.question_id = q.id
        JOIN lessons l ON q.lesson_id = l.id
        WHERE LOWER(ur.response_text) LIKE '%sleep%'
        ORDER BY ur.timestamp DESC;
        """
    },
    {
        "name": "Stress by Lesson",
        "query": """
        SELECT 
            l.lesson_name,
            COUNT(*) as stress_mentions,
            COUNT(DISTINCT u.user_id) as unique_users
        FROM user_responses ur
        JOIN users u ON ur.user_id = u.id
        JOIN questions q ON ur.question_id = q.id
        JOIN lessons l ON q.lesson_id = l.id
        WHERE LOWER(ur.response_text) LIKE '%stress%'
        GROUP BY l.lesson_name, l.lesson_number
        ORDER BY l.lesson_number;
        """
    },
    {
        "name": "Sleep by Lesson",
        "query": """
        SELECT 
            l.lesson_name,
            COUNT(*) as sleep_mentions,
            COUNT(DISTINCT u.user_id) as unique_users
        FROM user_responses ur
        JOIN users u ON ur.user_id = u.id
        JOIN questions q ON ur.question_id = q.id
        JOIN lessons l ON q.lesson_id = l.id
        WHERE LOWER(ur.response_text) LIKE '%sleep%'
        GROUP BY l.lesson_name, l.lesson_number
        ORDER BY l.lesson_number;
        """
    },
    {
        "name": "Top Stress Keywords",
        "query": """
        SELECT 
            CASE 
                WHEN LOWER(ur.response_text) LIKE '%work stress%' THEN 'Work Stress'
                WHEN LOWER(ur.response_text) LIKE '%stress management%' THEN 'Stress Management'
                WHEN LOWER(ur.response_text) LIKE '%stressful%' THEN 'Stressful Situations'
                WHEN LOWER(ur.response_text) LIKE '%reduce stress%' THEN 'Reduce Stress'
                WHEN LOWER(ur.response_text) LIKE '%stress level%' THEN 'Stress Levels'
                ELSE 'General Stress'
            END as stress_type,
            COUNT(*) as mentions,
            COUNT(DISTINCT u.user_id) as unique_users
        FROM user_responses ur
        JOIN users u ON ur.user_id = u.id
        WHERE LOWER(ur.response_text) LIKE '%stress%'
        GROUP BY stress_type
        ORDER BY mentions DESC;
        """
    },
    {
        "name": "Top Sleep Keywords",
        "query": """
        SELECT 
            CASE 
                WHEN LOWER(ur.response_text) LIKE '%sleep quality%' THEN 'Sleep Quality'
                WHEN LOWER(ur.response_text) LIKE '%sleep schedule%' THEN 'Sleep Schedule'
                WHEN LOWER(ur.response_text) LIKE '%sleep hygiene%' THEN 'Sleep Hygiene'
                WHEN LOWER(ur.response_text) LIKE '%sleep better%' THEN 'Sleep Better'
                WHEN LOWER(ur.response_text) LIKE '%sleep routine%' THEN 'Sleep Routine'
                WHEN LOWER(ur.response_text) LIKE '%sleep time%' THEN 'Sleep Time'
                ELSE 'General Sleep'
            END as sleep_type,
            COUNT(*) as mentions,
            COUNT(DISTINCT u.user_id) as unique_users
        FROM user_responses ur
        JOIN users u ON ur.user_id = u.id
        WHERE LOWER(ur.response_text) LIKE '%sleep%'
        GROUP BY sleep_type
        ORDER BY mentions DESC;
        """
    },
    {
        "name": "Stress vs Sleep Comparison",
        "query": """
        SELECT 
            'Stress' as topic,
            COUNT(*) as total_mentions,
            COUNT(DISTINCT u.user_id) as unique_users
        FROM user_responses ur
        JOIN users u ON ur.user_id = u.id
        WHERE LOWER(ur.response_text) LIKE '%stress%'
        
        UNION ALL
        
        SELECT 
            'Sleep' as topic,
            COUNT(*) as total_mentions,
            COUNT(DISTINCT u.user_id) as unique_users
        FROM user_responses ur
        JOIN users u ON ur.user_id = u.id
        WHERE LOWER(ur.response_text) LIKE '%sleep%'
        
        ORDER BY total_mentions DESC;
        """
    },
    {
        "name": "Recent Stress Responses",
        "query": """
        SELECT 
            u.user_id,
            ur.response_text,
            l.lesson_name,
            ur.timestamp,
            CASE 
                WHEN LENGTH(ur.response_text) > 100 THEN 
                    LEFT(ur.response_text, 100) || '...'
                ELSE ur.response_text
            END as short_response
        FROM user_responses ur
        JOIN users u ON ur.user_id = u.id
        JOIN questions q ON ur.question_id = q.id
        JOIN lessons l ON q.lesson_id = l.id
        WHERE LOWER(ur.response_text) LIKE '%stress%'
        ORDER BY ur.timestamp DESC
        LIMIT 20;
        """
    },
    {
        "name": "Recent Sleep Responses",
        "query": """
        SELECT 
            u.user_id,
            ur.response_text,
            l.lesson_name,
            ur.timestamp,
            CASE 
                WHEN LENGTH(ur.response_text) > 100 THEN 
                    LEFT(ur.response_text, 100) || '...'
                ELSE ur.response_text
            END as short_response
        FROM user_responses ur
        JOIN users u ON ur.user_id = u.id
        JOIN questions q ON ur.question_id = q.id
        JOIN lessons l ON q.lesson_id = l.id
        WHERE LOWER(ur.response_text) LIKE '%sleep%'
        ORDER BY ur.timestamp DESC
        LIMIT 20;
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

def create_query(session, query_data):
    """Create a query in SQLPad"""
    try:
        response = session.post(
            f"{SQLPAD_URL}/api/queries",
            json={
                "connectionId": "22519411-e15f-4707-9e9a-aa4081593f7f",  # 7taps Analytics Database
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
    """Main function to create simple keyword queries"""
    print("🔍 Creating Simple Keyword Search Queries")
    print("=" * 50)
    
    # Step 1: Login
    session = login_to_sqlpad()
    if not session:
        return
    
    # Step 2: Create all simple queries
    print("\n🔧 Creating simple keyword search queries...")
    success_count = 0
    total_queries = len(SIMPLE_QUERIES)
    
    for i, query_data in enumerate(SIMPLE_QUERIES, 1):
        print(f"\n[{i}/{total_queries}] Creating: {query_data['name']}")
        
        if create_query(session, query_data):
            success_count += 1
    
    print(f"\n🎉 Simple Query Creation Complete!")
    print(f"✅ Successfully created: {success_count}/{total_queries} queries")
    print(f"📊 Access SQLPad: {SQLPAD_URL}")
    print(f"🔗 Login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print()
    print("📋 New Simple Demo Queries:")
    for query in SIMPLE_QUERIES:
        print(f"   - {query['name']}")
    print()
    print("💡 Perfect for demos - simple keyword searches that show real insights!")

if __name__ == "__main__":
    main()
