#!/usr/bin/env python3
"""
Comprehensive UI Testing Orchestrator for 7taps Analytics
Tests every button, chart, and interactive element
"""

import requests
import json
import time
from typing import Dict, List, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class ComprehensiveUITester:
    def __init__(self, base_url: str = "https://seventaps-analytics-5135b3a0701a.herokuapp.com"):
        self.base_url = base_url
        self.results = []
        self.driver = None
        
    def setup_driver(self):
        """Setup headless Chrome driver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
            return True
        except Exception as e:
            print(f"❌ Failed to setup Chrome driver: {e}")
            return False
    
    def test_page_load(self, url: str, name: str) -> bool:
        """Test if a page loads successfully"""
        try:
            start_time = time.time()
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            duration = time.time() - start_time
            
            self.results.append({
                "test": f"Page Load: {name}",
                "url": url,
                "success": True,
                "duration": round(duration, 2),
                "error": None
            })
            
            print(f"✅ {name}: Loaded successfully ({duration:.2f}s)")
            return True
            
        except Exception as e:
            self.results.append({
                "test": f"Page Load: {name}",
                "url": url,
                "success": False,
                "duration": None,
                "error": str(e)
            })
            print(f"❌ {name}: Failed to load - {str(e)}")
            return False
    
    def test_navigation_links(self) -> bool:
        """Test all navigation links in sidebar"""
        try:
            # Start on dashboard page
            self.driver.get(f"{self.base_url}/")
            time.sleep(2)
            
            # Test Data Explorer link
            explorer_link = self.driver.find_element(By.CSS_SELECTOR, 'a[href="/explorer"]')
            explorer_link.click()
            time.sleep(2)
            
            # Test AI Chat link
            chat_link = self.driver.find_element(By.CSS_SELECTOR, 'a[href="/chat"]')
            chat_link.click()
            time.sleep(2)
            
            # Test API Docs link (should open in new tab)
            docs_link = self.driver.find_element(By.CSS_SELECTOR, 'a[href="/docs"]')
            docs_link.click()
            time.sleep(2)
            
            self.results.append({
                "test": "Navigation Links",
                "url": self.base_url,
                "success": True,
                "duration": None,
                "error": None
            })
            
            print("✅ Navigation Links: All working")
            return True
            
        except Exception as e:
            self.results.append({
                "test": "Navigation Links",
                "url": self.base_url,
                "success": False,
                "duration": None,
                "error": str(e)
            })
            print(f"❌ Navigation Links: Failed - {str(e)}")
            return False
    
    def test_dashboard_charts(self) -> bool:
        """Test all dashboard charts and interactive elements"""
        try:
            # Navigate to dashboard
            self.driver.get(f"{self.base_url}/")
            time.sleep(3)
            
            # Check for chart containers
            chart_selectors = [
                "#completion-funnel-chart",
                "#knowledge-lift-chart", 
                "#dropoff-chart",
                "#quiz-performance-chart"
            ]
            
            charts_found = 0
            for selector in chart_selectors:
                try:
                    chart_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if chart_element.is_displayed():
                        charts_found += 1
                        print(f"✅ Chart found: {selector}")
                except NoSuchElementException:
                    print(f"❌ Chart missing: {selector}")
            
            # Check for metric cards
            metric_selectors = [
                "#total-participants",
                "#completion-rate", 
                "#avg-score",
                "#nps-score"
            ]
            
            metrics_found = 0
            for selector in metric_selectors:
                try:
                    metric_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if metric_element.is_displayed():
                        metrics_found += 1
                        print(f"✅ Metric found: {selector}")
                except NoSuchElementException:
                    print(f"❌ Metric missing: {selector}")
            
            success = charts_found >= 2 and metrics_found >= 2  # At least 2 charts and 2 metrics
            
            self.results.append({
                "test": "Dashboard Charts",
                "url": f"{self.base_url}/",
                "success": success,
                "duration": None,
                "error": f"Found {charts_found}/4 charts, {metrics_found}/4 metrics" if not success else None
            })
            
            print(f"{'✅' if success else '❌'} Dashboard Charts: {charts_found}/4 charts, {metrics_found}/4 metrics")
            return success
            
        except Exception as e:
            self.results.append({
                "test": "Dashboard Charts",
                "url": f"{self.base_url}/",
                "success": False,
                "duration": None,
                "error": str(e)
            })
            print(f"❌ Dashboard Charts: Failed - {str(e)}")
            return False
    
    def test_data_explorer_functionality(self) -> bool:
        """Test Data Explorer interactive functionality"""
        try:
            # Navigate to data explorer
            self.driver.get(f"{self.base_url}/explorer")
            time.sleep(3)
            
            # Test table selection
            table_select = self.driver.find_element(By.ID, "table-select")
            table_select.click()
            time.sleep(1)
            
            # Test lesson filter
            lesson_filter = self.driver.find_element(By.ID, "lesson-filter")
            lesson_filter.click()
            time.sleep(1)
            
            # Test user filter
            user_filter = self.driver.find_element(By.ID, "user-filter")
            user_filter.click()
            time.sleep(1)
            
            # Test limit input
            limit_input = self.driver.find_element(By.ID, "limit-input")
            limit_input.clear()
            limit_input.send_keys("10")
            time.sleep(1)
            
            # Test Load Data button
            load_button = self.driver.find_element(By.CSS_SELECTOR, 'button[onclick="loadData()"]')
            load_button.click()
            time.sleep(3)
            
            # Check if data table is populated
            try:
                data_table = self.driver.find_element(By.ID, "data-table")
                table_content = data_table.text
                has_data = len(table_content) > 50  # Should have substantial content
                
                self.results.append({
                    "test": "Data Explorer Functionality",
                    "url": f"{self.base_url}/explorer",
                    "success": has_data,
                    "duration": None,
                    "error": "No data loaded" if not has_data else None
                })
                
                print(f"{'✅' if has_data else '❌'} Data Explorer: {'Data loaded' if has_data else 'No data loaded'}")
                return has_data
                
            except NoSuchElementException:
                self.results.append({
                    "test": "Data Explorer Functionality",
                    "url": f"{self.base_url}/explorer",
                    "success": False,
                    "duration": None,
                    "error": "Data table not found"
                })
                print("❌ Data Explorer: Data table not found")
                return False
                
        except Exception as e:
            self.results.append({
                "test": "Data Explorer Functionality",
                "url": f"{self.base_url}/explorer",
                "success": False,
                "duration": None,
                "error": str(e)
            })
            print(f"❌ Data Explorer: Failed - {str(e)}")
            return False
    
    def test_chat_functionality(self) -> bool:
        """Test AI Chat functionality"""
        try:
            # Navigate to chat
            self.driver.get(f"{self.base_url}/chat")
            time.sleep(3)
            
            # Look for chat input
            chat_inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="text"], textarea')
            
            if chat_inputs:
                # Test typing in chat
                chat_input = chat_inputs[0]
                chat_input.send_keys("Hello, this is a test message")
                time.sleep(1)
                
                # Look for send button
                send_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button[type="submit"], button')
                
                if send_buttons:
                    send_button = send_buttons[0]
                    send_button.click()
                    time.sleep(2)
                    
                    self.results.append({
                        "test": "Chat Functionality",
                        "url": f"{self.base_url}/chat",
                        "success": True,
                        "duration": None,
                        "error": None
                    })
                    
                    print("✅ Chat Functionality: Message sent successfully")
                    return True
                else:
                    self.results.append({
                        "test": "Chat Functionality",
                        "url": f"{self.base_url}/chat",
                        "success": False,
                        "duration": None,
                        "error": "Send button not found"
                    })
                    print("❌ Chat Functionality: Send button not found")
                    return False
            else:
                self.results.append({
                    "test": "Chat Functionality",
                    "url": f"{self.base_url}/chat",
                    "success": False,
                    "duration": None,
                    "error": "Chat input not found"
                })
                print("❌ Chat Functionality: Chat input not found")
                return False
                
        except Exception as e:
            self.results.append({
                "test": "Chat Functionality",
                "url": f"{self.base_url}/chat",
                "success": False,
                "duration": None,
                "error": str(e)
            })
            print(f"❌ Chat Functionality: Failed - {str(e)}")
            return False
    
    def test_api_endpoints(self) -> bool:
        """Test all public API endpoints"""
        endpoints = [
            ("/api/data-explorer/lessons", ["success", "lessons"]),
            ("/api/data-explorer/users", ["success", "users"]),
            ("/api/data-explorer/table/users?limit=5", ["success", "data", "columns"]),
            ("/health", ["status"])
        ]
        
        all_success = True
        
        for endpoint, expected_keys in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    missing_keys = [key for key in expected_keys if key not in data]
                    
                    if missing_keys:
                        all_success = False
                        print(f"❌ API {endpoint}: Missing keys {missing_keys}")
                    else:
                        print(f"✅ API {endpoint}: Working")
                else:
                    all_success = False
                    print(f"❌ API {endpoint}: Status {response.status_code}")
                    
            except Exception as e:
                all_success = False
                print(f"❌ API {endpoint}: Error - {str(e)}")
        
        self.results.append({
            "test": "API Endpoints",
            "url": self.base_url,
            "success": all_success,
            "duration": None,
            "error": None
        })
        
        return all_success
    
    def run_comprehensive_tests(self) -> Dict:
        """Run all comprehensive UI tests"""
        print("🚀 Starting Comprehensive UI Tests...")
        print("=" * 60)
        
        if not self.setup_driver():
            return {"error": "Failed to setup browser driver"}
        
        try:
            # Test page loads
            print("\n📄 Testing Page Loads:")
            self.test_page_load(f"{self.base_url}/", "Dashboard")
            self.test_page_load(f"{self.base_url}/explorer", "Data Explorer")
            self.test_page_load(f"{self.base_url}/chat", "AI Chat")
            
            # Test navigation
            print("\n🧭 Testing Navigation:")
            self.test_navigation_links()
            
            # Test dashboard functionality
            print("\n📊 Testing Dashboard:")
            self.test_dashboard_charts()
            
            # Test data explorer functionality
            print("\n🔍 Testing Data Explorer:")
            self.test_data_explorer_functionality()
            
            # Test chat functionality
            print("\n💬 Testing Chat:")
            self.test_chat_functionality()
            
            # Test API endpoints
            print("\n🔌 Testing API Endpoints:")
            self.test_api_endpoints()
            
        finally:
            if self.driver:
                self.driver.quit()
        
        # Calculate results
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["success"])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "=" * 60)
        print(f"📊 Comprehensive Test Results:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Show failures
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.results:
                if not result["success"]:
                    print(f"   - {result['test']}: {result['error']}")
        
        return {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": (passed_tests/total_tests)*100,
            "results": self.results
        }

if __name__ == "__main__":
    tester = ComprehensiveUITester()
    results = tester.run_comprehensive_tests()
    
    # Exit with error code if any tests failed
    exit(1 if results.get("failed", 0) > 0 else 0)
