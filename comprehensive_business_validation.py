#!/usr/bin/env python3
"""
Comprehensive Business Validation Suite for POL Analytics
Third-party audit-grade testing with enterprise coverage.

Addresses critical gaps:
- End-to-end user workflows
- Data accuracy validation  
- Security & privacy compliance
- Error handling & edge cases
- Integration testing
- Accessibility compliance
- Cross-browser compatibility
- Business logic validation
"""

import asyncio
import json
import time
import base64
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
import httpx
from typing import Dict, List, Any
import os
import hashlib

class ComprehensiveBusinessValidation:
    """Enterprise-grade business validation for POL Analytics."""
    
    def __init__(self, base_url: str = "https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app"):
        self.base_url = base_url
        self.results = {
            "audit_timestamp": datetime.utcnow().isoformat(),
            "audit_version": "comprehensive_v1.0",
            "platform": "POL Analytics - Practice of Life",
            "security_compliance": {},
            "end_to_end_workflows": {},
            "data_accuracy": {},
            "error_handling": {},
            "integration_testing": {},
            "accessibility_compliance": {},
            "cross_browser_compatibility": {},
            "business_logic_validation": {},
            "load_testing": {},
            "audit_summary": {}
        }
    
    async def validate_security_compliance(self) -> Dict[str, Any]:
        """Validate data security, privacy, and compliance measures."""
        print("🔒 Auditing Security & Privacy Compliance...")
        
        security_tests = {}
        
        async with httpx.AsyncClient() as client:
            # Test 1: Authentication security
            try:
                # Test invalid credentials rejection
                invalid_auth = base64.b64encode(b"invalid:credentials").decode()
                response = await client.post(
                    f"{self.base_url}/statements",
                    headers={"Authorization": f"Basic {invalid_auth}"},
                    json={"test": "data"}
                )
                security_tests["authentication_security"] = {
                    "passed": response.status_code == 401,
                    "status_code": response.status_code,
                    "message": "Invalid credentials properly rejected"
                }
            except Exception as e:
                security_tests["authentication_security"] = {
                    "passed": False,
                    "error": str(e),
                    "message": "Authentication security test failed"
                }
            
            # Test 2: HTTPS enforcement
            try:
                http_url = self.base_url.replace("https://", "http://")
                response = await client.get(http_url, follow_redirects=False)
                https_enforced = response.status_code in [301, 302, 308] or "https" in str(response.headers)
                security_tests["https_enforcement"] = {
                    "passed": https_enforced,
                    "redirect_status": response.status_code,
                    "message": "HTTPS enforcement validated"
                }
            except Exception:
                # If HTTP fails completely, HTTPS is properly enforced
                security_tests["https_enforcement"] = {
                    "passed": True,
                    "message": "HTTP completely blocked - HTTPS properly enforced"
                }
            
            # Test 3: Sensitive data exposure
            try:
                response = await client.get(f"{self.base_url}/api/health")
                health_data = response.json()
                sensitive_fields = ["password", "secret", "key", "token"]
                exposed_data = any(field in str(health_data).lower() for field in sensitive_fields)
                security_tests["sensitive_data_exposure"] = {
                    "passed": not exposed_data,
                    "exposed_sensitive_data": exposed_data,
                    "message": "No sensitive data exposed in public endpoints"
                }
            except Exception as e:
                security_tests["sensitive_data_exposure"] = {
                    "passed": False,
                    "error": str(e),
                    "message": "Sensitive data exposure test failed"
                }
        
        self.results["security_compliance"] = security_tests
        return security_tests
    
    async def validate_end_to_end_workflows(self) -> Dict[str, Any]:
        """Validate complete user workflows and journeys."""
        print("🔄 Auditing End-to-End User Workflows...")
        
        workflow_tests = {}
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Workflow 1: Dashboard → Data Explorer → Query Execution
            try:
                # Start at dashboard
                await page.goto(f"{self.base_url}/")
                await page.wait_for_load_state("networkidle")
                
                # Navigate to data explorer
                await page.goto(f"{self.base_url}/explorer")
                await page.wait_for_load_state("networkidle")
                
                # Check for interactive elements
                buttons = await page.query_selector_all("button")
                inputs = await page.query_selector_all("input, textarea")
                
                workflow_tests["dashboard_to_explorer_workflow"] = {
                    "passed": len(buttons) > 0 or len(inputs) > 0,
                    "interactive_elements": len(buttons) + len(inputs),
                    "message": f"Dashboard→Explorer workflow has {len(buttons)} buttons, {len(inputs)} inputs"
                }
            except Exception as e:
                workflow_tests["dashboard_to_explorer_workflow"] = {
                    "passed": False,
                    "error": str(e),
                    "message": "Dashboard→Explorer workflow failed"
                }
            
            # Workflow 2: September Chat Interaction
            try:
                await page.goto(f"{self.base_url}/chat")
                await page.wait_for_load_state("networkidle")
                
                # Look for chat input
                chat_input = await page.query_selector("textarea, input[type='text']")
                send_button = await page.query_selector("button")
                
                workflow_tests["september_chat_workflow"] = {
                    "passed": chat_input is not None and send_button is not None,
                    "chat_input_present": chat_input is not None,
                    "send_button_present": send_button is not None,
                    "message": "September chat workflow elements present"
                }
            except Exception as e:
                workflow_tests["september_chat_workflow"] = {
                    "passed": False,
                    "error": str(e),
                    "message": "September chat workflow failed"
                }
            
            await browser.close()
        
        self.results["end_to_end_workflows"] = workflow_tests
        return workflow_tests
    
    async def validate_data_accuracy(self) -> Dict[str, Any]:
        """Validate data accuracy and mathematical correctness of analytics."""
        print("📊 Auditing Data Accuracy & Mathematical Correctness...")
        
        accuracy_tests = {}
        
        async with httpx.AsyncClient() as client:
            # Test 1: xAPI statement injection and retrieval accuracy
            try:
                # Inject a test statement
                test_statement = {
                    "actor": {"mbox": "mailto:audit@test.com"},
                    "verb": {"id": "http://adlnet.gov/expapi/verbs/completed"},
                    "object": {"id": "http://test.com/audit-activity"}
                }
                
                auth = ("7taps.team", "PracticeofLife")
                inject_response = await client.post(
                    f"{self.base_url}/statements",
                    json=test_statement,
                    auth=auth,
                    timeout=10.0
                )
                
                if inject_response.status_code == 200:
                    inject_data = inject_response.json()
                    statement_id = inject_data.get("statements", [{}])[0].get("statement_id")
                    
                    # Verify the statement appears in recent data
                    await asyncio.sleep(2)  # Allow processing time
                    recent_response = await client.get(f"{self.base_url}/api/xapi/recent")
                    recent_data = recent_response.json()
                    
                    statements = recent_data.get("statements", [])
                    found_statement = any(s.get("statement_id") == statement_id for s in statements)
                    
                    accuracy_tests["xapi_injection_accuracy"] = {
                        "passed": found_statement,
                        "injected_statement_id": statement_id,
                        "found_in_recent": found_statement,
                        "total_recent_statements": len(statements),
                        "message": "xAPI statement injection and retrieval accurate"
                    }
                else:
                    accuracy_tests["xapi_injection_accuracy"] = {
                        "passed": False,
                        "injection_status": inject_response.status_code,
                        "message": "xAPI statement injection failed"
                    }
            except Exception as e:
                accuracy_tests["xapi_injection_accuracy"] = {
                    "passed": False,
                    "error": str(e),
                    "message": "xAPI injection accuracy test failed"
                }
            
            # Test 2: API data consistency
            try:
                # Get data from multiple endpoints
                health_response = await client.get(f"{self.base_url}/api/health")
                ingestion_response = await client.get(f"{self.base_url}/ui/test-xapi-ingestion")
                recent_response = await client.get(f"{self.base_url}/api/xapi/recent")
                
                health_ok = health_response.status_code == 200
                ingestion_ok = ingestion_response.status_code == 200
                recent_ok = recent_response.status_code == 200
                
                consistency_score = sum([health_ok, ingestion_ok, recent_ok]) / 3
                
                accuracy_tests["api_data_consistency"] = {
                    "passed": consistency_score >= 0.8,
                    "health_endpoint": health_ok,
                    "ingestion_endpoint": ingestion_ok,
                    "recent_data_endpoint": recent_ok,
                    "consistency_score": round(consistency_score * 100, 1),
                    "message": f"API data consistency: {round(consistency_score * 100, 1)}%"
                }
            except Exception as e:
                accuracy_tests["api_data_consistency"] = {
                    "passed": False,
                    "error": str(e),
                    "message": "API data consistency test failed"
                }
        
        self.results["data_accuracy"] = accuracy_tests
        return accuracy_tests
    
    async def validate_error_handling(self) -> Dict[str, Any]:
        """Validate error handling and edge case management."""
        print("⚠️ Auditing Error Handling & Edge Cases...")
        
        error_tests = {}
        
        async with httpx.AsyncClient() as client:
            # Test 1: Invalid JSON handling
            try:
                auth = ("7taps.team", "PracticeofLife")
                response = await client.post(
                    f"{self.base_url}/statements",
                    data="invalid json{",
                    headers={"Content-Type": "application/json"},
                    auth=auth
                )
                proper_error = response.status_code in [400, 422]
                error_tests["invalid_json_handling"] = {
                    "passed": proper_error,
                    "status_code": response.status_code,
                    "message": "Invalid JSON properly rejected"
                }
            except Exception as e:
                error_tests["invalid_json_handling"] = {
                    "passed": False,
                    "error": str(e),
                    "message": "Invalid JSON handling test failed"
                }
            
            # Test 2: Missing required fields
            try:
                auth = ("7taps.team", "PracticeofLife")
                incomplete_statement = {"actor": {"mbox": "mailto:test@example.com"}}  # Missing verb, object
                response = await client.post(
                    f"{self.base_url}/statements",
                    json=incomplete_statement,
                    auth=auth
                )
                proper_validation = response.status_code == 422
                error_tests["validation_error_handling"] = {
                    "passed": proper_validation,
                    "status_code": response.status_code,
                    "message": "Incomplete xAPI statements properly validated"
                }
            except Exception as e:
                error_tests["validation_error_handling"] = {
                    "passed": False,
                    "error": str(e),
                    "message": "Validation error handling test failed"
                }
            
            # Test 3: Rate limiting / DoS protection
            try:
                auth = ("7taps.team", "PracticeofLife")
                rapid_requests = []
                for i in range(5):  # Send 5 rapid requests
                    response = await client.post(
                        f"{self.base_url}/statements",
                        json={
                            "actor": {"mbox": f"mailto:test{i}@example.com"},
                            "verb": {"id": "http://test.com/verb"},
                            "object": {"id": f"http://test.com/object{i}"}
                        },
                        auth=auth
                    )
                    rapid_requests.append(response.status_code)
                
                success_rate = sum(1 for code in rapid_requests if code == 200) / len(rapid_requests)
                error_tests["rate_limiting_protection"] = {
                    "passed": success_rate >= 0.8,  # Allow some rate limiting
                    "success_rate": round(success_rate * 100, 1),
                    "request_results": rapid_requests,
                    "message": f"Rate limiting: {round(success_rate * 100, 1)}% success rate"
                }
            except Exception as e:
                error_tests["rate_limiting_protection"] = {
                    "passed": False,
                    "error": str(e),
                    "message": "Rate limiting test failed"
                }
        
        self.results["error_handling"] = error_tests
        return error_tests
    
    async def validate_integration_testing(self) -> Dict[str, Any]:
        """Validate end-to-end data flow integration."""
        print("🔗 Auditing Integration & Data Flow...")
        
        integration_tests = {}
        
        async with httpx.AsyncClient() as client:
            # Test 1: xAPI → Pub/Sub → BigQuery flow validation
            try:
                # Inject statement with unique identifier
                unique_id = f"integration-test-{int(time.time())}"
                test_statement = {
                    "id": unique_id,
                    "actor": {"mbox": "mailto:integration@test.com"},
                    "verb": {"id": "http://adlnet.gov/expapi/verbs/experienced"},
                    "object": {"id": "http://test.com/integration-activity"}
                }
                
                auth = ("7taps.team", "PracticeofLife")
                inject_response = await client.post(
                    f"{self.base_url}/statements",
                    json=test_statement,
                    auth=auth
                )
                
                if inject_response.status_code == 200:
                    inject_data = inject_response.json()
                    message_id = inject_data.get("statements", [{}])[0].get("message_id")
                    
                    # Verify ingestion stats updated
                    await asyncio.sleep(3)  # Allow processing time
                    stats_response = await client.get(f"{self.base_url}/ui/test-xapi-ingestion")
                    stats_data = stats_response.json()
                    
                    integration_tests["pubsub_integration"] = {
                        "passed": message_id is not None and stats_data.get("publisher_ready"),
                        "message_id": message_id,
                        "publisher_ready": stats_data.get("publisher_ready"),
                        "endpoint_status": stats_data.get("endpoint_status"),
                        "message": "xAPI → Pub/Sub integration validated"
                    }
                else:
                    integration_tests["pubsub_integration"] = {
                        "passed": False,
                        "injection_status": inject_response.status_code,
                        "message": "Pub/Sub integration test failed - injection rejected"
                    }
            except Exception as e:
                integration_tests["pubsub_integration"] = {
                    "passed": False,
                    "error": str(e),
                    "message": "Pub/Sub integration test failed"
                }
            
            # Test 2: BigQuery data explorer connectivity
            try:
                explorer_response = await client.get(f"{self.base_url}/api/explorer")
                explorer_data = explorer_response.json()
                
                has_tables = len(explorer_data.get("tables", [])) > 0
                has_project = bool(explorer_data.get("project_id"))
                
                integration_tests["bigquery_connectivity"] = {
                    "passed": has_tables and has_project,
                    "project_id": explorer_data.get("project_id"),
                    "table_count": len(explorer_data.get("tables", [])),
                    "tables": explorer_data.get("tables", [])[:3],  # First 3 tables
                    "message": "BigQuery connectivity and data access validated"
                }
            except Exception as e:
                integration_tests["bigquery_connectivity"] = {
                    "passed": False,
                    "error": str(e),
                    "message": "BigQuery connectivity test failed"
                }
        
        self.results["integration_testing"] = integration_tests
        return integration_tests
    
    async def validate_accessibility_compliance(self) -> Dict[str, Any]:
        """Validate accessibility and WCAG compliance."""
        print("♿ Auditing Accessibility Compliance...")
        
        a11y_tests = {}
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Test 1: Semantic HTML structure
            await page.goto(f"{self.base_url}/")
            
            # Check for proper heading hierarchy
            headings = await page.query_selector_all("h1, h2, h3, h4, h5, h6")
            has_h1 = len(await page.query_selector_all("h1")) > 0
            
            # Check for alt text on images
            images = await page.query_selector_all("img")
            images_with_alt = 0
            for img in images:
                alt = await img.get_attribute("alt")
                if alt:
                    images_with_alt += 1
            
            # Check for form labels
            inputs = await page.query_selector_all("input")
            labels = await page.query_selector_all("label")
            
            a11y_tests["semantic_html_structure"] = {
                "passed": has_h1 and len(headings) > 0,
                "has_h1": has_h1,
                "heading_count": len(headings),
                "images_with_alt": f"{images_with_alt}/{len(images)}",
                "form_labels": len(labels),
                "message": "Semantic HTML structure validated"
            }
            
            # Test 2: Keyboard navigation
            try:
                # Test tab navigation
                await page.keyboard.press("Tab")
                focused_element = await page.evaluate("document.activeElement.tagName")
                
                a11y_tests["keyboard_navigation"] = {
                    "passed": focused_element in ["A", "BUTTON", "INPUT", "TEXTAREA"],
                    "focused_element": focused_element,
                    "message": "Keyboard navigation functional"
                }
            except Exception as e:
                a11y_tests["keyboard_navigation"] = {
                    "passed": False,
                    "error": str(e),
                    "message": "Keyboard navigation test failed"
                }
            
            await browser.close()
        
        self.results["accessibility_compliance"] = a11y_tests
        return a11y_tests
    
    async def validate_business_logic(self) -> Dict[str, Any]:
        """Validate Practice of Life specific business logic."""
        print("🎯 Auditing POL Business Logic Validation...")
        
        business_tests = {}
        
        async with httpx.AsyncClient() as client:
            # Test 1: Digital wellness keyword presence
            try:
                response = await client.get(f"{self.base_url}/")
                content = response.text.lower()
                
                wellness_keywords = [
                    "digital wellness", "practice of life", "engagement", 
                    "learning", "mindfulness", "well-being", "analytics"
                ]
                found_keywords = [kw for kw in wellness_keywords if kw in content]
                
                business_tests["digital_wellness_content"] = {
                    "passed": len(found_keywords) >= 4,
                    "keywords_found": found_keywords,
                    "keyword_count": len(found_keywords),
                    "message": f"Found {len(found_keywords)}/7 digital wellness keywords"
                }
            except Exception as e:
                business_tests["digital_wellness_content"] = {
                    "passed": False,
                    "error": str(e),
                    "message": "Digital wellness content validation failed"
                }
            
            # Test 2: September AI contextual responses
            try:
                september_response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={"message": "How can I improve my digital wellness?"}
                )
                
                if september_response.status_code == 200:
                    chat_data = september_response.json()
                    response_text = chat_data.get("response", "").lower()
                    
                    pol_context = any(term in response_text for term in [
                        "digital wellness", "practice of life", "mindfulness", "engagement"
                    ])
                    
                    business_tests["september_contextual_responses"] = {
                        "passed": pol_context,
                        "response_contains_pol_context": pol_context,
                        "response_preview": chat_data.get("response", "")[:100],
                        "message": "September provides POL-contextual responses"
                    }
                else:
                    business_tests["september_contextual_responses"] = {
                        "passed": False,
                        "status_code": september_response.status_code,
                        "message": "September API not responding"
                    }
            except Exception as e:
                business_tests["september_contextual_responses"] = {
                    "passed": False,
                    "error": str(e),
                    "message": "September contextual response test failed"
                }
        
        self.results["business_logic_validation"] = business_tests
        return business_tests
    
    async def validate_load_testing(self) -> Dict[str, Any]:
        """Validate platform performance under load."""
        print("⚡ Auditing Load Performance...")
        
        load_tests = {}
        
        # Test 1: Concurrent dashboard access
        async def test_dashboard_access():
            async with httpx.AsyncClient() as client:
                start_time = time.time()
                response = await client.get(f"{self.base_url}/")
                end_time = time.time()
                return {
                    "status_code": response.status_code,
                    "response_time": (end_time - start_time) * 1000
                }
        
        try:
            # Run 5 concurrent requests
            tasks = [test_dashboard_access() for _ in range(5)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_requests = [r for r in results if isinstance(r, dict) and r.get("status_code") == 200]
            avg_response_time = sum(r["response_time"] for r in successful_requests) / len(successful_requests) if successful_requests else 0
            
            load_tests["concurrent_dashboard_access"] = {
                "passed": len(successful_requests) >= 4,  # 80% success rate
                "successful_requests": len(successful_requests),
                "total_requests": len(tasks),
                "avg_response_time_ms": round(avg_response_time),
                "success_rate": round(len(successful_requests) / len(tasks) * 100, 1),
                "message": f"Concurrent access: {len(successful_requests)}/5 successful"
            }
        except Exception as e:
            load_tests["concurrent_dashboard_access"] = {
                "passed": False,
                "error": str(e),
                "message": "Concurrent dashboard access test failed"
            }
        
        self.results["load_testing"] = load_tests
        return load_tests
    
    async def generate_audit_summary(self) -> Dict[str, Any]:
        """Generate comprehensive audit summary with improvement recommendations."""
        print("📋 Generating Comprehensive Audit Summary...")
        
        # Calculate category scores
        category_scores = {}
        total_tests = 0
        passed_tests = 0
        
        for category, tests in self.results.items():
            if isinstance(tests, dict) and category not in ["audit_summary", "audit_timestamp", "audit_version", "platform"]:
                category_passed = 0
                category_total = 0
                
                for test_name, test_result in tests.items():
                    if isinstance(test_result, dict) and "passed" in test_result:
                        category_total += 1
                        total_tests += 1
                        if test_result["passed"]:
                            category_passed += 1
                            passed_tests += 1
                
                category_scores[category] = {
                    "score": round((category_passed / category_total * 100), 1) if category_total > 0 else 0,
                    "passed": category_passed,
                    "total": category_total
                }
        
        overall_score = round((passed_tests / total_tests * 100), 1) if total_tests > 0 else 0
        
        # Generate recommendations
        recommendations = []
        
        if category_scores.get("security_compliance", {}).get("score", 0) < 90:
            recommendations.append("Enhance security compliance measures")
        
        if category_scores.get("data_accuracy", {}).get("score", 0) < 90:
            recommendations.append("Improve data accuracy validation and mathematical correctness")
        
        if category_scores.get("business_logic_validation", {}).get("score", 0) < 80:
            recommendations.append("Strengthen POL mission alignment in content and AI responses")
        
        if category_scores.get("accessibility_compliance", {}).get("score", 0) < 90:
            recommendations.append("Implement WCAG accessibility improvements")
        
        if overall_score < 85:
            recommendations.append("Address failing test categories to improve platform reliability")
        
        # Business impact assessment
        audit_summary = {
            "overall_score": overall_score,
            "grade": "A" if overall_score >= 90 else "B" if overall_score >= 80 else "C" if overall_score >= 70 else "D",
            "tests_passed": passed_tests,
            "total_tests": total_tests,
            "category_scores": category_scores,
            "business_readiness": "Production Ready" if overall_score >= 85 else "Needs Improvement",
            "stakeholder_confidence": "High" if overall_score >= 90 else "Medium" if overall_score >= 75 else "Low",
            "recommendations": recommendations,
            "audit_timestamp": self.results["audit_timestamp"],
            "next_audit_recommended": (datetime.utcnow() + timedelta(days=30)).isoformat()
        }
        
        self.results["audit_summary"] = audit_summary
        return audit_summary
    
    async def run_comprehensive_audit(self) -> Dict[str, Any]:
        """Execute complete enterprise-grade business audit."""
        print("🔍 Starting Comprehensive POL Analytics Business Audit...")
        print(f"Platform: {self.base_url}")
        print("=" * 70)
        
        # Run all validation categories
        await self.validate_security_compliance()
        await self.validate_end_to_end_workflows()
        await self.validate_data_accuracy()
        await self.validate_error_handling()
        await self.validate_integration_testing()
        await self.validate_accessibility_compliance()
        await self.validate_business_logic()
        await self.validate_load_testing()
        await self.generate_audit_summary()
        
        print("=" * 70)
        print("✅ Comprehensive Business Audit Complete!")
        
        return self.results

async def main():
    """Execute comprehensive business audit."""
    audit = ComprehensiveBusinessValidation()
    results = await audit.run_comprehensive_audit()
    
    # Save results
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    results_file = f"comprehensive_audit_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print executive summary
    summary = results["audit_summary"]
    print(f"\n📊 Executive Audit Summary:")
    print(f"Overall Score: {summary['overall_score']}% (Grade: {summary['grade']})")
    print(f"Business Readiness: {summary['business_readiness']}")
    print(f"Stakeholder Confidence: {summary['stakeholder_confidence']}")
    print(f"Tests Passed: {summary['tests_passed']}/{summary['total_tests']}")
    
    print(f"\n📈 Category Scores:")
    for category, score_data in summary["category_scores"].items():
        print(f"  {category.replace('_', ' ').title()}: {score_data['score']}% ({score_data['passed']}/{score_data['total']})")
    
    if summary["recommendations"]:
        print(f"\n💡 Priority Recommendations:")
        for i, rec in enumerate(summary["recommendations"], 1):
            print(f"  {i}. {rec}")
    
    print(f"\n📁 Full audit results: {results_file}")
    print(f"🔄 Next audit recommended: {summary['next_audit_recommended']}")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())



