#!/usr/bin/env python3
"""
Simple test script for the updated dashboard
"""

import requests
import json
from datetime import datetime

def test_dashboard():
    """Test the updated dashboard functionality"""
    
    # Test the main dashboard endpoint
    try:
        print("🧪 Testing Dashboard...")
        
        # Test the main dashboard
        response = requests.get("https://seventaps-analytics-5135b3a0701a.herokuapp.com/", timeout=30)
        
        if response.status_code == 200:
            print("✅ Dashboard loads successfully")
            
            # Check for key elements in the HTML
            content = response.text
            
            # Check for generalized header
            if "Analytics Dashboard" in content:
                print("✅ Generalized header found")
            else:
                print("❌ Generalized header not found")
                
            # Check for statistics sections
            if "Total Users" in content and "User Activities" in content:
                print("✅ Statistics sections found")
            else:
                print("❌ Statistics sections missing")
                
            # Check for interactive charts
            if "completion-chart" in content and "trends-chart" in content:
                print("✅ Interactive charts found")
            else:
                print("❌ Interactive charts missing")
                
            # Check for insights section
            if "Key Insights" in content:
                print("✅ Key insights section found")
            else:
                print("❌ Key insights section missing")
                
            # Check for navigation links
            if "Admin Panel" in content and "Data Explorer" in content:
                print("✅ Navigation links found")
            else:
                print("❌ Navigation links missing")
                
        else:
            print(f"❌ Dashboard failed to load: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing dashboard: {e}")
    
    # Test health endpoint
    try:
        print("\n🧪 Testing Health Endpoint...")
        response = requests.get("https://seventaps-analytics-5135b3a0701a.herokuapp.com/health", timeout=10)
        
        if response.status_code == 200:
            print("✅ Health endpoint working")
            health_data = response.json()
            print(f"   Status: {health_data.get('status', 'unknown')}")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing health endpoint: {e}")
    
    # Test API endpoint
    try:
        print("\n🧪 Testing API Endpoint...")
        response = requests.get("https://seventaps-analytics-5135b3a0701a.herokuapp.com/api", timeout=10)
        
        if response.status_code == 200:
            print("✅ API endpoint working")
            api_data = response.json()
            print(f"   Title: {api_data.get('title', 'unknown')}")
            print(f"   Status: {api_data.get('status', 'unknown')}")
        else:
            print(f"❌ API endpoint failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing API endpoint: {e}")

def test_database_connection():
    """Test database connection through the dashboard"""
    try:
        print("\n🧪 Testing Database Connection...")
        
        # Test the test-db endpoint
        response = requests.get("https://seventaps-analytics-5135b3a0701a.herokuapp.com/test-db", timeout=30)
        
        if response.status_code == 200:
            print("✅ Database connection test successful")
            db_data = response.json()
            
            if db_data.get('status') == 'success':
                print(f"   Database: {db_data.get('database', 'unknown')}")
                print(f"   Lessons: {db_data.get('lessons', 0)}")
                print(f"   Users: {db_data.get('users', 0)}")
                print(f"   Responses: {db_data.get('responses', 0)}")
            else:
                print(f"   Database error: {db_data.get('error', 'unknown')}")
        else:
            print(f"❌ Database test failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing database connection: {e}")

if __name__ == "__main__":
    print("🚀 Starting Dashboard Tests...")
    print("=" * 50)
    
    test_dashboard()
    test_database_connection()
    
    print("\n" + "=" * 50)
    print("🏁 Dashboard Tests Complete!")
