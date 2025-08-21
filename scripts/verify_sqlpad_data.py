#!/usr/bin/env python3
"""
Verify SQLPad can access the Heroku database data
"""
import requests
import json

# SQLPad Configuration
SQLPAD_URL = "http://localhost:3000"
ADMIN_EMAIL = "admin@7taps.com"
ADMIN_PASSWORD = "admin123"

def login_and_get_connections():
    """Login and get available connections"""
    print("🔐 Logging into SQLPad...")
    
    # Login
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
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return None, None
    
    print("✅ Login successful!")
    
    # Get connections
    response = session.get(f"{SQLPAD_URL}/api/connections")
    if response.status_code != 200:
        print(f"❌ Failed to get connections: {response.status_code}")
        return None, None
    
    connections = response.json()
    print(f"📋 Found {len(connections)} connections:")
    
    for conn in connections:
        print(f"  - {conn.get('name', 'Unknown')} (ID: {conn.get('id', 'Unknown')})")
    
    return session, connections

def run_test_queries(session, connection_id):
    """Run test queries to verify data access"""
    print(f"\n🔍 Testing database connection (ID: {connection_id})...")
    
    test_queries = [
        {
            "name": "Total Users",
            "query": "SELECT COUNT(*) as total_users FROM users;"
        },
        {
            "name": "Available Tables",
            "query": "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"
        },
        {
            "name": "Recent Activity",
            "query": "SELECT COUNT(*) as recent_activities FROM user_activities WHERE timestamp > NOW() - INTERVAL '7 days';"
        }
    ]
    
    for test in test_queries:
        print(f"\n📊 Running: {test['name']}")
        
        try:
            response = session.post(
                f"{SQLPAD_URL}/api/queries",
                json={
                    "connectionId": connection_id,
                    "queryText": test["query"],
                    "name": test["name"]
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Query executed successfully!")
                print(f"   Query ID: {result.get('id', 'Unknown')}")
            else:
                print(f"❌ Query failed: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Query error: {e}")

def main():
    """Main verification function"""
    print("🔍 SQLPad Data Verification")
    print("=" * 40)
    
    # Login and get connections
    session, connections = login_and_get_connections()
    if not session or not connections:
        return
    
    # Find the 7taps Analytics connection
    analytics_conn = None
    for conn in connections:
        if any(keyword in conn.get('name', '') for keyword in ["7taps Analytics", "SSL Require", "7tapbs"]):
            analytics_conn = conn
            break
    
    if not analytics_conn:
        print("❌ Analytics connection not found!")
        print("Available connections:")
        for conn in connections:
            print(f"  - {conn.get('name', 'Unknown')}")
        return
    
    print(f"\n🎯 Found target connection: {analytics_conn['name']}")
    
    # Run test queries
    run_test_queries(session, analytics_conn['id'])
    
    print(f"\n🎉 Verification Complete!")
    print(f"📊 Access SQLPad: {SQLPAD_URL}")
    print(f"🔗 Login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print(f"📋 Connection: {analytics_conn['name']}")

if __name__ == "__main__":
    main()
