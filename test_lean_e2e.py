#!/usr/bin/env python3
"""
Lean E2E Testing - Minimal tests for lean deployment
Tests only essential functionality.
"""

import requests
import time
import sys

PROJECT_URL = "https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app"
TIMEOUT = 10

def test_lean_endpoints():
    """Test only essential endpoints."""
    print("🧪 Testing Lean Endpoints")
    print("=" * 30)
    
    tests_passed = 0
    total_tests = 4
    
    # Test 1: Health check
    try:
        response = requests.get(f"{PROJECT_URL}/api/health", timeout=TIMEOUT)
        if response.status_code == 200:
            print("✅ Health check passed")
            tests_passed += 1
        else:
            print("❌ Health check failed")
    except Exception as e:
        print(f"❌ Health check error: {e}")
    
    # Test 2: Data explorer page loads
    try:
        response = requests.get(f"{PROJECT_URL}/ui/data-explorer", timeout=TIMEOUT)
        if response.status_code == 200 and "data-explorer" in response.text.lower():
            print("✅ Data explorer page loads")
            tests_passed += 1
        else:
            print("❌ Data explorer page failed")
    except Exception as e:
        print(f"❌ Data explorer error: {e}")
    
    # Test 3: Safety dashboard loads
    try:
        response = requests.get(f"{PROJECT_URL}/ui/safety", timeout=TIMEOUT)
        if response.status_code == 200:
            print("✅ Safety dashboard loads")
            tests_passed += 1
        else:
            print("❌ Safety dashboard failed")
    except Exception as e:
        print(f"❌ Safety dashboard error: {e}")
    
    # Test 4: AI service integration
    try:
        response = requests.post(
            f"{PROJECT_URL}/api/ai-content/analyze",
            json={"content": "I feel great today", "context": "general"},
            timeout=TIMEOUT
        )
        if response.status_code == 200:
            print("✅ AI service integration works")
            tests_passed += 1
        else:
            print("❌ AI service integration failed")
    except Exception as e:
        print(f"❌ AI service error: {e}")
    
    print(f"\n📊 Lean E2E Results: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("🎉 All lean tests passed!")
        return True
    else:
        print("❌ Some lean tests failed!")
        return False

if __name__ == "__main__":
    success = test_lean_endpoints()
    sys.exit(0 if success else 1)
