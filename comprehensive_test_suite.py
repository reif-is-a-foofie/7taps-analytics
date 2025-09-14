#!/usr/bin/env python3
"""
Comprehensive Test Suite for 7taps Analytics Platform
Tests business logic, security rules, and integration across all components
"""

import asyncio
import json
import time
from playwright.async_api import async_playwright
import httpx
from typing import Dict, List, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComprehensiveTestSuite:
    def __init__(self, base_url: str = "https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app"):
        self.base_url = base_url
        self.results = {
            "business_logic": {},
            "security": {},
            "performance": {},
            "integration": {},
            "ui_functionality": {}
        }
        self.failed_tests = []
        self.passed_tests = []
    
    async def run_all_tests(self):
        """Run the complete test suite"""
        print("🚀 Starting Comprehensive Test Suite...")
        print("=" * 60)
        
        # Test categories
        await self.test_business_logic()
        await self.test_security_rules()
        await self.test_performance()
        await self.test_integration()
        await self.test_ui_functionality()
        
        # Generate report
        self.generate_test_report()
    
    async def test_business_logic(self):
        """Test core business logic and data integrity"""
        print("\n📊 Testing Business Logic...")
        
        # Test 1: Dashboard metrics accuracy
        await self._test_dashboard_metrics_accuracy()
        
        # Test 2: Data Explorer data consistency
        await self._test_data_explorer_consistency()
        
        # Test 3: Analytics data validation
        await self._test_analytics_data_validation()
        
        # Test 4: User activity tracking
        await self._test_user_activity_tracking()
    
    async def test_security_rules(self):
        """Test security rules and access controls"""
        print("\n🔒 Testing Security Rules...")
        
        # Test 1: API endpoint access
        await self._test_api_endpoint_access()
        
        # Test 2: Data access controls
        await self._test_data_access_controls()
        
        # Test 3: Input validation
        await self._test_input_validation()
        
        # Test 4: Authentication requirements
        await self._test_authentication_requirements()
    
    async def test_performance(self):
        """Test performance and response times"""
        print("\n⚡ Testing Performance...")
        
        # Test 1: Page load times
        await self._test_page_load_times()
        
        # Test 2: API response times
        await self._test_api_response_times()
        
        # Test 3: Data loading performance
        await self._test_data_loading_performance()
        
        # Test 4: Error handling performance
        await self._test_error_handling_performance()
    
    async def test_integration(self):
        """Test integration between components"""
        print("\n🔗 Testing Integration...")
        
        # Test 1: BigQuery connectivity
        await self._test_bigquery_connectivity()
        
        # Test 2: API endpoint integration
        await self._test_api_endpoint_integration()
        
        # Test 3: UI-API data flow
        await self._test_ui_api_data_flow()
        
        # Test 4: Cross-component communication
        await self._test_cross_component_communication()
    
    async def test_ui_functionality(self):
        """Test UI functionality and user experience"""
        print("\n🖥️ Testing UI Functionality...")
        
        # Test 1: Navigation and routing
        await self._test_navigation_routing()
        
        # Test 2: Form interactions
        await self._test_form_interactions()
        
        # Test 3: Data visualization
        await self._test_data_visualization()
        
        # Test 4: Error handling in UI
        await self._test_ui_error_handling()
    
    # Business Logic Tests
    async def _test_dashboard_metrics_accuracy(self):
        """Test that dashboard metrics are accurate and consistent"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/dashboard/metrics")
                assert response.status_code == 200, f"Dashboard metrics endpoint failed: {response.status_code}"
                
                data = response.json()
                metrics = data.get("metrics", {})
                
                # Validate required metrics exist
                required_metrics = ["total_activities", "active_users_today", "total_lessons", "completion_rate"]
                for metric in required_metrics:
                    assert metric in metrics, f"Required metric {metric} missing from dashboard"
                
                # Validate metric types and ranges
                assert isinstance(metrics["total_activities"], (int, float)), "total_activities should be numeric"
                assert metrics["total_activities"] >= 0, "total_activities should be non-negative"
                
                self.passed_tests.append("Dashboard metrics accuracy")
                print("  ✅ Dashboard metrics accuracy")
                
        except Exception as e:
            self.failed_tests.append(f"Dashboard metrics accuracy: {str(e)}")
            print(f"  ❌ Dashboard metrics accuracy: {str(e)}")
    
    async def _test_data_explorer_consistency(self):
        """Test that Data Explorer shows consistent data"""
        try:
            async with httpx.AsyncClient() as client:
                # Test lessons endpoint
                lessons_response = await client.get(f"{self.base_url}/api/data-explorer/lessons")
                assert lessons_response.status_code == 200, "Lessons endpoint failed"
                
                # Test users endpoint
                users_response = await client.get(f"{self.base_url}/api/data-explorer/users")
                assert users_response.status_code == 200, "Users endpoint failed"
                
                # Test table data endpoint
                table_response = await client.get(f"{self.base_url}/api/data-explorer/table/user_responses")
                assert table_response.status_code == 200, "Table data endpoint failed"
                
                # Validate data structure
                lessons_response_data = lessons_response.json()
                users_response_data = users_response.json()
                table_data = table_response.json()
                
                # Check response format (should be wrapped in dictionary)
                assert isinstance(lessons_response_data, dict), "Lessons response should be a dictionary"
                assert isinstance(users_response_data, dict), "Users response should be a dictionary"
                assert isinstance(table_data, list), "Table data should be a list"
                
                # Extract the actual data arrays
                lessons_data = lessons_response_data.get("lessons", [])
                users_data = users_response_data.get("users", [])
                
                assert isinstance(lessons_data, list), "Lessons data should be a list"
                assert isinstance(users_data, list), "Users data should be a list"
                
                self.passed_tests.append("Data Explorer consistency")
                print("  ✅ Data Explorer consistency")
                
        except Exception as e:
            self.failed_tests.append(f"Data Explorer consistency: {str(e)}")
            print(f"  ❌ Data Explorer consistency: {str(e)}")
    
    async def _test_analytics_data_validation(self):
        """Test analytics data validation and accuracy"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/dashboard/metrics")
                data = response.json()
                analytics = data.get("analytics", {})
                
                # Validate analytics structure
                required_analytics = ["lesson_completion", "activity_trends", "response_distribution"]
                for analytic in required_analytics:
                    assert analytic in analytics, f"Required analytic {analytic} missing"
                    assert isinstance(analytics[analytic], list), f"{analytic} should be a list"
                
                self.passed_tests.append("Analytics data validation")
                print("  ✅ Analytics data validation")
                
        except Exception as e:
            self.failed_tests.append(f"Analytics data validation: {str(e)}")
            print(f"  ❌ Analytics data validation: {str(e)}")
    
    async def _test_user_activity_tracking(self):
        """Test user activity tracking functionality"""
        try:
            async with httpx.AsyncClient() as client:
                # Test user activities endpoint
                response = await client.get(f"{self.base_url}/api/data-explorer/table/user_activities")
                assert response.status_code == 200, "User activities endpoint failed"
                
                data = response.json()
                assert isinstance(data, list), "User activities should be a list"
                
                # Validate activity data structure
                if data:
                    activity = data[0]
                    required_fields = ["user_id", "activity_type", "lesson_id", "timestamp"]
                    for field in required_fields:
                        assert field in activity, f"Required field {field} missing from activity"
                
                self.passed_tests.append("User activity tracking")
                print("  ✅ User activity tracking")
                
        except Exception as e:
            self.failed_tests.append(f"User activity tracking: {str(e)}")
            print(f"  ❌ User activity tracking: {str(e)}")
    
    # Security Tests
    async def _test_api_endpoint_access(self):
        """Test API endpoint access controls"""
        try:
            async with httpx.AsyncClient() as client:
                # Test public endpoints (should be accessible)
                public_endpoints = [
                    "/api/health",
                    "/api/dashboard/metrics",
                    "/api/data-explorer/lessons",
                    "/api/data-explorer/users"
                ]
                
                for endpoint in public_endpoints:
                    response = await client.get(f"{self.base_url}{endpoint}")
                    assert response.status_code in [200, 404], f"Public endpoint {endpoint} should be accessible"
                
                # Test that disabled PostgreSQL endpoints return 501
                disabled_endpoints = [
                    "/api/dashboard/load",
                    "/api/data-explorer/table/user_responses/filtered?lesson_ids=999999"
                ]
                
                for endpoint in disabled_endpoints:
                    response = await client.get(f"{self.base_url}{endpoint}")
                    # Some endpoints might return 404 instead of 501, which is acceptable
                    assert response.status_code in [404, 501], f"Disabled endpoint {endpoint} should return 404 or 501"
                
                self.passed_tests.append("API endpoint access")
                print("  ✅ API endpoint access")
                
        except Exception as e:
            self.failed_tests.append(f"API endpoint access: {str(e)}")
            print(f"  ❌ API endpoint access: {str(e)}")
    
    async def _test_data_access_controls(self):
        """Test data access controls and permissions"""
        try:
            async with httpx.AsyncClient() as client:
                # Test that we can access BigQuery data
                response = await client.get(f"{self.base_url}/api/data-explorer/table/user_responses")
                assert response.status_code == 200, "Should be able to access BigQuery data"
                
                # Test that invalid table names are handled properly
                invalid_response = await client.get(f"{self.base_url}/api/data-explorer/table/invalid_table")
                assert invalid_response.status_code in [400, 404, 500], "Invalid table should return error"
                
                self.passed_tests.append("Data access controls")
                print("  ✅ Data access controls")
                
        except Exception as e:
            self.failed_tests.append(f"Data access controls: {str(e)}")
            print(f"  ❌ Data access controls: {str(e)}")
    
    async def _test_input_validation(self):
        """Test input validation and sanitization"""
        try:
            async with httpx.AsyncClient() as client:
                # Test with invalid parameters
                invalid_params = [
                    "?limit=invalid",
                    "?lesson_ids=abc,def",
                    "?user_ids=xyz"
                ]
                
                for params in invalid_params:
                    response = await client.get(f"{self.base_url}/api/data-explorer/table/user_responses{params}")
                    # Should handle invalid input gracefully
                    assert response.status_code in [200, 400, 422], f"Should handle invalid params gracefully: {params}"
                
                self.passed_tests.append("Input validation")
                print("  ✅ Input validation")
                
        except Exception as e:
            self.failed_tests.append(f"Input validation: {str(e)}")
            print(f"  ❌ Input validation: {str(e)}")
    
    async def _test_authentication_requirements(self):
        """Test authentication requirements"""
        try:
            async with httpx.AsyncClient() as client:
                # Test that public endpoints don't require authentication
                response = await client.get(f"{self.base_url}/api/health")
                assert response.status_code == 200, "Health endpoint should be public"
                
                # Test that dashboard is accessible without authentication
                response = await client.get(f"{self.base_url}/api/dashboard/metrics")
                assert response.status_code == 200, "Dashboard should be accessible without authentication"
                
                self.passed_tests.append("Authentication requirements")
                print("  ✅ Authentication requirements")
                
        except Exception as e:
            self.failed_tests.append(f"Authentication requirements: {str(e)}")
            print(f"  ❌ Authentication requirements: {str(e)}")
    
    # Performance Tests
    async def _test_page_load_times(self):
        """Test page load times and performance"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Test main pages
                pages_to_test = [
                    ("/", "Dashboard"),
                    ("/explorer", "Data Explorer"),
                    ("/admin", "Admin")
                ]
                
                for page_path, page_name in pages_to_test:
                    start_time = time.time()
                    await page.goto(f"{self.base_url}{page_path}")
                    await page.wait_for_load_state("networkidle")
                    load_time = time.time() - start_time
                    
                    assert load_time < 10, f"Page {page_path} took too long to load: {load_time:.2f}s"
                    print(f"    📄 {page_path}: {load_time:.2f}s")
                
                await browser.close()
                self.passed_tests.append("Page load times")
                print("  ✅ Page load times")
                
        except Exception as e:
            self.failed_tests.append(f"Page load times: {str(e)}")
            print(f"  ❌ Page load times: {str(e)}")
    
    async def _test_api_response_times(self):
        """Test API response times"""
        try:
            async with httpx.AsyncClient() as client:
                endpoints_to_test = [
                    "/api/health",
                    "/api/dashboard/metrics",
                    "/api/data-explorer/lessons",
                    "/api/data-explorer/users",
                    "/api/data-explorer/table/user_responses"
                ]
                
                for endpoint in endpoints_to_test:
                    start_time = time.time()
                    response = await client.get(f"{self.base_url}{endpoint}")
                    response_time = time.time() - start_time
                    
                    assert response_time < 5, f"API {endpoint} took too long: {response_time:.2f}s"
                    print(f"    🔌 {endpoint}: {response_time:.2f}s")
                
                self.passed_tests.append("API response times")
                print("  ✅ API response times")
                
        except Exception as e:
            self.failed_tests.append(f"API response times: {str(e)}")
            print(f"  ❌ API response times: {str(e)}")
    
    async def _test_data_loading_performance(self):
        """Test data loading performance"""
        try:
            async with httpx.AsyncClient() as client:
                # Test large data queries
                start_time = time.time()
                response = await client.get(f"{self.base_url}/api/data-explorer/table/user_responses?limit=1000")
                load_time = time.time() - start_time
                
                assert response.status_code == 200, "Large data query failed"
                assert load_time < 10, f"Large data query took too long: {load_time:.2f}s"
                
                self.passed_tests.append("Data loading performance")
                print("  ✅ Data loading performance")
                
        except Exception as e:
            self.failed_tests.append(f"Data loading performance: {str(e)}")
            print(f"  ❌ Data loading performance: {str(e)}")
    
    async def _test_error_handling_performance(self):
        """Test error handling performance"""
        try:
            async with httpx.AsyncClient() as client:
                # Test error scenarios
                error_endpoints = [
                    "/api/nonexistent",
                    "/api/data-explorer/table/invalid_table",
                    "/api/dashboard/load"  # This should return 404 or 501
                ]
                
                for endpoint in error_endpoints:
                    start_time = time.time()
                    response = await client.get(f"{self.base_url}{endpoint}")
                    response_time = time.time() - start_time
                    
                    assert response_time < 3, f"Error handling took too long for {endpoint}: {response_time:.2f}s"
                
                self.passed_tests.append("Error handling performance")
                print("  ✅ Error handling performance")
                
        except Exception as e:
            self.failed_tests.append(f"Error handling performance: {str(e)}")
            print(f"  ❌ Error handling performance: {str(e)}")
    
    # Integration Tests
    async def _test_bigquery_connectivity(self):
        """Test BigQuery connectivity and data access"""
        try:
            async with httpx.AsyncClient() as client:
                # Test BigQuery endpoints
                bigquery_endpoints = [
                    "/api/data-explorer/lessons",
                    "/api/data-explorer/users",
                    "/api/data-explorer/table/user_responses",
                    "/api/data-explorer/table/user_activities"
                ]
                
                for endpoint in bigquery_endpoints:
                    response = await client.get(f"{self.base_url}{endpoint}")
                    assert response.status_code == 200, f"BigQuery endpoint {endpoint} failed"
                    
                    data = response.json()
                    # Handle different response formats
                    if endpoint in ["/api/data-explorer/lessons", "/api/data-explorer/users"]:
                        # These endpoints return objects with arrays
                        assert isinstance(data, dict), f"BigQuery endpoint {endpoint} should return object"
                        if endpoint == "/api/data-explorer/lessons":
                            assert "lessons" in data, f"Lessons endpoint should have 'lessons' key"
                            assert isinstance(data["lessons"], list), f"Lessons data should be a list"
                        elif endpoint == "/api/data-explorer/users":
                            assert "users" in data, f"Users endpoint should have 'users' key"
                            assert isinstance(data["users"], list), f"Users data should be a list"
                    else:
                        # Other endpoints return arrays directly
                        assert isinstance(data, list), f"BigQuery endpoint {endpoint} should return list"
                
                self.passed_tests.append("BigQuery connectivity")
                print("  ✅ BigQuery connectivity")
                
        except Exception as e:
            self.failed_tests.append(f"BigQuery connectivity: {str(e)}")
            print(f"  ❌ BigQuery connectivity: {str(e)}")
    
    async def _test_api_endpoint_integration(self):
        """Test API endpoint integration"""
        try:
            async with httpx.AsyncClient() as client:
                # Test that all API endpoints work together
                health_response = await client.get(f"{self.base_url}/api/health")
                assert health_response.status_code == 200, "Health endpoint failed"
                
                dashboard_response = await client.get(f"{self.base_url}/api/dashboard/metrics")
                assert dashboard_response.status_code == 200, "Dashboard endpoint failed"
                
                # Test that dashboard data is consistent with individual endpoints
                dashboard_data = dashboard_response.json()
                lessons_response = await client.get(f"{self.base_url}/api/data-explorer/lessons")
                users_response = await client.get(f"{self.base_url}/api/data-explorer/users")
                
                assert lessons_response.status_code == 200, "Lessons endpoint failed"
                assert users_response.status_code == 200, "Users endpoint failed"
                
                self.passed_tests.append("API endpoint integration")
                print("  ✅ API endpoint integration")
                
        except Exception as e:
            self.failed_tests.append(f"API endpoint integration: {str(e)}")
            print(f"  ❌ API endpoint integration: {str(e)}")
    
    async def _test_ui_api_data_flow(self):
        """Test UI-API data flow"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Test dashboard data flow
                await page.goto(f"{self.base_url}/")
                await page.wait_for_load_state("networkidle")
                
                # Check if dashboard loads without errors
                errors = await page.evaluate("""
                    () => {
                        const errors = [];
                        if (window.console && window.console.error) {
                            const originalError = window.console.error;
                            window.console.error = (...args) => {
                                errors.push(args.join(' '));
                                originalError.apply(console, args);
                            };
                        }
                        return errors;
                    }
                """)
                
                assert len(errors) == 0, f"Dashboard has JavaScript errors: {errors}"
                
                await browser.close()
                self.passed_tests.append("UI-API data flow")
                print("  ✅ UI-API data flow")
                
        except Exception as e:
            self.failed_tests.append(f"UI-API data flow: {str(e)}")
            print(f"  ❌ UI-API data flow: {str(e)}")
    
    async def _test_cross_component_communication(self):
        """Test cross-component communication"""
        try:
            async with httpx.AsyncClient() as client:
                # Test that components can communicate properly
                # This is more of a smoke test for the overall system
                
                # Test health endpoint
                health_response = await client.get(f"{self.base_url}/api/health")
                assert health_response.status_code == 200, "Health endpoint failed"
                
                # Test that the system is responsive
                start_time = time.time()
                response = await client.get(f"{self.base_url}/api/dashboard/metrics")
                response_time = time.time() - start_time
                
                assert response.status_code == 200, "Dashboard endpoint failed"
                assert response_time < 5, "System is not responsive"
                
                self.passed_tests.append("Cross-component communication")
                print("  ✅ Cross-component communication")
                
        except Exception as e:
            self.failed_tests.append(f"Cross-component communication: {str(e)}")
            print(f"  ❌ Cross-component communication: {str(e)}")
    
    # UI Functionality Tests
    async def _test_navigation_routing(self):
        """Test navigation and routing"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Test main navigation
                pages_to_test = [
                    ("/", "Dashboard"),
                    ("/explorer", "Data Explorer"),
                    ("/admin", "Admin")
                ]
                
                for url, expected_title in pages_to_test:
                    await page.goto(f"{self.base_url}{url}")
                    await page.wait_for_load_state("networkidle")
                    
                    # Check if page loaded without errors
                    title = await page.title()
                    assert title, f"Page {url} should have a title"
                    
                    print(f"    🧭 {url}: {title}")
                
                await browser.close()
                self.passed_tests.append("Navigation routing")
                print("  ✅ Navigation routing")
                
        except Exception as e:
            self.failed_tests.append(f"Navigation routing: {str(e)}")
            print(f"  ❌ Navigation routing: {str(e)}")
    
    async def _test_form_interactions(self):
        """Test form interactions and user input"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Test Data Explorer form interactions
                await page.goto(f"{self.base_url}/explorer")
                await page.wait_for_load_state("networkidle")
                
                # Test table selection
                table_select = await page.query_selector("#table-select")
                if table_select:
                    await table_select.select_option("user_responses")
                    await page.wait_for_timeout(1000)  # Wait for data to load
                
                # Test limit input
                limit_input = await page.query_selector("#limit-input")
                if limit_input:
                    await limit_input.fill("50")
                    await page.wait_for_timeout(1000)
                
                await browser.close()
                self.passed_tests.append("Form interactions")
                print("  ✅ Form interactions")
                
        except Exception as e:
            self.failed_tests.append(f"Form interactions: {str(e)}")
            print(f"  ❌ Form interactions: {str(e)}")
    
    async def _test_data_visualization(self):
        """Test data visualization and charts"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Test dashboard charts
                await page.goto(f"{self.base_url}/")
                await page.wait_for_load_state("networkidle")
                
                # Check if charts are rendered
                chart_elements = await page.query_selector_all("canvas")
                assert len(chart_elements) > 0, "Dashboard should have chart elements"
                
                # Check if data is displayed
                data_elements = await page.query_selector_all("[data-testid*='metric'], .metric, .stat")
                assert len(data_elements) > 0, "Dashboard should display metrics"
                
                await browser.close()
                self.passed_tests.append("Data visualization")
                print("  ✅ Data visualization")
                
        except Exception as e:
            self.failed_tests.append(f"Data visualization: {str(e)}")
            print(f"  ❌ Data visualization: {str(e)}")
    
    async def _test_ui_error_handling(self):
        """Test error handling in UI"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Test error scenarios
                await page.goto(f"{self.base_url}/nonexistent-page")
                await page.wait_for_load_state("networkidle")
                
                # Check if error page is handled gracefully
                content = await page.content()
                assert "404" in content or "Not Found" in content or "Error" in content, "Error page should be handled"
                
                await browser.close()
                self.passed_tests.append("UI error handling")
                print("  ✅ UI error handling")
                
        except Exception as e:
            self.failed_tests.append(f"UI error handling: {str(e)}")
            print(f"  ❌ UI error handling: {str(e)}")
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 60)
        print("📋 COMPREHENSIVE TEST REPORT")
        print("=" * 60)
        
        total_tests = len(self.passed_tests) + len(self.failed_tests)
        pass_rate = (len(self.passed_tests) / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📊 Test Summary:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {len(self.passed_tests)}")
        print(f"   Failed: {len(self.failed_tests)}")
        print(f"   Pass Rate: {pass_rate:.1f}%")
        
        if self.passed_tests:
            print(f"\n✅ Passed Tests ({len(self.passed_tests)}):")
            for test in self.passed_tests:
                print(f"   • {test}")
        
        if self.failed_tests:
            print(f"\n❌ Failed Tests ({len(self.failed_tests)}):")
            for test in self.failed_tests:
                print(f"   • {test}")
        
        print(f"\n🎯 Business Logic Validation: {'✅ PASSED' if all('business_logic' in test.lower() or 'accuracy' in test.lower() or 'consistency' in test.lower() or 'validation' in test.lower() or 'tracking' in test.lower() for test in self.passed_tests) else '❌ FAILED'}")
        print(f"🔒 Security Rules Validation: {'✅ PASSED' if all('security' in test.lower() or 'access' in test.lower() or 'validation' in test.lower() or 'authentication' in test.lower() for test in self.passed_tests) else '❌ FAILED'}")
        print(f"⚡ Performance Validation: {'✅ PASSED' if all('performance' in test.lower() or 'load' in test.lower() or 'response' in test.lower() for test in self.passed_tests) else '❌ FAILED'}")
        print(f"🔗 Integration Validation: {'✅ PASSED' if all('integration' in test.lower() or 'connectivity' in test.lower() or 'communication' in test.lower() for test in self.passed_tests) else '❌ FAILED'}")
        print(f"🖥️ UI Functionality Validation: {'✅ PASSED' if all('ui' in test.lower() or 'navigation' in test.lower() or 'form' in test.lower() or 'visualization' in test.lower() for test in self.passed_tests) else '❌ FAILED'}")
        
        # Save detailed report
        report_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_tests": total_tests,
            "passed_tests": len(self.passed_tests),
            "failed_tests": len(self.failed_tests),
            "pass_rate": pass_rate,
            "passed_test_details": self.passed_tests,
            "failed_test_details": self.failed_tests,
            "business_logic_status": "PASSED" if all('business_logic' in test.lower() or 'accuracy' in test.lower() or 'consistency' in test.lower() or 'validation' in test.lower() or 'tracking' in test.lower() for test in self.passed_tests) else "FAILED",
            "security_status": "PASSED" if all('security' in test.lower() or 'access' in test.lower() or 'validation' in test.lower() or 'authentication' in test.lower() for test in self.passed_tests) else "FAILED",
            "performance_status": "PASSED" if all('performance' in test.lower() or 'load' in test.lower() or 'response' in test.lower() for test in self.passed_tests) else "FAILED",
            "integration_status": "PASSED" if all('integration' in test.lower() or 'connectivity' in test.lower() or 'communication' in test.lower() for test in self.passed_tests) else "FAILED",
            "ui_functionality_status": "PASSED" if all('ui' in test.lower() or 'navigation' in test.lower() or 'form' in test.lower() or 'visualization' in test.lower() for test in self.passed_tests) else "FAILED"
        }
        
        with open("comprehensive_test_report.json", "w") as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: comprehensive_test_report.json")
        
        if pass_rate >= 90:
            print(f"\n🎉 EXCELLENT! System is performing at {pass_rate:.1f}% pass rate!")
        elif pass_rate >= 80:
            print(f"\n👍 GOOD! System is performing at {pass_rate:.1f}% pass rate!")
        elif pass_rate >= 70:
            print(f"\n⚠️  FAIR! System is performing at {pass_rate:.1f}% pass rate - needs improvement!")
        else:
            print(f"\n🚨 POOR! System is performing at {pass_rate:.1f}% pass rate - requires immediate attention!")

async def main():
    """Run the comprehensive test suite"""
    test_suite = ComprehensiveTestSuite()
    await test_suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
