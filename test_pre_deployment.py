#!/usr/bin/env python3
"""
Pre-Deployment Validation Script
Tests changes locally before deployment to catch issues early.
"""

import os
import sys
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

def test_template_favicon_links():
    """Test that favicon links are in templates."""
    print("🔍 Testing favicon links in templates...")
    
    templates_to_check = [
        "templates/base.html",
        "templates/data_explorer_modern.html"
    ]
    
    all_good = True
    for template_path in templates_to_check:
        path = Path(template_path)
        if not path.exists():
            print(f"❌ Template {template_path} missing")
            all_good = False
            continue
            
        content = path.read_text()
        if 'href="/static/favicon.ico"' in content:
            print(f"✅ Favicon link found in {template_path}")
        else:
            print(f"❌ Favicon link missing from {template_path}")
            all_good = False
    
    return all_good

def test_hover_functionality():
    """Test that hover tooltips are properly implemented."""
    print("🔍 Testing hover functionality...")
    
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

def test_timezone_formatting():
    """Test that timezone formatting is implemented."""
    print("🔍 Testing timezone formatting...")
    
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

def test_backend_timestamp_formatting():
    """Test that backend timestamp formatting is implemented."""
    print("🔍 Testing backend timestamp formatting...")
    
    backend_path = Path("app/ui/pubsub_feed.py")
    
    if not backend_path.exists():
        print("❌ Backend file missing")
        return False
    
    content = backend_path.read_text()
    
    # Check for timestamp formatting imports and usage
    checks = [
        ('from app.utils.timestamp_utils import format_compact', 'Timestamp utils import'),
        ('format_compact(timestamp)', 'Timestamp formatting usage'),
    ]
    
    all_good = True
    for check, description in checks:
        if check in content:
            print(f"✅ {description} found")
        else:
            print(f"❌ {description} missing")
            all_good = False
    
    return all_good

def test_user_id_hover_implementation():
    """Test that user ID hover is properly implemented."""
    print("🔍 Testing user ID hover implementation...")
    
    template_path = Path("templates/data_explorer_modern.html")
    content = template_path.read_text()
    
    # Check for user ID hover implementation
    checks = [
        ('relative group', 'Hover group container'),
        ('group-hover:opacity-100', 'Hover trigger'),
        ('{{ statement.actor_id }}', 'Full ID display in tooltip'),
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

def main():
    """Run all pre-deployment validation tests."""
    print("🧪 Pre-Deployment Validation Tests")
    print("=" * 40)
    
    tests = [
        test_favicon_exists,
        test_template_favicon_links,
        test_hover_functionality,
        test_timezone_formatting,
        test_backend_timestamp_formatting,
        test_user_id_hover_implementation,
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
        print("\n💡 Common fixes:")
        print("   • Download favicon: curl -L -o app/static/favicon.ico https://www.practiceoflife.com/favicon.ico")
        print("   • Check template syntax and indentation")
        print("   • Verify backend imports and function calls")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
