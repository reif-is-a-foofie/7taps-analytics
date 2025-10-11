#!/usr/bin/env python3
"""End-to-end production readiness tests."""

import requests
from datetime import datetime, timedelta
import json

BASE_URL = "https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app"
AUTH = ("7taps.team", "PracticeofLife")

def test_health():
    """Test 1: System health check."""
    print("\n" + "="*60)
    print("TEST 1: System Health")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 200, "Health check failed"
    assert response.json()["status"] == "healthy", "System unhealthy"
    print("✅ PASS - System is healthy")

def test_xapi_ingestion():
    """Test 2: xAPI statement ingestion (7taps integration)."""
    print("\n" + "="*60)
    print("TEST 2: xAPI Ingestion (7taps Integration)")
    print("="*60)
    
    statement = {
        "actor": {
            "mbox": "mailto:e2e-test@practiceoflife.com",
            "name": "E2E Test User"
        },
        "verb": {
            "id": "http://adlnet.gov/expapi/verbs/completed",
            "display": {"en-US": "completed"}
        },
        "object": {
            "id": "https://courses.practiceoflife.com/BppNeFkyEYF9",
            "definition": {
                "name": {"en-US": "You're Here. Start Strong"},
                "description": {"en-US": "Lesson 1 - Test"}
            }
        },
        "context": {
            "platform": "e2e-test-group",
            "extensions": {
                "https://7taps.com/lesson-number": "1",
                "https://7taps.com/lesson-name": "You're Here. Start Strong"
            }
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/statements",
        auth=AUTH,
        json=statement,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 200, "Statement ingestion failed"
    assert response.json()["status"] == "success", "Statement not queued"
    print("✅ PASS - xAPI ingestion working")

def test_dashboard_ui():
    """Test 3: Dashboard loads."""
    print("\n" + "="*60)
    print("TEST 3: Dashboard UI")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/ui/dashboard")
    print(f"Status: {response.status_code}")
    print(f"Content length: {len(response.text)} bytes")
    
    assert response.status_code == 200, "Dashboard failed to load"
    assert "POL Analytics" in response.text, "Dashboard missing content"
    print("✅ PASS - Dashboard loads correctly")

def test_daily_analytics_ui():
    """Test 4: Daily Analytics dashboard."""
    print("\n" + "="*60)
    print("TEST 4: Daily Analytics UI")
    print("="*60)
    
    today = datetime.now().strftime("%Y-%m-%d")
    response = requests.get(f"{BASE_URL}/ui/daily-analytics?target_date={today}")
    
    print(f"Status: {response.status_code}")
    print(f"Content length: {len(response.text)} bytes")
    
    assert response.status_code == 200, "Daily Analytics failed to load"
    assert "Daily Course Analytics" in response.text, "Daily Analytics missing content"
    print("✅ PASS - Daily Analytics loads correctly")

def test_flagged_content_ui():
    """Test 5: Flagged Content dashboard."""
    print("\n" + "="*60)
    print("TEST 5: Flagged Content UI")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/ui/flagged-content")
    
    print(f"Status: {response.status_code}")
    print(f"Content length: {len(response.text)} bytes")
    
    assert response.status_code == 200, "Flagged Content failed to load"
    assert "Flagged Content" in response.text, "Flagged Content missing title"
    print("✅ PASS - Flagged Content loads correctly")

def test_daily_progress_api():
    """Test 6: Daily progress API endpoint."""
    print("\n" + "="*60)
    print("TEST 6: Daily Progress API")
    print("="*60)
    
    today = datetime.now().strftime("%Y-%m-%d")
    response = requests.get(f"{BASE_URL}/api/daily-progress/data?date={today}")
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response keys: {list(data.keys())}")
    
    assert response.status_code == 200, "Daily progress API failed"
    print("✅ PASS - Daily progress API working")

def test_api_docs():
    """Test 7: API documentation accessible."""
    print("\n" + "="*60)
    print("TEST 7: API Documentation")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/api/docs")
    
    print(f"Status: {response.status_code}")
    print(f"Content length: {len(response.text)} bytes")
    
    assert response.status_code == 200, "API docs failed to load"
    assert "POL Analytics" in response.text, "API docs missing content"
    print("✅ PASS - API documentation accessible")

def test_flagged_words_api():
    """Test 8: Flagged words management API."""
    print("\n" + "="*60)
    print("TEST 8: Flagged Words Management")
    print("="*60)
    
    # Get current flagged words
    response = requests.get(f"{BASE_URL}/api/trigger-words")
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Current flagged words: {data.get('total_count', 0)}")
    
    assert response.status_code == 200, "Flagged words API failed"
    assert data.get("success") == True, "Flagged words query failed"
    print("✅ PASS - Flagged words API working")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("POL ANALYTICS - END-TO-END PRODUCTION TESTS")
    print("="*60)
    print(f"Target: {BASE_URL}")
    print(f"Time: {datetime.now()}")
    
    tests = [
        test_health,
        test_xapi_ingestion,
        test_dashboard_ui,
        test_daily_analytics_ui,
        test_flagged_content_ui,
        test_daily_progress_api,
        test_api_docs,
        test_flagged_words_api
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ FAIL - {e}")
            failed += 1
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/len(tests)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED - READY FOR PRODUCTION")
    else:
        print(f"\n⚠️  {failed} TEST(S) FAILED - FIX BEFORE GOING LIVE")
        exit(1)


