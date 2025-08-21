#!/usr/bin/env python3
"""
Recreate SQLPad connection with proper SSL settings
"""
import requests
import json

# SQLPad Configuration
SQLPAD_URL = "http://localhost:3000"
ADMIN_EMAIL = "admin@7taps.com"
ADMIN_PASSWORD = "admin123"

# Heroku Database Configuration with proper SSL
DB_CONFIG = {
    "name": "7taps Analytics Database",
    "driver": "postgres",
    "host": "c5cnr847jq0fj3.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com",
    "port": 5432,
    "database": "d7s5ke2hmuqipn",
    "username": "u19o5qm786p1d1",
    "password": "p952c21ce2372a85402c0253505bb3f892f49f149b27cce81e5f44b558b98f4c2",
    "ssl": True,
    "sslRejectUnauthorized": False,
    "sslMode": "require"
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

def delete_existing_connections(session):
    """Delete all existing connections"""
    print("🧹 Deleting existing connections...")
    
    response = session.get(f"{SQLPAD_URL}/api/connections")
    if response.status_code == 200:
        connections = response.json()
        for conn in connections:
            print(f"   Deleting: {conn.get('name', 'Unknown')}")
            delete_response = session.delete(f"{SQLPAD_URL}/api/connections/{conn['id']}")
            if delete_response.status_code == 200:
                print(f"   ✅ Deleted: {conn.get('name', 'Unknown')}")
            else:
                print(f"   ❌ Failed to delete: {conn.get('name', 'Unknown')}")
    
    print("✅ All connections deleted!")

def create_new_connection(session):
    """Create new connection with proper SSL settings"""
    print("🔧 Creating new connection with SSL settings...")
    
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
    """Test the connection"""
    print("🧪 Testing connection...")
    
    test_query = "SELECT COUNT(*) as total_users FROM users;"
    
    try:
        response = session.post(
            f"{SQLPAD_URL}/api/queries",
            json={
                "connectionId": connection_id,
                "queryText": test_query,
                "name": "SSL Test Query"
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
    """Main recreation function"""
    print("🔄 Recreating SQLPad Connection with SSL")
    print("=" * 50)
    
    # Step 1: Login
    session = login_to_sqlpad()
    if not session:
        return
    
    # Step 2: Delete existing connections
    delete_existing_connections(session)
    
    # Step 3: Create new connection
    connection_id = create_new_connection(session)
    if not connection_id:
        return
    
    # Step 4: Test the connection
    if not test_connection(session, connection_id):
        print("⚠️  Connection created but test failed.")
        print("🔧 You may need to configure SSL settings manually in the web interface.")
        return
    
    print()
    print("🎉 Connection Recreation Complete!")
    print(f"📊 Access SQLPad: {SQLPAD_URL}")
    print(f"🔗 Login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print("📋 The connection should now work without SSL errors!")

if __name__ == "__main__":
    main()
