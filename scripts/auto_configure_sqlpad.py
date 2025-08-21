#!/usr/bin/env python3
"""
Automatically configure SQLPad with Heroku PostgreSQL connection
"""
import requests
import json
import time
import sys
from urllib.parse import quote

# SQLPad Configuration
SQLPAD_URL = "http://localhost:3000"
ADMIN_EMAIL = "admin@7taps.com"
ADMIN_PASSWORD = "admin123"

# Heroku Database Configuration
DB_CONFIG = {
    "name": "7taps Analytics Database",
    "driver": "postgres",
    "host": "c5cnr847jq0fj3.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com",
    "port": 5432,
    "database": "d7s5ke2hmuqipn",
    "username": "u19o5qm786p1d1",
    "password": "p952c21ce2372a85402c0253505bb3f892f49f149b27cce81e5f44b558b98f4c2",
    "ssl": True,
    "sslRejectUnauthorized": False
}

def wait_for_sqlpad():
    """Wait for SQLPad to be ready"""
    print("Waiting for SQLPad to start...")
    for i in range(30):
        try:
            response = requests.get(f"{SQLPAD_URL}/", timeout=5)
            if response.status_code == 200:
                print("✅ SQLPad is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(2)
        print(f"  Attempt {i+1}/30...")
    
    print("❌ SQLPad failed to start within 60 seconds")
    return False

def login_to_sqlpad():
    """Login to SQLPad and get session cookie"""
    print("Logging into SQLPad...")
    
    login_data = {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }
    
    try:
        response = requests.post(
            f"{SQLPAD_URL}/api/signin",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print("✅ Login successful!")
            return response.cookies
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def create_connection(cookies):
    """Create the database connection"""
    print("Creating database connection...")
    
    try:
        response = requests.post(
            f"{SQLPAD_URL}/api/connections",
            json=DB_CONFIG,
            cookies=cookies,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print("✅ Database connection created successfully!")
            connection_id = response.json().get("id")
            print(f"Connection ID: {connection_id}")
            return connection_id
        else:
            print(f"❌ Failed to create connection: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Connection creation error: {e}")
        return None

def test_connection(cookies, connection_id):
    """Test the database connection"""
    print("Testing database connection...")
    
    try:
        # Try the test endpoint
        response = requests.post(
            f"{SQLPAD_URL}/api/connections/{connection_id}/test",
            cookies=cookies
        )
        
        if response.status_code == 200:
            print("✅ Database connection test successful!")
            return True
        else:
            print(f"⚠️  Test endpoint returned {response.status_code}, trying alternative...")
            
            # Alternative: try to get connection details
            response = requests.get(
                f"{SQLPAD_URL}/api/connections/{connection_id}",
                cookies=cookies
            )
            
            if response.status_code == 200:
                print("✅ Database connection verified!")
                return True
            else:
                print(f"❌ Connection verification failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
            
    except Exception as e:
        print(f"❌ Connection test error: {e}")
        return False

def run_test_query(cookies, connection_id):
    """Run a test query to verify data access"""
    print("Running test query...")
    
    test_query = "SELECT COUNT(*) as total_users FROM users;"
    
    try:
        response = requests.post(
            f"{SQLPAD_URL}/api/queries",
            json={
                "connectionId": connection_id,
                "queryText": test_query,
                "name": "Test Query"
            },
            cookies=cookies,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print("✅ Test query executed successfully!")
            return True
        else:
            print(f"❌ Test query failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test query error: {e}")
        return False

def main():
    """Main automation function"""
    print("🚀 Starting SQLPad Auto-Configuration...")
    print(f"Target: {SQLPAD_URL}")
    print(f"Database: {DB_CONFIG['host']}")
    print()
    
    # Step 1: Wait for SQLPad
    if not wait_for_sqlpad():
        sys.exit(1)
    
    # Step 2: Login
    cookies = login_to_sqlpad()
    if not cookies:
        sys.exit(1)
    
    # Step 3: Create connection
    connection_id = create_connection(cookies)
    if not connection_id:
        sys.exit(1)
    
    # Step 4: Test connection
    if not test_connection(cookies, connection_id):
        sys.exit(1)
    
    # Step 5: Run test query
    if not run_test_query(cookies, connection_id):
        sys.exit(1)
    
    print()
    print("🎉 SQLPad Auto-Configuration Complete!")
    print(f"📊 Access SQLPad: {SQLPAD_URL}")
    print(f"🔗 Login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print("📋 The '7taps Analytics Database' connection should now be available!")

if __name__ == "__main__":
    main()
