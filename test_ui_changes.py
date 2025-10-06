#!/usr/bin/env python3
"""
UI Change Validation Script
Tests UI changes locally before deployment to catch issues early.
"""

import os
import sys
import subprocess
import time
import requests
from pathlib import Path

def test_favicon_exists():
    """Test that favicon file exists and has content."""
    print("🔍 Testing favicon...")
    
    favicon_path = Path("app/static/favicon.ico")
    if not favicon_path.exists():
        print("❌ Favicon file missing")
        return False
    
    if favicon_path.stat().st_size == 0:
        print("❌ Favicon file is empty")
        return False
    
    print(f"✅ Favicon exists ({favicon_path.stat().st_size} bytes)")
    return True

def test_static_files_served():
    """Test that static files are served correctly."""
    print("🔍 Testing static file serving...")
    
    try:
        # Start local server in background
        print("🚀 Starting local server...")
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "app.main:app", 
            "--host", "127.0.0.1", "--port", "8001"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for server to start
        time.sleep(5)
        
        # Test favicon endpoint
        response = requests.get("http://127.0.0.1:8001/static/favicon.ico", timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Favicon served correctly ({len(response.content)} bytes)")
            favicon_ok = True
        else:
            print(f"❌ Favicon not served (status: {response.status_code})")
            favicon_ok = False
        
        # Test data explorer page
        response = requests.get("http://127.0.0.1:8001/ui/data-explorer", timeout=10)
        
        if response.status_code == 200:
            print("✅ Data explorer page loads")
            page_ok = True
            
            # Check if favicon link is in HTML
            if 'href="/static/favicon.ico"' in response.text:
                print("✅ Favicon link found in HTML")
                link_ok = True
            else:
                print("❌ Favicon link missing from HTML")
                link_ok = False
        else:
            print(f"❌ Data explorer page failed (status: {response.status_code})")
            page_ok = False
            link_ok = False
        
        # Clean up
        process.terminate()
        process.wait()
        
        return favicon_ok and page_ok and link_ok
        
    except Exception as e:
        print(f"❌ Static file test failed: {e}")
        return False

def test_hover_functionality():
    """Test that hover tooltips are properly implemented."""
    print("🔍 Testing hover functionality...")
    
    try:
        # Check if hover tooltip HTML is in the template
        template_path = Path("templates/data_explorer_modern.html")
        
        if not template_path.exists():
            print("❌ Data explorer template missing")
            return False
        
        content = template_path.read_text()
        
        # Check for hover tooltip elements
        checks = [
            ('group-hover:opacity-100', 'Hover opacity transition'),
            ('absolute bottom-full', 'Tooltip positioning'),
            ('bg-gray-800 text-white', 'Tooltip styling'),
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
        
    except Exception as e:
        print(f"❌ Hover functionality test failed: {e}")
        return False

def test_timezone_formatting():
    """Test that timezone formatting is implemented."""
    print("🔍 Testing timezone formatting...")
    
    try:
        template_path = Path("templates/data_explorer_modern.html")
        content = template_path.read_text()
        
        # Check for CST instead of UTC
        if 'CST' in content and 'UTC' not in content:
            print("✅ Timezone changed to CST")
            return True
        elif 'UTC' in content:
            print("❌ Still showing UTC instead of CST")
            return False
        else:
            print("⚠️ No timezone indicators found")
            return False
            
    except Exception as e:
        print(f"❌ Timezone test failed: {e}")
        return False

def main():
    """Run all UI validation tests."""
    print("🧪 UI Change Validation Tests")
    print("=" * 40)
    
    tests = [
        test_favicon_exists,
        test_static_files_served,
        test_hover_functionality,
        test_timezone_formatting,
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
    
    print("📊 Test Results:")
    print(f"✅ Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Safe to deploy.")
        return True
    else:
        print("⚠️ Some tests failed. Fix issues before deploying.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
