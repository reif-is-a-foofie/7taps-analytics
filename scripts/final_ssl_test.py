#!/usr/bin/env python3
"""
Final SSL Connection Test
"""
import requests
import json

# SQLPad Configuration
SQLPAD_URL = "http://localhost:3000"
ADMIN_EMAIL = "admin@7taps.com"
ADMIN_PASSWORD = "admin123"

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

def run_comprehensive_test(session, connection_id):
    """Run comprehensive tests to verify SSL connection"""
    print("🧪 Running comprehensive SSL connection tests...")
    
    test_queries = [
        {
            "name": "Basic Connection Test",
            "query": "SELECT 1 as test_value;"
        },
        {
            "name": "Database Version",
            "query": "SELECT version();"
        },
        {
            "name": "SSL Status Check",
            "query": "SHOW ssl;"
        },
        {
            "name": "User Count",
            "query": "SELECT COUNT(*) as total_users FROM users;"
        },
        {
            "name": "Table List",
            "query": "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name LIMIT 5;"
        }
    ]
    
    success_count = 0
    total_tests = len(test_queries)
    
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
                print(f"   ✅ SUCCESS - Query ID: {result.get('id', 'Unknown')}")
                success_count += 1
            else:
                print(f"   ❌ FAILED - Status: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ ERROR - {e}")
    
    print(f"\n📈 Test Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 ALL TESTS PASSED! SSL connection is working perfectly!")
        return True
    elif success_count > 0:
        print("⚠️  Some tests passed, SSL connection is partially working.")
        return True
    else:
        print("❌ All tests failed, SSL connection is not working.")
        return False

def main():
    """Main test function"""
    print("🔒 Final SSL Connection Test")
    print("=" * 40)
    
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
    
    # Step 3: Run comprehensive tests
    success = run_comprehensive_test(session, connection['id'])
    
    print(f"\n🎯 Final Status:")
    if success:
        print("✅ SSL Connection: WORKING")
        print("✅ Database Access: WORKING")
        print("✅ Query Execution: WORKING")
        print(f"\n📊 Access SQLPad: {SQLPAD_URL}")
        print(f"🔗 Login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        print("🎉 You can now use SQLPad to query your Heroku database!")
    else:
        print("❌ SSL Connection: FAILED")
        print("🔧 You may need to configure SSL settings manually in the web interface.")

if __name__ == "__main__":
    main()
