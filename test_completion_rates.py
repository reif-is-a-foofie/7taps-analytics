#!/usr/bin/env python3
"""
Test script to verify completion rate calculations are working correctly.
"""

import requests
import json

def test_completion_rates():
    """Test the completion rate calculations."""
    base_url = "http://localhost:8000"
    
    print("Testing Completion Rate Calculations...")
    print("=" * 50)
    
    # Test dashboard completion rates
    print("\n1. Testing Dashboard Completion Rates")
    try:
        response = requests.get(f"{base_url}/api/dashboard/load")
        if response.status_code == 200:
            data = response.json()
            if data['success'] and 'charts' in data['data']:
                for chart in data['data']['charts']:
                    if chart['type'] == 'lesson_completion':
                        print(f"✅ Dashboard completion rates retrieved")
                        print(f"   Chart title: {chart['title']}")
                        print(f"   Number of lessons: {len(chart['data'])}")
                        
                        # Check for realistic completion rates
                        unrealistic_rates = []
                        for lesson in chart['data']:
                            rate = lesson.get('rate', 0)
                            if rate == 100.0:
                                unrealistic_rates.append(f"{lesson.get('lesson', 'Unknown')}: {rate}%")
                        
                        if unrealistic_rates:
                            print(f"   ⚠️  Found potentially unrealistic rates: {unrealistic_rates}")
                        else:
                            print(f"   ✅ Completion rates look realistic")
                        
                        # Show sample data
                        if chart['data']:
                            sample = chart['data'][0]
                            print(f"   Sample lesson: {sample.get('lesson', 'Unknown')}")
                            print(f"     Started: {sample.get('started', 0)}")
                            print(f"     Completed: {sample.get('completed', 0)}")
                            print(f"     Rate: {sample.get('rate', 0)}%")
        else:
            print(f"❌ Dashboard request failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Dashboard test error: {e}")
    
    # Test public API completion rates
    print("\n2. Testing Public API Completion Rates")
    try:
        response = requests.get(f"{base_url}/api/public/analytics/lesson-completion")
        if response.status_code == 200:
            data = response.json()
            if data['success'] and 'lessons' in data['data']:
                lessons = data['data']['lessons']
                print(f"✅ Public API completion rates retrieved")
                print(f"   Number of lessons: {len(lessons)}")
                
                # Check for realistic completion rates
                unrealistic_rates = []
                for lesson in lessons:
                    rate = lesson.get('completion_rate', 0)
                    if rate == 100.0:
                        unrealistic_rates.append(f"Lesson {lesson.get('lesson_number', 'Unknown')}: {rate}%")
                
                if unrealistic_rates:
                    print(f"   ⚠️  Found potentially unrealistic rates: {unrealistic_rates}")
                else:
                    print(f"   ✅ Completion rates look realistic")
                
                # Show summary
                summary = data['data']['summary']
                print(f"   Summary:")
                print(f"     Total lessons: {summary.get('total_lessons', 0)}")
                print(f"     Total started: {summary.get('total_users_started', 0)}")
                print(f"     Total completed: {summary.get('total_users_completed', 0)}")
                print(f"     Average rate: {summary.get('average_completion_rate', 0)}%")
                
                # Show best and worst performing lessons
                if summary.get('best_performing_lesson'):
                    best = summary['best_performing_lesson']
                    print(f"     Best: Lesson {best.get('lesson_number', 'Unknown')} - {best.get('completion_rate', 0)}%")
                
                if summary.get('worst_performing_lesson'):
                    worst = summary['worst_performing_lesson']
                    print(f"     Worst: Lesson {worst.get('lesson_number', 'Unknown')} - {worst.get('completion_rate', 0)}%")
        else:
            print(f"❌ Public API request failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Public API test error: {e}")
    
    # Test analytics completion rates
    print("\n3. Testing Analytics Completion Rates")
    try:
        response = requests.get(f"{base_url}/api/analytics/completion-rates")
        if response.status_code == 200:
            data = response.json()
            if data['success'] and 'raw_data' in data['data']:
                raw_data = data['data']['raw_data']
                print(f"✅ Analytics completion rates retrieved")
                print(f"   Number of lessons: {len(raw_data)}")
                
                # Check for realistic completion rates
                unrealistic_rates = []
                for lesson in raw_data:
                    rate = lesson.get('completion_rate', 0)
                    if rate == 100.0:
                        unrealistic_rates.append(f"Lesson {lesson.get('lesson_number', 'Unknown')}: {rate}%")
                
                if unrealistic_rates:
                    print(f"   ⚠️  Found potentially unrealistic rates: {unrealistic_rates}")
                else:
                    print(f"   ✅ Completion rates look realistic")
                
                # Show sample data
                if raw_data:
                    sample = raw_data[0]
                    print(f"   Sample lesson: {sample.get('lesson_name', 'Unknown')}")
                    print(f"     Started: {sample.get('users_started', 0)}")
                    print(f"     Completed: {sample.get('users_completed', 0)}")
                    print(f"     Rate: {sample.get('completion_rate', 0)}%")
        else:
            print(f"❌ Analytics request failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Analytics test error: {e}")
    
    print("\n" + "=" * 50)
    print("Completion Rate Testing Complete!")

if __name__ == "__main__":
    test_completion_rates()
