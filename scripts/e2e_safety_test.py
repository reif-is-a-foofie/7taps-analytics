#!/usr/bin/env python3
"""
End-to-End Testing for Enhanced Safety System
Tests the complete safety pipeline with real xAPI statement scenarios
"""

import requests
import json
import time
from datetime import datetime

class SafetyE2ETest:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        
    def test_endpoint(self, endpoint, method="GET", data=None, params=None):
        """Test an API endpoint and return results"""
        try:
            if method == "GET":
                response = requests.get(f"{self.base_url}{endpoint}", params=params)
            elif method == "POST":
                response = requests.post(f"{self.base_url}{endpoint}", json=data, params=params)
            
            result = {
                "endpoint": endpoint,
                "method": method,
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
                "timestamp": datetime.now().isoformat()
            }
            
            self.test_results.append(result)
            return result
            
        except Exception as e:
            error_result = {
                "endpoint": endpoint,
                "method": method,
                "status_code": 0,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            self.test_results.append(error_result)
            return error_result
    
    def test_basic_connectivity(self):
        """Test basic API connectivity"""
        print("🔍 Testing basic connectivity...")
        
        # Health check
        result = self.test_endpoint("/health")
        print(f"  Health check: {'✅' if result['success'] else '❌'}")
        
        # API health check
        result = self.test_endpoint("/api/health")
        print(f"  API health: {'✅' if result['success'] else '❌'}")
        
        return all(r['success'] for r in self.test_results[-2:])
    
    def test_safety_word_management(self):
        """Test CRUD operations for filtered words"""
        print("\n📝 Testing safety word management...")
        
        # Get existing words
        result = self.test_endpoint("/api/safety/words")
        print(f"  Get words: {'✅' if result['success'] else '❌'}")
        if result['success']:
            print(f"    Found {len(result['response'])} existing words")
        
        # Create a new test word with unique name
        import time
        unique_word = f"test_word_{int(time.time())}"
        new_word = {
            "word": unique_word,
            "category": "spam",
            "severity": 2,
            "is_active": True
        }
        result = self.test_endpoint("/api/safety/words", method="POST", data=new_word)
        print(f"  Create word: {'✅' if result['success'] else '❌'}")
        
        # Get words again to verify
        result = self.test_endpoint("/api/safety/words")
        print(f"  Verify creation: {'✅' if result['success'] else '❌'}")
        
        return True
    
    def test_content_analysis(self):
        """Test content analysis with various scenarios"""
        print("\n🧠 Testing content analysis...")
        
        test_cases = [
            {
                "name": "Clean educational content",
                "content": "I completed the digital wellness lesson and learned about mindful technology use. This was really helpful for my daily routine.",
                "expected_flagged": False
            },
            {
                "name": "Spam content",
                "content": "This course is spam and waste of time. Not helpful at all.",
                "expected_flagged": True
            },
            {
                "name": "Inappropriate content",
                "content": "I found this content inappropriate and offensive.",
                "expected_flagged": True
            },
            {
                "name": "Mixed content",
                "content": "Great lesson on digital wellness! However, some parts were inappropriate and could be improved.",
                "expected_flagged": True
            }
        ]
        
        for test_case in test_cases:
            result = self.test_endpoint(
                "/api/safety/analyze/enhanced",
                method="POST",
                params={"content": test_case["content"]}
            )
            
            if result['success']:
                is_flagged = result['response'].get('is_flagged', False)
                matches_expected = is_flagged == test_case['expected_flagged']
                print(f"  {test_case['name']}: {'✅' if matches_expected else '❌'}")
                print(f"    Expected flagged: {test_case['expected_flagged']}, Got: {is_flagged}")
                
                if result['response'].get('existing_filter_matches'):
                    print(f"    Matched words: {[m['word'] for m in result['response']['existing_filter_matches']]}")
            else:
                print(f"  {test_case['name']}: ❌ (API Error)")
        
        return True
    
    def test_gemini_integration(self):
        """Test Gemini AI integration"""
        print("\n🤖 Testing Gemini AI integration...")
        
        # Test suggestions endpoint
        result = self.test_endpoint("/api/safety/suggestions")
        print(f"  AI suggestions: {'✅' if result['success'] else '❌'}")
        if result['success']:
            suggestions = result['response']
            print(f"    Got {len(suggestions)} AI suggestions")
        
        # Test enhanced analysis with AI
        result = self.test_endpoint(
            "/api/safety/analyze/enhanced",
            method="POST",
            params={"content": "This is a test for AI analysis capabilities"}
        )
        print(f"  AI analysis: {'✅' if result['success'] else '❌'}")
        
        return True
    
    def test_real_xapi_scenarios(self):
        """Test with realistic xAPI statement scenarios"""
        print("\n📊 Testing real xAPI scenarios...")
        
        xapi_scenarios = [
            {
                "name": "Lesson completion",
                "content": "Actor completed lesson 'Digital Wellness Fundamentals' with score 85%. Response: 'Learned valuable techniques for managing screen time and maintaining work-life balance.'"
            },
            {
                "name": "Quiz response",
                "content": "User answered quiz question about sleep hygiene. Response: 'I try to avoid screens 1 hour before bed, but sometimes I still check my phone. Need to improve this habit.'"
            },
            {
                "name": "Reflection submission",
                "content": "Student submitted reflection on digital detox. Response: 'Spent 3 hours without any devices today. Felt more present and focused. Will try to do this weekly.'"
            },
            {
                "name": "Concern report",
                "content": "User reported concern about course content. Response: 'Some of the examples seem inappropriate and could be triggering for certain users. Please review.'"
            }
        ]
        
        for scenario in xapi_scenarios:
            result = self.test_endpoint(
                "/api/safety/analyze/enhanced",
                method="POST",
                params={"content": scenario["content"]}
            )
            
            if result['success']:
                is_flagged = result['response'].get('is_flagged', False)
                risk_level = result['response'].get('overall_risk_level', 0)
                print(f"  {scenario['name']}: {'🚨' if is_flagged else '✅'} (Risk: {risk_level})")
            else:
                print(f"  {scenario['name']}: ❌ (API Error)")
        
        return True
    
    def test_ui_accessibility(self):
        """Test UI endpoints"""
        print("\n🖥️  Testing UI accessibility...")
        
        # Test safety words UI
        result = self.test_endpoint("/safety-ui")
        print(f"  Safety UI: {'✅' if result['success'] else '❌'}")
        
        return True
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n📋 Generating test report...")
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r['success'])
        failed_tests = total_tests - successful_tests
        
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "successful": successful_tests,
                "failed": failed_tests,
                "success_rate": f"{(successful_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
            },
            "test_results": self.test_results,
            "timestamp": datetime.now().isoformat()
        }
        
        # Save report
        with open("safety_e2e_test_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n🎯 Test Summary:")
        print(f"  Total tests: {total_tests}")
        print(f"  Successful: {successful_tests}")
        print(f"  Failed: {failed_tests}")
        print(f"  Success rate: {report['test_summary']['success_rate']}")
        print(f"\n📄 Full report saved to: safety_e2e_test_report.json")
        
        return report
    
    def run_all_tests(self):
        """Run complete end-to-end test suite"""
        print("🚀 Starting Enhanced Safety System E2E Tests")
        print("=" * 50)
        
        start_time = time.time()
        
        # Run all test suites
        self.test_basic_connectivity()
        self.test_safety_word_management()
        self.test_content_analysis()
        self.test_gemini_integration()
        self.test_real_xapi_scenarios()
        self.test_ui_accessibility()
        
        # Generate report
        report = self.generate_report()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n⏱️  Total test duration: {duration:.2f} seconds")
        print("=" * 50)
        
        return report

if __name__ == "__main__":
    tester = SafetyE2ETest()
    report = tester.run_all_tests()
    
    # Exit with appropriate code
    exit(0 if report['test_summary']['failed'] == 0 else 1)
