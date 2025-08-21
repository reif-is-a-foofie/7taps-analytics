#!/usr/bin/env python3
"""
Test script for the new public API endpoints.
"""

import requests
import json
from datetime import datetime

def test_public_api_endpoints():
    """Test the public API endpoints."""
    base_url = "http://localhost:8000"
    
    print("Testing Public API Endpoints...")
    print("=" * 50)
    
    # Test health endpoint
    print("\n1. Testing /api/public/health")
    try:
        response = requests.get(f"{base_url}/api/public/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed")
            print(f"   Status: {data['data']['status']}")
            print(f"   Database connected: {data['data']['database_connected']}")
            print(f"   Data validation: {data['data']['data_validation']}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {e}")
    
    # Test metrics overview
    print("\n2. Testing /api/public/metrics/overview")
    try:
        response = requests.get(f"{base_url}/api/public/metrics/overview")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Metrics overview retrieved")
            print(f"   Total users: {data['data']['total_users']}")
            print(f"   Total activities: {data['data']['total_activities']}")
            print(f"   Total responses: {data['data']['total_responses']}")
            print(f"   Platform health: {data['data']['platform_health']}")
        else:
            print(f"❌ Metrics overview failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Metrics overview error: {e}")
    
    # Test lesson completion analytics
    print("\n3. Testing /api/public/analytics/lesson-completion")
    try:
        response = requests.get(f"{base_url}/api/public/analytics/lesson-completion")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Lesson completion analytics retrieved")
            print(f"   Total lessons: {data['data']['summary']['total_lessons']}")
            print(f"   Average completion rate: {data['data']['summary']['average_completion_rate']}%")
            if data['data']['lessons']:
                print(f"   Sample lesson: {data['data']['lessons'][0]}")
        else:
            print(f"❌ Lesson completion analytics failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Lesson completion analytics error: {e}")
    
    # Test user engagement analytics
    print("\n4. Testing /api/public/analytics/user-engagement")
    try:
        response = requests.get(f"{base_url}/api/public/analytics/user-engagement")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ User engagement analytics retrieved")
            print(f"   Total users: {data['data']['engagement_summary']['total_users']}")
            print(f"   Total activities: {data['data']['engagement_summary']['total_activities']}")
            print(f"   Engagement categories: {data['data']['engagement_summary']['engagement_categories']}")
        else:
            print(f"❌ User engagement analytics failed: {response.status_code}")
    except Exception as e:
        print(f"❌ User engagement analytics error: {e}")
    
    # Test sample data
    print("\n5. Testing /api/public/data/sample")
    try:
        response = requests.get(f"{base_url}/api/public/data/sample")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Sample data retrieved")
            print(f"   Sample users: {len(data['data']['sample_users'])}")
            print(f"   Sample activities: {len(data['data']['sample_activities'])}")
            print(f"   Sample responses: {len(data['data']['sample_responses'])}")
            print(f"   Data quality: {data['data']['data_quality']['validation_status']}")
        else:
            print(f"❌ Sample data failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Sample data error: {e}")
    
    print("\n" + "=" * 50)
    print("Public API Testing Complete!")

if __name__ == "__main__":
    test_public_api_endpoints()
