#!/usr/bin/env python3
"""
Clean up duplicate SQLPad connections and create a single working connection
"""
import requests
import json
import time

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

def get_connections(session):
    """Get all connections"""
    response = session.get(f"{SQLPAD_URL}/api/connections")
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Failed to get connections: {response.status_code}")
        return []

def delete_connection(session, connection_id):
    """Delete a connection"""
    response = session.delete(f"{SQLPAD_URL}/api/connections/{connection_id}")
    if response.status_code == 200:
        print(f"✅ Deleted connection {connection_id}")
        return True
    else:
        print(f"❌ Failed to delete connection {connection_id}: {response.status_code}")
        return False

def cleanup_connections(session):
    """Clean up all existing connections"""
    print("🧹 Cleaning up existing connections...")
    
    connections = get_connections(session)
    if not connections:
        print("No connections found to clean up.")
        return
    
    print(f"Found {len(connections)} connections:")
    for conn in connections:
        print(f"  - {conn.get('name', 'Unknown')} (ID: {conn.get('id', 'Unknown')})")
    
    # Delete all connections
    for conn in connections:
        delete_connection(session, conn['id'])
    
    print("✅ All connections cleaned up!")

def create_working_connection(session):
    """Create a single working connection"""
    print("🔧 Creating new working connection...")
    
    try:
        response = session.post(
            f"{SQLPAD_URL}/api/connections",
            json=DB_CONFIG,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            connection_id = result.get("id")
            print(f"✅ Connection created successfully!")
            print(f"   ID: {connection_id}")
            print(f"   Name: {result.get('name', 'Unknown')}")
            return connection_id
        else:
            print(f"❌ Failed to create connection: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Connection creation error: {e}")
        return None

def test_connection(session, connection_id):
    """Test the connection with a simple query"""
    print("🧪 Testing connection...")
    
    test_query = "SELECT COUNT(*) as total_users FROM users;"
    
    try:
        response = session.post(
            f"{SQLPAD_URL}/api/queries",
            json={
                "connectionId": connection_id,
                "queryText": test_query,
                "name": "Connection Test"
            },
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Connection test successful!")
            print(f"   Query ID: {result.get('id', 'Unknown')}")
            return True
        else:
            print(f"❌ Connection test failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Connection test error: {e}")
        return False

def main():
    """Main cleanup and configuration function"""
    print("🧹 SQLPad Connection Cleanup & Configuration")
    print("=" * 50)
    
    # Step 1: Login
    session = login_to_sqlpad()
    if not session:
        return
    
    # Step 2: Clean up existing connections
    cleanup_connections(session)
    
    # Step 3: Create new working connection
    connection_id = create_working_connection(session)
    if not connection_id:
        return
    
    # Step 4: Test the connection
    if not test_connection(session, connection_id):
        print("⚠️  Connection created but test failed. You may need to configure SSL settings manually.")
        return
    
    print()
    print("🎉 Cleanup and Configuration Complete!")
    print(f"📊 Access SQLPad: {SQLPAD_URL}")
    print(f"🔗 Login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print("📋 You should now have a single working '7taps Analytics Database' connection!")

if __name__ == "__main__":
    main()


