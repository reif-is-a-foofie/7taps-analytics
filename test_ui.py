#!/usr/bin/env python3
"""
Simple UI test script to validate dashboard functionality
"""
import requests
import time
from bs4 import BeautifulSoup

BASE_URL = "https://seventaps-analytics-5135b3a0701a.herokuapp.com"

def test_dashboard_loads():
    """Test that dashboard loads with real data"""
    print("🔍 Testing dashboard loads with real data...")
    
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200, f"Dashboard failed to load: {response.status_code}"
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Check title
    title = soup.find('h1')
    assert title and '7taps HR Analytics Explorer' in title.text, "Title not found"
    
    # Check real data is displayed
    total_participants = soup.find(id='total-participants')
    assert total_participants and '21' in total_participants.text, "Total participants not showing real data"
    
    # Check no mock data
    page_text = soup.get_text()
    assert '65% of learners use mobile devices' not in page_text, "Mock data still present"
    assert '25% reduction in screen time' not in page_text, "Mock data still present"
    
    print("✅ Dashboard loads with real data")

def test_api_endpoints():
    """Test API endpoints work"""
    print("🔍 Testing API endpoints...")
    
    # Test health endpoint
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200, f"Health endpoint failed: {response.status_code}"
    data = response.json()
    assert data['status'] == 'healthy', f"Health status not healthy: {data}"
    
    # Test chat endpoint
    response = requests.post(f"{BASE_URL}/api/chat", 
                           json={"message": "test", "history": []})
    assert response.status_code == 200, f"Chat endpoint failed: {response.status_code}"
    data = response.json()
    assert 'response' in data, "Chat response missing"
    
    # Test API docs
    response = requests.get(f"{BASE_URL}/docs")
    assert response.status_code == 200, f"API docs failed: {response.status_code}"
    assert 'Swagger UI' in response.text, "API docs not loading"
    
    print("✅ API endpoints working")

def test_data_explorer():
    """Test data explorer functionality"""
    print("🔍 Testing data explorer...")
    
    # Test lessons endpoint
    response = requests.get(f"{BASE_URL}/api/data-explorer/lessons")
    assert response.status_code == 200, f"Lessons endpoint failed: {response.status_code}"
    data = response.json()
    assert data['success'], f"Lessons endpoint error: {data}"
    assert len(data['lessons']) > 0, "No lessons returned"
    
    # Test users endpoint
    response = requests.get(f"{BASE_URL}/api/data-explorer/users")
    assert response.status_code == 200, f"Users endpoint failed: {response.status_code}"
    data = response.json()
    assert data['success'], f"Users endpoint error: {data}"
    assert len(data['users']) > 0, "No users returned"
    
    print("✅ Data explorer endpoints working")

def test_charts_data():
    """Test that charts have real data"""
    print("🔍 Testing charts have real data...")
    
    response = requests.get(f"{BASE_URL}/")
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Check that chart data is passed to JavaScript
    script_tags = soup.find_all('script')
    chart_data_found = False
    
    for script in script_tags:
        if script.string and 'lessonNames' in script.string:
            # Check for real data
            if '"You\'re Here. Start Strong"' in script.string:
                chart_data_found = True
                break
    
    assert chart_data_found, "Chart data not found in JavaScript"
    
    # Check chart containers exist
    chart_containers = [
        'completion-funnel-chart',
        'dropoff-chart', 
        'knowledge-lift-chart',
        'quiz-performance-chart'
    ]
    
    for container_id in chart_containers:
        container = soup.find(id=container_id)
        assert container, f"Chart container {container_id} not found"
    
    print("✅ Charts have real data")

def main():
    """Run all tests"""
    print("🚀 Starting UI Tests...")
    print("=" * 50)
    
    try:
        test_dashboard_loads()
        test_api_endpoints()
        test_data_explorer()
        test_charts_data()
        
        print("=" * 50)
        print("🎉 ALL TESTS PASSED!")
        print("✅ Dashboard is ready for demo")
        
    except Exception as e:
        print("=" * 50)
        print(f"❌ TEST FAILED: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()
