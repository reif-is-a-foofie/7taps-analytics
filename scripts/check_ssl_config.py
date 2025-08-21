#!/usr/bin/env python3
"""
Check current SSL configuration of SQLPad connection
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

def get_connection_details(session):
    """Get detailed connection information"""
    response = session.get(f"{SQLPAD_URL}/api/connections")
    if response.status_code == 200:
        connections = response.json()
        for conn in connections:
            if any(keyword in conn.get('name', '') for keyword in ["7taps Analytics", "SSL Require", "7tapbs"]):
                return conn
    return None

def main():
    """Main function to check SSL configuration"""
    print("🔍 Checking SQLPad SSL Configuration")
    print("=" * 40)
    
    # Step 1: Login
    session = login_to_sqlpad()
    if not session:
        return
    
    # Step 2: Get connection details
    connection = get_connection_details(session)
    if not connection:
        print("❌ No analytics connection found!")
        return
    
    print(f"\n📋 Connection Details:")
    print(f"   Name: {connection.get('name', 'Unknown')}")
    print(f"   ID: {connection.get('id', 'Unknown')}")
    print(f"   Driver: {connection.get('driver', 'Unknown')}")
    print(f"   Host: {connection.get('host', 'Unknown')}")
    print(f"   Port: {connection.get('port', 'Unknown')}")
    print(f"   Database: {connection.get('database', 'Unknown')}")
    print(f"   Username: {connection.get('username', 'Unknown')}")
    
    print(f"\n🔒 SSL Configuration:")
    print(f"   SSL Enabled: {connection.get('ssl', 'Unknown')}")
    print(f"   SSL Reject Unauthorized: {connection.get('sslRejectUnauthorized', 'Unknown')}")
    print(f"   SSL Mode: {connection.get('sslMode', 'Unknown')}")
    
    # Check for any other SSL-related fields
    ssl_fields = {k: v for k, v in connection.items() if 'ssl' in k.lower()}
    if ssl_fields:
        print(f"\n🔍 All SSL-related fields:")
        for field, value in ssl_fields.items():
            print(f"   {field}: {value}")
    
    print(f"\n💡 If you're still seeing SSL errors, try these steps:")
    print(f"   1. Go to http://localhost:3000")
    print(f"   2. Login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print(f"   3. Click 'Connections' → '{connection.get('name', 'Unknown')}'")
    print(f"   4. Ensure SSL settings are:")
    print(f"      ✅ Use SSL: Checked")
    print(f"      🔧 SSL Mode: 'require' (not 'verify-full')")
    print(f"      ⚠️  SSL Certificate Verification: Disabled")
    print(f"   5. Click 'Test Connection'")
    print(f"   6. Click 'Save'")

if __name__ == "__main__":
    main()
