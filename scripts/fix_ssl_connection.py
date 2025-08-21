#!/usr/bin/env python3
"""
Fix SSL Connection Issues in SQLPad
"""
import requests
import json

# SQLPad Configuration
SQLPAD_URL = "http://localhost:3000"
ADMIN_EMAIL = "admin@7taps.com"
ADMIN_PASSWORD = "admin123"

# Different SSL configurations to try
SSL_CONFIGS = [
    {
        "name": "SSL Require (No Verify)",
        "ssl": True,
        "sslRejectUnauthorized": False
    },
    {
        "name": "SSL Prefer",
        "ssl": True,
        "sslRejectUnauthorized": False,
        "sslMode": "prefer"
    },
    {
        "name": "SSL Allow",
        "ssl": True,
        "sslRejectUnauthorized": False,
        "sslMode": "allow"
    },
    {
        "name": "SSL Disable",
        "ssl": False
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

def update_connection_ssl(session, connection_id, ssl_config):
    """Update connection with SSL configuration"""
    print(f"🔧 Trying SSL config: {ssl_config['name']}")
    
    # Get current connection details
    response = session.get(f"{SQLPAD_URL}/api/connections/{connection_id}")
    if response.status_code != 200:
        print(f"❌ Failed to get connection details: {response.status_code}")
        return False
    
    connection_data = response.json()
    
    # Update SSL settings
    connection_data.update(ssl_config)
    
    # Remove the id field as it's not needed for update
    if 'id' in connection_data:
        del connection_data['id']
    
    # Update the connection
    response = session.put(
        f"{SQLPAD_URL}/api/connections/{connection_id}",
        json=connection_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        print(f"✅ Updated connection with {ssl_config['name']}")
        return True
    else:
        print(f"❌ Failed to update connection: {response.status_code}")
        print(f"Response: {response.text}")
        return False

def test_connection(session, connection_id):
    """Test the connection with a simple query"""
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
            return True
        else:
            print(f"❌ Connection test failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Connection test error: {e}")
        return False

def main():
    """Main SSL fix function"""
    print("🔧 SQLPad SSL Connection Fix")
    print("=" * 40)
    
    # Step 1: Login
    session = login_to_sqlpad()
    if not session:
        return
    
    # Step 2: Get the connection
    connection = get_connection(session)
    if not connection:
        print("❌ No 7taps Analytics connection found!")
        return
    
    connection_id = connection['id']
    print(f"📋 Found connection: {connection['name']} (ID: {connection_id})")
    
    # Step 3: Try different SSL configurations
    print("\n🔧 Testing different SSL configurations...")
    
    for ssl_config in SSL_CONFIGS:
        print(f"\n--- Testing: {ssl_config['name']} ---")
        
        # Update connection with SSL config
        if update_connection_ssl(session, connection_id, ssl_config):
            # Test the connection
            if test_connection(session, connection_id):
                print(f"🎉 SUCCESS! {ssl_config['name']} works!")
                print(f"📊 Access SQLPad: {SQLPAD_URL}")
                print(f"🔗 Login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
                return
            else:
                print(f"❌ {ssl_config['name']} failed the test")
        else:
            print(f"❌ Failed to update with {ssl_config['name']}")
    
    print("\n❌ All SSL configurations failed!")
    print("🔧 You'll need to configure SSL manually in the SQLPad web interface.")
    print("📋 Run: python3 scripts/manual_ssl_configure.py")

if __name__ == "__main__":
    main()
