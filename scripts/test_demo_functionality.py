#!/usr/bin/env python3
"""
Test script to verify all demo functionality is working properly.
Run this before the demo to ensure everything is operational.
"""

import requests
import json
import sys

BASE_URL = "https://seventaps-analytics-5135b3a0701a.herokuapp.com"

def test_endpoint(endpoint, expected_status=200, description=""):
    """Test an endpoint and return success/failure"""
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        if response.status_code == expected_status:
            print(f"✅ {description or endpoint}: OK")
            return True
        else:
            print(f"❌ {description or endpoint}: Failed (Status: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ {description or endpoint}: Error - {str(e)}")
        return False

def test_api_endpoint(endpoint, expected_status=200, description=""):
    """Test an API endpoint and return success/failure"""
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        if response.status_code == expected_status:
            data = response.json()
            print(f"✅ {description or endpoint}: OK")
            if 'success' in data:
                print(f"   └─ Success: {data['success']}")
            return True
        else:
            print(f"❌ {description or endpoint}: Failed (Status: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ {description or endpoint}: Error - {str(e)}")
        return False

def main():
    print("🚀 Testing 7taps Analytics Demo Functionality")
    print("=" * 50)
    
    tests = [
        # Core endpoints
        ("/health", 200, "Health Check"),
        ("/", 200, "Main Dashboard"),
        ("/docs", 200, "API Documentation"),
        
        # Data Explorer APIs
        ("/api/data-explorer/lessons", 200, "Lessons API"),
        ("/api/data-explorer/users", 200, "Users API"),
        ("/api/data-explorer/table/user_responses", 200, "User Responses Table"),
        ("/api/data-explorer/table/lessons", 200, "Lessons Table"),
        
        # xAPI endpoints
        ("/api/xapi/ingest", 405, "xAPI Ingestion (POST only)"),
        ("/statements", 405, "7taps xAPI Statements (POST only)"),
        
        # Chat API
        ("/api/chat", 405, "AI Chat API (POST only)"),
    ]
    
    passed = 0
    total = len(tests)
    
    for endpoint, expected_status, description in tests:
        if test_api_endpoint(endpoint, expected_status, description):
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Demo is ready.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
