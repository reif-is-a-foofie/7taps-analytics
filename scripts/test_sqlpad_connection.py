#!/usr/bin/env python3
"""
Test SQLPad connection to Heroku database
"""

import requests
import json
import time

def test_sqlpad_connection():
    """Test SQLPad connection and run a sample query"""
    
    # SQLPad base URL
    base_url = "http://localhost:3000"
    
    # Test basic connectivity
    print("🔍 Testing SQLPad connectivity...")
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print("✅ SQLPad is accessible")
        else:
            print(f"❌ SQLPad returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to SQLPad: {e}")
        return False
    
    # Test database connection
    print("\n🔍 Testing database connection...")
    try:
        # Get connections
        response = requests.get(f"{base_url}/api/connections")
        if response.status_code == 200:
            connections = response.json()
            print(f"✅ Found {len(connections)} database connections")
            
            # Look for our Heroku connection
            heroku_conn = None
            for conn in connections:
                if conn.get('name') == '7taps Analytics Database':
                    heroku_conn = conn
                    break
            
            if heroku_conn:
                print(f"✅ Found Heroku connection: {heroku_conn['name']}")
                print(f"   Host: {heroku_conn.get('host', 'N/A')}")
                print(f"   Database: {heroku_conn.get('database', 'N/A')}")
                print(f"   Driver: {heroku_conn.get('driver', 'N/A')}")
            else:
                print("❌ Heroku connection not found")
                return False
        else:
            print(f"❌ Failed to get connections: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing connections: {e}")
        return False
    
    # Test a simple query
    print("\n🔍 Testing sample query...")
    try:
        # Simple query to test connection
        test_query = "SELECT COUNT(*) as total_users FROM users"
        
        # Create a batch (query execution)
        batch_data = {
            "connectionId": heroku_conn['id'],
            "queryText": test_query,
            "name": "Test Query"
        }
        
        response = requests.post(f"{base_url}/api/batches", json=batch_data)
        if response.status_code == 200:
            batch = response.json()
            batch_id = batch['id']
            print(f"✅ Query submitted, batch ID: {batch_id}")
            
            # Wait for results
            time.sleep(2)
            
            # Get results
            response = requests.get(f"{base_url}/api/batches/{batch_id}")
            if response.status_code == 200:
                batch_info = response.json()
                if batch_info.get('status') == 'finished':
                    print("✅ Query completed successfully")
                    
                    # Get the actual results
                    statement_id = batch_info.get('statements', [{}])[0].get('id')
                    if statement_id:
                        response = requests.get(f"{base_url}/api/statements/{statement_id}/results")
                        if response.status_code == 200:
                            results = response.json()
                            print(f"✅ Query results: {results}")
                            return True
                        else:
                            print(f"❌ Failed to get results: {response.status_code}")
                else:
                    print(f"❌ Query failed: {batch_info.get('status')}")
            else:
                print(f"❌ Failed to get batch status: {response.status_code}")
        else:
            print(f"❌ Failed to submit query: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing query: {e}")
        return False
    
    return False

if __name__ == "__main__":
    print("🚀 SQLPad Connection Test")
    print("=" * 40)
    
    success = test_sqlpad_connection()
    
    if success:
        print("\n🎉 SQLPad is properly connected to Heroku database!")
        print("You can now access it at: http://localhost:3000")
        print("Login with: admin@7taps.com / admin123")
    else:
        print("\n❌ SQLPad connection test failed")
        print("Check the configuration and try again")
