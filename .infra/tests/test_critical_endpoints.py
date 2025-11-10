#!/usr/bin/env python3
"""
Critical Endpoints Test Suite
Verifies that critical endpoints work and non-critical endpoints are removed.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_removed_endpoints():
    """Test that API docs and chat endpoints are removed."""
    print("🔍 Testing removed endpoints...")
    
    main_py = project_root / "app" / "main.py"
    content = main_py.read_text()
    
    removed_patterns = [
        ('docs_url="/api/docs"', 'API docs URL'),
        ('redoc_url="/api/redoc"', 'ReDoc URL'),
        ('@app.get("/chat"', 'Chat UI endpoint'),
        ('@app.post("/api/chat"', 'Chat API endpoint'),
        ('@app.get("/docs"', 'Docs endpoint'),
        ('@app.get("/api-docs"', 'API docs endpoint'),
    ]
    
    all_removed = True
    for pattern, description in removed_patterns:
        if pattern in content:
            print(f"❌ {description} still exists")
            all_removed = False
        else:
            print(f"✅ {description} removed")
    
    return all_removed

def test_critical_endpoints_exist():
    """Test that critical endpoints are defined."""
    print("\n🔍 Testing critical endpoints exist...")
    
    main_py = project_root / "app" / "main.py"
    content = main_py.read_text()
    
    critical_patterns = [
        ('@app.get("/health"', 'Health check endpoint'),
        ('@app.get("/api/health"', 'API health endpoint'),
        ('app.include_router(xapi_router', 'xAPI router'),
        ('app.include_router(seventaps_router', '7taps router'),
        ('app.include_router(daily_analytics_router', 'Daily analytics router'),
        ('app.include_router(safety_router', 'Safety router'),
        ('app.include_router(pubsub_feed_router', 'Data explorer router'),
        ('app.include_router(cohort_api_router', 'Cohort API router'),
    ]
    
    all_exist = True
    for pattern, description in critical_patterns:
        if pattern in content:
            print(f"✅ {description} exists")
        else:
            print(f"❌ {description} missing")
            all_exist = False
    
    return all_exist

def test_ui_templates_no_api_docs():
    """Test that UI templates don't link to API docs."""
    print("\n🔍 Testing UI templates (no API docs links)...")
    
    templates_to_check = [
        "app/templates/data_explorer_modern.html",
        "app/templates/safety_dashboard_simple.html",
        "app/templates/daily_progress_working.html",
        "app/templates/daily_analytics.html",
    ]
    
    all_clean = True
    for template_path in templates_to_check:
        path = project_root / template_path
        if not path.exists():
            print(f"⚠️ Template {template_path} not found")
            continue
        
        content = path.read_text()
        
        # Check for removed links
        removed_links = [
            ('/api/docs', 'API docs link'),
            ('/api-docs', 'API docs link'),
            ('/chat', 'Chat link'),
        ]
        
        for link, description in removed_links:
            if link in content:
                print(f"❌ {description} found in {template_path}")
                all_clean = False
        
        if all_clean:
            print(f"✅ {template_path} clean (no API docs/chat links)")
    
    return all_clean

def test_cohort_filtering_implemented():
    """Test that cohort filtering is properly implemented."""
    print("\n🔍 Testing cohort filtering implementation...")
    
    cohort_filtering = project_root / "app" / "utils" / "cohort_filtering.py"
    cohort_api = project_root / "app" / "api" / "cohort_api.py"
    
    all_exist = True
    
    if cohort_filtering.exists():
        content = cohort_filtering.read_text()
        if "build_cohort_filter_sql" in content:
            print("✅ Cohort filtering utility exists with SQL builder")
        else:
            print("❌ Cohort SQL builder function missing")
            all_exist = False
        if "get_all_available_cohorts" in content:
            print("✅ Get cohorts function exists")
        else:
            print("❌ Get cohorts function missing")
            all_exist = False
    else:
        print("❌ Cohort filtering utility missing")
        all_exist = False
    
    if cohort_api.exists():
        print("✅ Cohort API endpoint exists")
    else:
        print("❌ Cohort API endpoint missing")
        all_exist = False
    
    return all_exist

def test_fastapi_config():
    """Test that FastAPI is configured without docs."""
    print("\n🔍 Testing FastAPI configuration...")
    
    main_py = project_root / "app" / "main.py"
    content = main_py.read_text()
    
    # Check that docs are disabled
    if 'docs_url=None' in content and 'redoc_url=None' in content:
        print("✅ FastAPI docs disabled")
        return True
    else:
        print("❌ FastAPI docs still enabled")
        return False

def test_middleware_updated():
    """Test that middleware excludes API docs paths."""
    print("\n🔍 Testing middleware configuration...")
    
    middleware_py = project_root / "app" / "middleware" / "request_tracking.py"
    if not middleware_py.exists():
        print("⚠️ Middleware file not found")
        return False
    
    content = middleware_py.read_text()
    
    # Check that API docs paths are removed from exclusions
    if '/redoc' not in content and '/openapi.json' not in content:
        print("✅ Middleware updated (API docs paths removed)")
        return True
    else:
        print("❌ Middleware still includes API docs paths")
        return False

def main():
    """Run all critical endpoint tests."""
    print("🧪 Critical Endpoints Test Suite")
    print("=" * 50)
    
    tests = [
        ("Removed Endpoints", test_removed_endpoints),
        ("Critical Endpoints", test_critical_endpoints_exist),
        ("UI Templates Clean", test_ui_templates_no_api_docs),
        ("Cohort Filtering", test_cohort_filtering_implemented),
        ("FastAPI Config", test_fastapi_config),
        ("Middleware Updated", test_middleware_updated),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Test '{name}' failed with error: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    passed = sum(results)
    total = len(results)
    
    for i, (name, _) in enumerate(tests):
        status = "✅" if results[i] else "❌"
        print(f"{status} {name}")
    
    print(f"\n✅ Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All critical endpoint tests passed!")
        return True
    else:
        print("⚠️ Some tests failed. Review the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

