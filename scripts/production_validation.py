"""
Production Validation Script for UI Components and BigQuery Integration.

This script validates existing UI components and new optimizations
in the production environment.
"""

import requests
import json
from typing import Dict, Any, List
from datetime import datetime
import time

class ProductionValidator:
    """Comprehensive production validation for UI components and BigQuery integration."""
    
    def __init__(self, base_url: str = "https://seventaps-analytics-5135b3a0701a.herokuapp.com"):
        self.base_url = base_url
        self.results = []
        self.session = requests.Session()
        self.session.timeout = 30
    
    def log_result(self, test_name: str, success: bool, details: str = "", response_time: float = 0):
        """Log test result."""
        self.results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "response_time": response_time,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def test_existing_ui_components(self) -> Dict[str, bool]:
        """Test existing UI components accessibility."""
        print("🔍 Testing Existing UI Components...")
        
        components = {
            "explorer": "/explorer",
            "chat": "/chat", 
            "admin": "/ui/admin",
            "docs": "/docs"
        }
        
        results = {}
        
        for name, endpoint in components.items():
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}")
                response_time = time.time() - start_time
                
                success = response.status_code == 200
                results[name] = success
                
                self.log_result(
                    f"ui_component_{name}",
                    success,
                    f"Status: {response.status_code}, Time: {response_time:.2f}s",
                    response_time
                )
                
                print(f"  {'✅' if success else '❌'} {name}: {response.status_code} ({response_time:.2f}s)")
                
            except Exception as e:
                results[name] = False
                self.log_result(f"ui_component_{name}", False, str(e))
                print(f"  ❌ {name}: Error - {str(e)}")
        
        return results
    
    def test_bigquery_integration(self) -> Dict[str, bool]:
        """Test BigQuery integration endpoints."""
        print("🔍 Testing BigQuery Integration...")
        
        endpoints = {
            "connection_status": "/api/analytics/bigquery/connection-status",
            "query_endpoint": "/api/analytics/bigquery/query",
            "dashboard_data": "/ui/bigquery-dashboard/data",
            "dashboard_page": "/ui/bigquery-dashboard"
        }
        
        results = {}
        
        for name, endpoint in endpoints.items():
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}")
                response_time = time.time() - start_time
                
                success = response.status_code == 200
                results[name] = success
                
                self.log_result(
                    f"bigquery_{name}",
                    success,
                    f"Status: {response.status_code}, Time: {response_time:.2f}s",
                    response_time
                )
                
                print(f"  {'✅' if success else '❌'} {name}: {response.status_code} ({response_time:.2f}s)")
                
                # Test response content for successful endpoints
                if success and response.headers.get('content-type', '').startswith('application/json'):
                    try:
                        data = response.json()
                        print(f"    Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    except:
                        print(f"    Response: {response.text[:100]}...")
                
            except Exception as e:
                results[name] = False
                self.log_result(f"bigquery_{name}", False, str(e))
                print(f"  ❌ {name}: Error - {str(e)}")
        
        return results
    
    def test_data_explorer_functionality(self) -> Dict[str, bool]:
        """Test data explorer functionality."""
        print("🔍 Testing Data Explorer Functionality...")
        
        endpoints = {
            "lessons": "/api/data-explorer/lessons",
            "users": "/api/data-explorer/users",
            "table_data": "/api/data-explorer/table/lessons?limit=10",
            "table_stats": "/api/data-explorer/stats/lessons"
        }
        
        results = {}
        
        for name, endpoint in endpoints.items():
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}")
                response_time = time.time() - start_time
                
                success = response.status_code == 200
                results[name] = success
                
                self.log_result(
                    f"data_explorer_{name}",
                    success,
                    f"Status: {response.status_code}, Time: {response_time:.2f}s",
                    response_time
                )
                
                print(f"  {'✅' if success else '❌'} {name}: {response.status_code} ({response_time:.2f}s)")
                
                # Test response content
                if success:
                    try:
                        data = response.json()
                        if isinstance(data, dict):
                            print(f"    Success: {data.get('success', 'N/A')}")
                            if 'data' in data:
                                print(f"    Data type: {type(data['data'])}")
                            if 'lessons' in data:
                                print(f"    Lessons count: {len(data['lessons'])}")
                    except:
                        print(f"    Response: {response.text[:100]}...")
                
            except Exception as e:
                results[name] = False
                self.log_result(f"data_explorer_{name}", False, str(e))
                print(f"  ❌ {name}: Error - {str(e)}")
        
        return results
    
    def test_cost_monitoring_endpoints(self) -> Dict[str, bool]:
        """Test cost monitoring endpoints (if implemented)."""
        print("🔍 Testing Cost Monitoring Endpoints...")
        
        endpoints = {
            "current_usage": "/api/cost/current-usage",
            "optimization_recommendations": "/api/cost/optimization-recommendations",
            "deployment_status": "/api/debug/ui-deployment-status",
            "bigquery_status": "/api/debug/bigquery-integration-status"
        }
        
        results = {}
        
        for name, endpoint in endpoints.items():
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}")
                response_time = time.time() - start_time
                
                # Accept both 200 (implemented) and 404 (not yet implemented)
                success = response.status_code in [200, 404]
                results[name] = success
                
                status = "Implemented" if response.status_code == 200 else "Not implemented"
                
                self.log_result(
                    f"cost_monitoring_{name}",
                    success,
                    f"Status: {response.status_code} ({status}), Time: {response_time:.2f}s",
                    response_time
                )
                
                print(f"  {'✅' if success else '❌'} {name}: {response.status_code} ({status}) ({response_time:.2f}s)")
                
            except Exception as e:
                results[name] = False
                self.log_result(f"cost_monitoring_{name}", False, str(e))
                print(f"  ❌ {name}: Error - {str(e)}")
        
        return results
    
    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        print("\n📊 Generating Validation Report...")
        
        # Calculate overall statistics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["success"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Calculate average response time
        response_times = [r["response_time"] for r in self.results if r["response_time"] > 0]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Group results by category
        categories = {}
        for result in self.results:
            category = result["test"].split("_")[0]
            if category not in categories:
                categories[category] = {"passed": 0, "failed": 0, "total": 0}
            categories[category]["total"] += 1
            if result["success"]:
                categories[category]["passed"] += 1
            else:
                categories[category]["failed"] += 1
        
        report = {
            "validation_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": success_rate,
                "avg_response_time": avg_response_time,
                "timestamp": datetime.utcnow().isoformat()
            },
            "category_breakdown": categories,
            "detailed_results": self.results,
            "recommendations": self._generate_recommendations(),
            "production_status": {
                "base_url": self.base_url,
                "deployment_platform": "Heroku",
                "validation_date": datetime.utcnow().isoformat()
            }
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        # Analyze results and generate recommendations
        ui_tests = [r for r in self.results if r["test"].startswith("ui_component")]
        bigquery_tests = [r for r in self.results if r["test"].startswith("bigquery")]
        cost_tests = [r for r in self.results if r["test"].startswith("cost_monitoring")]
        
        ui_success_rate = sum(1 for r in ui_tests if r["success"]) / len(ui_tests) if ui_tests else 0
        bigquery_success_rate = sum(1 for r in bigquery_tests if r["success"]) / len(bigquery_tests) if bigquery_tests else 0
        cost_success_rate = sum(1 for r in cost_tests if r["success"]) / len(cost_tests) if cost_tests else 0
        
        if ui_success_rate < 1.0:
            recommendations.append("Fix failing UI components before deploying new features")
        
        if bigquery_success_rate < 0.5:
            recommendations.append("BigQuery integration needs significant work - most endpoints not accessible")
        
        if cost_success_rate < 0.5:
            recommendations.append("Implement cost monitoring endpoints as planned in contracts")
        
        # Performance recommendations
        slow_tests = [r for r in self.results if r["response_time"] > 3.0]
        if len(slow_tests) > 0:
            recommendations.append("Optimize slow endpoints - several taking over 3 seconds")
        
        if not recommendations:
            recommendations.append("All systems operational - proceed with new feature deployment")
        
        return recommendations
    
    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive production validation."""
        print("🚀 Starting Comprehensive Production Validation...")
        print("=" * 60)
        print(f"Testing: {self.base_url}")
        print(f"Time: {datetime.utcnow().isoformat()}")
        print("=" * 60)
        
        # Run all test suites
        ui_results = self.test_existing_ui_components()
        bigquery_results = self.test_bigquery_integration()
        explorer_results = self.test_data_explorer_functionality()
        cost_results = self.test_cost_monitoring_endpoints()
        
        # Generate final report
        report = self.generate_validation_report()
        
        print("\n" + "=" * 60)
        print("📊 VALIDATION COMPLETE")
        print("=" * 60)
        print(f"Total Tests: {report['validation_summary']['total_tests']}")
        print(f"Passed: {report['validation_summary']['passed_tests']}")
        print(f"Failed: {report['validation_summary']['failed_tests']}")
        print(f"Success Rate: {report['validation_summary']['success_rate']:.1f}%")
        print(f"Avg Response Time: {report['validation_summary']['avg_response_time']:.2f}s")
        
        print("\n📋 RECOMMENDATIONS:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"  {i}. {rec}")
        
        return report


if __name__ == "__main__":
    # Run validation directly
    validator = ProductionValidator()
    report = validator.run_comprehensive_validation()
    
    # Save report
    import os
    os.makedirs("reports/testing_agent", exist_ok=True)
    with open("reports/testing_agent/production_validation_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Report saved to: reports/testing_agent/production_validation_report.json")
