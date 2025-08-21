#!/usr/bin/env python3
"""
Test SQLPad UI Connection - Simulate actual web interface usage
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

def test_ui_query_execution(session, connection_id):
    """Test query execution as it would happen in the UI"""
    print("🧪 Testing UI Query Execution...")
    
    # This simulates what happens when you click "Run" in the UI
    test_query = "SELECT COUNT(*) as total_users FROM users;"
    
    try:
        # First, create the query (this is what the UI does)
        create_response = session.post(
            f"{SQLPAD_URL}/api/queries",
            json={
                "connectionId": connection_id,
                "queryText": test_query,
                "name": "UI Test Query"
            },
            headers={"Content-Type": "application/json"}
        )
        
        if create_response.status_code != 200:
            print(f"❌ Failed to create query: {create_response.status_code}")
            print(f"Response: {create_response.text}")
            return False
        
        query_id = create_response.json().get('id')
        print(f"✅ Query created with ID: {query_id}")
        
        # Now execute the query (this simulates the UI execution)
        execute_response = session.post(
            f"{SQLPAD_URL}/api/queries/{query_id}/execute",
            headers={"Content-Type": "application/json"}
        )
        
        if execute_response.status_code == 200:
            result = execute_response.json()
            print("✅ Query executed successfully!")
            print(f"   Status: {result.get('status', 'Unknown')}")
            return True
        else:
            print(f"❌ Query execution failed: {execute_response.status_code}")
            print(f"Response: {execute_response.text}")
            
            # Check if this is the SSL error
            if "no pg_hba.conf entry" in execute_response.text or "no encryption" in execute_response.text:
                print("🚨 SSL ERROR DETECTED!")
                print("   The UI is still trying to connect without SSL encryption.")
                print("   This means the SSL settings are not being applied correctly.")
            return False
            
    except Exception as e:
        print(f"❌ Query execution error: {e}")
        return False

def check_connection_settings(session, connection_id):
    """Check the actual connection settings being used"""
    print("🔍 Checking Connection Settings...")
    
    try:
        response = session.get(f"{SQLPAD_URL}/api/connections/{connection_id}")
        if response.status_code == 200:
            connection = response.json()
            print(f"📋 Connection Details:")
            print(f"   Name: {connection.get('name', 'Unknown')}")
            print(f"   Host: {connection.get('host', 'Unknown')}")
            print(f"   Database: {connection.get('database', 'Unknown')}")
            print(f"   SSL: {connection.get('ssl', 'Unknown')}")
            print(f"   SSL Mode: {connection.get('sslMode', 'Unknown')}")
            print(f"   SSL Reject Unauthorized: {connection.get('sslRejectUnauthorized', 'Unknown')}")
            
            # Check if SSL settings are actually set
            ssl_enabled = connection.get('ssl', False)
            ssl_mode = connection.get('sslMode', '')
            
            if not ssl_enabled or not ssl_mode:
                print("⚠️  SSL settings are not properly configured!")
                print("   This explains why the UI is still getting SSL errors.")
                return False
            else:
                print("✅ SSL settings appear to be configured.")
                return True
        else:
            print(f"❌ Failed to get connection details: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking connection settings: {e}")
        return False

def main():
    """Main UI test function"""
    print("🌐 SQLPad UI Connection Test")
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
    
    # Step 3: Check connection settings
    ssl_configured = check_connection_settings(session, connection['id'])
    
    # Step 4: Test UI query execution
    ui_working = test_ui_query_execution(session, connection['id'])
    
    print(f"\n🎯 UI Test Results:")
    if ui_working:
        print("✅ UI Connection: WORKING")
        print("✅ SSL Configuration: WORKING")
    else:
        print("❌ UI Connection: FAILED")
        if not ssl_configured:
            print("🔧 Issue: SSL settings not properly configured")
            print("💡 Solution: Need to manually configure SSL in the web interface")
        else:
            print("🔧 Issue: SSL settings configured but still failing")
            print("💡 Solution: May need different SSL configuration")

if __name__ == "__main__":
    main()
