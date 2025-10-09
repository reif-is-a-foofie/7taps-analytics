#!/usr/bin/env python3
"""
Business-Centric UI Validation Test Suite for POL Analytics
Following AGENTS.md requirements for business-case tier testing.

This suite validates:
- Digital wellness analytics outputs
- Stakeholder dashboard functionality  
- Business KPI accuracy
- Practice of Life mission alignment
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
import httpx
from typing import Dict, List, Any
import os

class BusinessValidationSuite:
    """Comprehensive business validation for POL Analytics platform."""
    
    def __init__(self, base_url: str = "https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app"):
        self.base_url = base_url
        self.results = {
            "test_timestamp": datetime.utcnow().isoformat(),
            "platform": "POL Analytics",
            "mission_alignment": {},
            "stakeholder_dashboards": {},
            "business_kpis": {},
            "digital_wellness_metrics": {},
            "user_experience": {},
            "api_performance": {},
            "summary": {}
        }
    
    async def validate_mission_alignment(self) -> Dict[str, Any]:
        """Validate platform alignment with Practice of Life mission."""
        print("🎯 Validating POL Mission Alignment...")
        
        mission_tests = {}
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Test 1: Branding consistency
            await page.goto(f"{self.base_url}/")
            title = await page.title()
            pol_branding = "POL Analytics" in title
            mission_tests["branding_consistency"] = {
                "passed": pol_branding,
                "title": title,
                "message": "POL branding present in title" if pol_branding else "Missing POL branding"
            }
            
            # Test 2: Digital wellness focus
            content = await page.content()
            wellness_keywords = ["digital wellness", "Practice of Life", "engagement", "learning"]
            wellness_focus = sum(1 for keyword in wellness_keywords if keyword.lower() in content.lower())
            mission_tests["digital_wellness_focus"] = {
                "passed": wellness_focus >= 2,
                "keywords_found": wellness_focus,
                "message": f"Found {wellness_focus}/4 wellness-focused keywords"
            }
            
            # Test 3: September AI assistant alignment
            await page.goto(f"{self.base_url}/chat")
            september_content = await page.content()
            september_present = "September" in september_content
            pol_assistant = "POL Analytics Assistant" in september_content
            mission_tests["ai_assistant_alignment"] = {
                "passed": september_present and pol_assistant,
                "september_present": september_present,
                "pol_context": pol_assistant,
                "message": "September AI assistant properly aligned with POL mission"
            }
            
            await browser.close()
        
        self.results["mission_alignment"] = mission_tests
        return mission_tests
    
    async def validate_stakeholder_dashboards(self) -> Dict[str, Any]:
        """Validate stakeholder dashboard functionality and data accuracy."""
        print("📊 Validating Stakeholder Dashboards...")
        
        dashboard_tests = {}
        
        async with httpx.AsyncClient() as client:
            # Test 1: Main dashboard accessibility
            try:
                response = await client.get(f"{self.base_url}/")
                dashboard_tests["main_dashboard_access"] = {
                    "passed": response.status_code == 200,
                    "status_code": response.status_code,
                    "response_time_ms": round(response.elapsed.total_seconds() * 1000),
                    "message": "Main dashboard accessible"
                }
            except Exception as e:
                dashboard_tests["main_dashboard_access"] = {
                    "passed": False,
                    "error": str(e),
                    "message": "Main dashboard access failed"
                }
            
            # Test 2: Data explorer functionality
            try:
                response = await client.get(f"{self.base_url}/explorer")
                dashboard_tests["data_explorer_access"] = {
                    "passed": response.status_code == 200,
                    "status_code": response.status_code,
                    "response_time_ms": round(response.elapsed.total_seconds() * 1000),
                    "message": "Data explorer accessible"
                }
            except Exception as e:
                dashboard_tests["data_explorer_access"] = {
                    "passed": False,
                    "error": str(e),
                    "message": "Data explorer access failed"
                }
            
            # Test 3: Real-time data feed
            try:
                response = await client.get(f"{self.base_url}/ui/recent-pubsub")
                dashboard_tests["realtime_feed_access"] = {
                    "passed": response.status_code == 200,
                    "status_code": response.status_code,
                    "response_time_ms": round(response.elapsed.total_seconds() * 1000),
                    "message": "Real-time Pub/Sub feed accessible"
                }
            except Exception as e:
                dashboard_tests["realtime_feed_access"] = {
                    "passed": False,
                    "error": str(e),
                    "message": "Real-time feed access failed"
                }
        
        self.results["stakeholder_dashboards"] = dashboard_tests
        return dashboard_tests
    
    async def validate_business_kpis(self) -> Dict[str, Any]:
        """Validate business KPI accuracy and availability."""
        print("📈 Validating Business KPIs...")
        
        kpi_tests = {}
        
        async with httpx.AsyncClient() as client:
            # Test 1: Health metrics
            try:
                response = await client.get(f"{self.base_url}/api/health")
                health_data = response.json()
                kpi_tests["system_health_kpi"] = {
                    "passed": health_data.get("status") == "healthy",
                    "status": health_data.get("status"),
                    "service": health_data.get("service"),
                    "message": "System health KPI available and healthy"
                }
            except Exception as e:
                kpi_tests["system_health_kpi"] = {
                    "passed": False,
                    "error": str(e),
                    "message": "System health KPI unavailable"
                }
            
            # Test 2: xAPI ingestion metrics
            try:
                response = await client.get(f"{self.base_url}/ui/test-xapi-ingestion")
                ingestion_data = response.json()
                kpi_tests["ingestion_metrics_kpi"] = {
                    "passed": "endpoint_status" in ingestion_data,
                    "endpoint_status": ingestion_data.get("endpoint_status"),
                    "publisher_ready": ingestion_data.get("publisher_ready"),
                    "total_statements": ingestion_data.get("total_statements_ingested", 0),
                    "message": "xAPI ingestion metrics available"
                }
            except Exception as e:
                kpi_tests["ingestion_metrics_kpi"] = {
                    "passed": False,
                    "error": str(e),
                    "message": "Ingestion metrics KPI unavailable"
                }
            
            # Test 3: Recent activity metrics
            try:
                response = await client.get(f"{self.base_url}/api/xapi/recent")
                activity_data = response.json()
                kpi_tests["activity_metrics_kpi"] = {
                    "passed": "ingestion_stats" in activity_data,
                    "statements_available": activity_data.get("available", 0),
                    "ingestion_stats": activity_data.get("ingestion_stats", {}),
                    "message": "Recent activity metrics available"
                }
            except Exception as e:
                kpi_tests["activity_metrics_kpi"] = {
                    "passed": False,
                    "error": str(e),
                    "message": "Activity metrics KPI unavailable"
                }
        
        self.results["business_kpis"] = kpi_tests
        return kpi_tests
    
    async def validate_digital_wellness_analytics(self) -> Dict[str, Any]:
        """Validate digital wellness-specific analytics capabilities."""
        print("🧠 Validating Digital Wellness Analytics...")
        
        wellness_tests = {}
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Test 1: September AI assistant functionality
            await page.goto(f"{self.base_url}/chat")
            
            # Test September chat response
            await page.fill('textarea[placeholder*="message"], input[placeholder*="message"], #messageInput', 'What digital wellness insights can you provide?')
            
            # Wait for and click send button
            try:
                send_button = await page.wait_for_selector('button:has-text("Send"), .send-button, #sendButton', timeout=5000)
                await send_button.click()
                
                # Wait for response
                await page.wait_for_timeout(3000)
                
                # Check for response in messages
                messages = await page.query_selector_all('.message, .chat-message')
                wellness_tests["september_ai_response"] = {
                    "passed": len(messages) > 1,  # Initial message + response
                    "message_count": len(messages),
                    "message": "September AI assistant responds to digital wellness queries"
                }
            except Exception as e:
                wellness_tests["september_ai_response"] = {
                    "passed": False,
                    "error": str(e),
                    "message": "September AI assistant response test failed"
                }
            
            await browser.close()
        
        # Test 2: API explorer for wellness data
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/api/explorer")
                explorer_data = response.json()
                wellness_tests["wellness_data_explorer"] = {
                    "passed": explorer_data.get("success", False),
                    "project_id": explorer_data.get("project_id"),
                    "dataset": explorer_data.get("dataset"),
                    "tables": explorer_data.get("tables", []),
                    "message": "Wellness data exploration capabilities available"
                }
            except Exception as e:
                wellness_tests["wellness_data_explorer"] = {
                    "passed": False,
                    "error": str(e),
                    "message": "Wellness data explorer unavailable"
                }
        
        self.results["digital_wellness_metrics"] = wellness_tests
        return wellness_tests
    
    async def validate_user_experience(self) -> Dict[str, Any]:
        """Validate user experience and interface responsiveness."""
        print("👥 Validating User Experience...")
        
        ux_tests = {}
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Test 1: Page load performance
            start_time = time.time()
            await page.goto(f"{self.base_url}/")
            load_time = (time.time() - start_time) * 1000
            
            ux_tests["page_load_performance"] = {
                "passed": load_time < 5000,  # Under 5 seconds
                "load_time_ms": round(load_time),
                "message": f"Page loads in {round(load_time)}ms"
            }
            
            # Test 2: Navigation functionality
            nav_links = await page.query_selector_all('a[href], .nav-item')
            ux_tests["navigation_availability"] = {
                "passed": len(nav_links) > 0,
                "nav_link_count": len(nav_links),
                "message": f"Found {len(nav_links)} navigation elements"
            }
            
            # Test 3: Mobile responsiveness check
            await page.set_viewport_size({"width": 375, "height": 667})  # iPhone size
            mobile_content = await page.content()
            mobile_responsive = "viewport" in mobile_content and "width=device-width" in mobile_content
            
            ux_tests["mobile_responsiveness"] = {
                "passed": mobile_responsive,
                "viewport_meta": mobile_responsive,
                "message": "Mobile viewport configuration present"
            }
            
            await browser.close()
        
        self.results["user_experience"] = ux_tests
        return ux_tests
    
    async def validate_api_performance(self) -> Dict[str, Any]:
        """Validate API performance and reliability."""
        print("⚡ Validating API Performance...")
        
        api_tests = {}
        
        async with httpx.AsyncClient() as client:
            # Test critical API endpoints
            endpoints = [
                ("/api/health", "Health Check"),
                ("/api/xapi/recent", "Recent xAPI Data"),
                ("/ui/test-xapi-ingestion", "xAPI Ingestion Status"),
                ("/api/explorer", "Data Explorer API")
            ]
            
            for endpoint, name in endpoints:
                try:
                    start_time = time.time()
                    response = await client.get(f"{self.base_url}{endpoint}")
                    response_time = (time.time() - start_time) * 1000
                    
                    api_tests[f"{name.lower().replace(' ', '_')}_performance"] = {
                        "passed": response.status_code == 200 and response_time < 2000,
                        "status_code": response.status_code,
                        "response_time_ms": round(response_time),
                        "endpoint": endpoint,
                        "message": f"{name} responds in {round(response_time)}ms"
                    }
                except Exception as e:
                    api_tests[f"{name.lower().replace(' ', '_')}_performance"] = {
                        "passed": False,
                        "error": str(e),
                        "endpoint": endpoint,
                        "message": f"{name} API test failed"
                    }
        
        self.results["api_performance"] = api_tests
        return api_tests
    
    async def generate_business_summary(self) -> Dict[str, Any]:
        """Generate business impact summary and recommendations."""
        print("📋 Generating Business Impact Summary...")
        
        # Calculate overall scores
        total_tests = 0
        passed_tests = 0
        
        for category, tests in self.results.items():
            if isinstance(tests, dict) and category != "summary":
                for test_name, test_result in tests.items():
                    if isinstance(test_result, dict) and "passed" in test_result:
                        total_tests += 1
                        if test_result["passed"]:
                            passed_tests += 1
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Business impact assessment
        business_impact = {
            "overall_health": "Excellent" if success_rate >= 90 else "Good" if success_rate >= 75 else "Needs Attention",
            "success_rate_percent": round(success_rate, 1),
            "tests_passed": passed_tests,
            "total_tests": total_tests,
            "mission_alignment_status": "Aligned" if self.results.get("mission_alignment", {}) else "Needs Review",
            "stakeholder_readiness": "Ready" if success_rate >= 80 else "In Progress",
            "recommendations": []
        }
        
        # Generate recommendations
        if success_rate < 90:
            business_impact["recommendations"].append("Investigate failing tests to improve platform reliability")
        
        if not self.results.get("mission_alignment", {}).get("digital_wellness_focus", {}).get("passed"):
            business_impact["recommendations"].append("Enhance digital wellness messaging and content")
        
        if not self.results.get("digital_wellness_metrics", {}).get("september_ai_response", {}).get("passed"):
            business_impact["recommendations"].append("Improve September AI assistant functionality")
        
        # Performance recommendations
        slow_apis = [test for test in self.results.get("api_performance", {}).values() 
                    if isinstance(test, dict) and test.get("response_time_ms", 0) > 1000]
        if slow_apis:
            business_impact["recommendations"].append("Optimize API performance for better user experience")
        
        business_impact["test_timestamp"] = self.results["test_timestamp"]
        business_impact["platform_version"] = "POL Analytics v1.0"
        
        self.results["summary"] = business_impact
        return business_impact
    
    async def run_full_validation(self) -> Dict[str, Any]:
        """Run complete business validation suite."""
        print("🚀 Starting POL Analytics Business Validation Suite...")
        print(f"Testing platform: {self.base_url}")
        print("-" * 60)
        
        # Run all validation categories
        await self.validate_mission_alignment()
        await self.validate_stakeholder_dashboards()
        await self.validate_business_kpis()
        await self.validate_digital_wellness_analytics()
        await self.validate_user_experience()
        await self.validate_api_performance()
        await self.generate_business_summary()
        
        print("-" * 60)
        print("✅ Business Validation Suite Complete!")
        
        return self.results

async def main():
    """Execute business validation test suite."""
    suite = BusinessValidationSuite()
    results = await suite.run_full_validation()
    
    # Save results
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    results_file = f"business_validation_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    summary = results["summary"]
    print(f"\n📊 Business Impact Summary:")
    print(f"Overall Health: {summary['overall_health']}")
    print(f"Success Rate: {summary['success_rate_percent']}% ({summary['tests_passed']}/{summary['total_tests']})")
    print(f"Mission Alignment: {summary['mission_alignment_status']}")
    print(f"Stakeholder Readiness: {summary['stakeholder_readiness']}")
    
    if summary["recommendations"]:
        print(f"\n💡 Recommendations:")
        for i, rec in enumerate(summary["recommendations"], 1):
            print(f"  {i}. {rec}")
    
    print(f"\n📁 Detailed results saved to: {results_file}")
    return results

if __name__ == "__main__":
    asyncio.run(main())



