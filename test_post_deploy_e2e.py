#!/usr/bin/env python3
"""
Post-Deploy E2E Testing Script
Tests the live production site after deployment to catch real-world issues.
"""

import requests
import time
import sys
from pathlib import Path

# Configuration
PROJECT_URL = "https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app"
TIMEOUT = 30
MAX_RETRIES = 3

def wait_for_deployment():
    """Wait for deployment to be ready."""
    print("⏳ Waiting for deployment to be ready...")
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(f"{PROJECT_URL}/health", timeout=10)
            if response.status_code == 200:
                print("✅ Deployment is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        print(f"   Attempt {attempt + 1}/{MAX_RETRIES} - waiting...")
        time.sleep(10)
    
    print("❌ Deployment not ready after maximum retries")
    return False

def test_favicon_served():
    """Test that favicon is served correctly."""
    print("🔍 Testing favicon serving...")
    
    try:
        response = requests.get(f"{PROJECT_URL}/static/favicon.ico", timeout=TIMEOUT)
        
        if response.status_code == 200:
            content_length = len(response.content)
            if content_length > 0:
                print(f"✅ Favicon served correctly ({content_length} bytes)")
                return True
            else:
                print("❌ Favicon served but empty")
                return False
        else:
            print(f"❌ Favicon not served (status: {response.status_code})")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Favicon test failed: {e}")
        return False

def test_data_explorer_page():
    """Test that data explorer page loads correctly."""
    print("🔍 Testing data explorer page...")
    
    try:
        response = requests.get(f"{PROJECT_URL}/ui/data-explorer", timeout=TIMEOUT)
        
        if response.status_code == 200:
            content = response.text
            
            # Check for key elements
            checks = [
                ('Data Explorer', 'Page title'),
                ('Recent Events', 'Events section'),
                ('CST', 'Central Time display'),
                ('href="/static/favicon.ico"', 'Favicon link'),
                ('group-hover:opacity-100', 'Hover functionality'),
                ('copyToClipboard', 'Copy functionality'),
            ]
            
            all_good = True
            for check, description in checks:
                if check in content:
                    print(f"✅ {description} found")
                else:
                    print(f"❌ {description} missing")
                    all_good = False
            
            return all_good
        else:
            print(f"❌ Data explorer page failed (status: {response.status_code})")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Data explorer test failed: {e}")
        return False

def test_hover_functionality():
    """Test that hover tooltips work (check HTML structure)."""
    print("🔍 Testing hover functionality...")
    
    try:
        response = requests.get(f"{PROJECT_URL}/ui/data-explorer", timeout=TIMEOUT)
        content = response.text
        
        # Check for hover tooltip implementation
        checks = [
            ('relative group', 'Hover group container'),
            ('group-hover:opacity-100', 'Hover trigger'),
            ('absolute bottom-full', 'Tooltip positioning'),
            ('bg-gray-800 text-white', 'Tooltip styling'),
            ('cursor-pointer', 'Clickable styling'),
        ]
        
        all_good = True
        for check, description in checks:
            if check in content:
                print(f"✅ {description} found")
            else:
                print(f"❌ {description} missing")
                all_good = False
        
        return all_good
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Hover functionality test failed: {e}")
        return False

def test_timezone_display():
    """Test that timestamps show CST not UTC."""
    print("🔍 Testing timezone display...")
    
    try:
        response = requests.get(f"{PROJECT_URL}/ui/data-explorer", timeout=TIMEOUT)
        content = response.text
        
        # Check for CST display and absence of UTC
        if 'CST' in content:
            print("✅ CST timezone found")
            cst_found = True
        else:
            print("❌ CST timezone not found")
            cst_found = False
        
        if 'UTC' not in content:
            print("✅ No UTC timezone found")
            no_utc = True
        else:
            print("❌ UTC timezone still present")
            no_utc = False
        
        return cst_found and no_utc
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Timezone test failed: {e}")
        return False

def test_user_id_display():
    """Test that user IDs are displayed correctly."""
    print("🔍 Testing user ID display...")
    
    try:
        response = requests.get(f"{PROJECT_URL}/ui/data-explorer", timeout=TIMEOUT)
        content = response.text
        
        # Check for truncated user IDs with hover functionality
        if '70ce7a5e298f' in content or '...' in content:
            print("✅ User ID truncation found")
            truncation_found = True
        else:
            print("❌ User ID truncation not found")
            truncation_found = False
        
        # Check for hover tooltip with full ID
        if 'title=' in content and 'actor_id' in content:
            print("✅ User ID hover tooltip found")
            tooltip_found = True
        else:
            print("❌ User ID hover tooltip not found")
            tooltip_found = False
        
        return truncation_found and tooltip_found
        
    except requests.exceptions.RequestException as e:
        print(f"❌ User ID test failed: {e}")
        return False

def test_api_endpoints():
    """Test that key API endpoints respond."""
    print("🔍 Testing API endpoints...")
    
    endpoints = [
        ("/health", "Health check"),
        ("/api/status", "Status API"),
    ]
    
    all_good = True
    for endpoint, description in endpoints:
        try:
            response = requests.get(f"{PROJECT_URL}{endpoint}", timeout=TIMEOUT)
            if response.status_code == 200:
                print(f"✅ {description} responding")
            else:
                print(f"❌ {description} failed (status: {response.status_code})")
                all_good = False
        except requests.exceptions.RequestException as e:
            print(f"❌ {description} failed: {e}")
            all_good = False
    
    return all_good

def main():
    """Run all post-deploy E2E tests."""
    print("🧪 Post-Deploy E2E Testing")
    print("=" * 40)
    print(f"🌐 Testing: {PROJECT_URL}")
    print()
    
    # Wait for deployment to be ready
    if not wait_for_deployment():
        print("❌ Deployment not ready - aborting tests")
        return False
    
    print()
    
    # Run all tests
    tests = [
        test_favicon_served,
        test_data_explorer_page,
        test_hover_functionality,
        test_timezone_display,
        test_user_id_display,
        test_api_endpoints,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            print()
        except Exception as e:
            print(f"❌ Test {test.__name__} failed: {e}")
            results.append(False)
            print()
    
    passed = sum(results)
    total = len(results)
    
    print("📊 E2E Test Results:")
    print(f"✅ Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All E2E tests passed! Production deployment is working correctly.")
        return True
    else:
        print("⚠️ Some E2E tests failed. Production deployment has issues.")
        print("\n💡 Common fixes:")
        print("   • Check Cloud Run logs: gcloud logs read --service=taps-analytics-ui")
        print("   • Verify environment variables are set correctly")
        print("   • Check if static files are being served")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
