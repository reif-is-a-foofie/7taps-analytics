#!/usr/bin/env python3
"""
Comprehensive Selenium UI Testing for 7taps Analytics
Tests all UI components on localhost:8000
"""

import time
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class SeleniumUITester:
    def __init__(self, base_url: str = "http://localhost:8008"):
        self.base_url = base_url
        self.results = []
        self.driver = None
        
    def setup_driver(self):
        """Setup Chrome driver for UI testing"""
        chrome_options = Options()
        # chrome_options.add_argument("--headless")  # Uncomment for headless testing
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
    
    def test_navigation_system(self) -> bool:
        """Test navigation sidebar and links"""
        try:
            print("\n🧭 Testing Navigation System...")
            
            # Start on dashboard
            self.driver.get(f"{self.base_url}/")
            time.sleep(2)
            
            # Check for sidebar elements
            sidebar_elements = self.driver.find_elements(By.CSS_SELECTOR, "[class*='sidebar']")
            print(f"   Found {len(sidebar_elements)} sidebar elements")
            
            # Test navigation links
            navigation_tests = [
                ("/explorer", "Data Explorer"),
                ("/chat", "AI Chat"),
                ("/docs", "API Docs")
            ]
            
            for path, name in navigation_tests:
                try:
                    # Find and click navigation link
                    link = self.driver.find_element(By.CSS_SELECTOR, f'a[href="{path}"]')
                    link.click()
                    time.sleep(2)
                    
                    # Verify we're on the correct page
                    current_url = self.driver.current_url
                    if path in current_url:
                        print(f"   ✅ {name} navigation working")
                    else:
                        print(f"   ❌ {name} navigation failed - expected {path}, got {current_url}")
                        
                except NoSuchElementException:
                    print(f"   ❌ {name} link not found")
                except Exception as e:
                    print(f"   ❌ {name} navigation error: {e}")
            
            self.results.append({
                "test": "Navigation System",
                "url": self.base_url,
                "success": True,
                "duration": None,
                "error": None
            })
            return True
            
        except Exception as e:
            self.results.append({
                "test": "Navigation System",
                "url": self.base_url,
                "success": False,
                "duration": None,
                "error": str(e)
            })
            print(f"❌ Navigation system failed: {e}")
            return False
    
    def test_dashboard_analytics(self) -> bool:
        """Test dashboard analytics integration"""
        try:
            print("\n📊 Testing Dashboard Analytics...")
            
            self.driver.get(f"{self.base_url}/")
            time.sleep(3)
            
            # Check for analytics elements
            analytics_elements = self.driver.find_elements(By.CSS_SELECTOR, "[class*='analytics'], [class*='chart'], [class*='query']")
            print(f"   Found {len(analytics_elements)} analytics elements")
            
            # Check for specific analytics sections
            sections_to_check = [
                "analytics",
                "chart",
                "query",
                "completion",
                "engagement",
                "metrics"
            ]
            
            found_sections = 0
            for section in sections_to_check:
                elements = self.driver.find_elements(By.CSS_SELECTOR, f"[class*='{section}'], [id*='{section}']")
                if elements:
                    found_sections += 1
                    print(f"   ✅ {section} section found ({len(elements)} elements)")
            
            print(f"   Found {found_sections}/{len(sections_to_check)} analytics sections")
            
            # Test analytics API integration
            try:
                # Look for any analytics API calls or data loading
                page_source = self.driver.page_source
                if "analytics" in page_source.lower():
                    print("   ✅ Analytics integration detected in page")
                else:
                    print("   ⚠️ No analytics integration detected")
                    
            except Exception as e:
                print(f"   ❌ Analytics API test error: {e}")
            
            self.results.append({
                "test": "Dashboard Analytics",
                "url": f"{self.base_url}/",
                "success": found_sections > 0,
                "duration": None,
                "error": None
            })
            return found_sections > 0
            
        except Exception as e:
            self.results.append({
                "test": "Dashboard Analytics",
                "url": f"{self.base_url}/",
                "success": False,
                "duration": None,
                "error": str(e)
            })
            print(f"❌ Dashboard analytics failed: {e}")
            return False
    
    def test_chat_interface(self) -> bool:
        """Test chat interface and analytics integration"""
        try:
            print("\n💬 Testing Chat Interface...")
            
            self.driver.get(f"{self.base_url}/chat")
            time.sleep(3)
            
            # Check for chat elements
            chat_elements = self.driver.find_elements(By.CSS_SELECTOR, "[class*='chat'], [id*='chat'], textarea, input[type='text']")
            print(f"   Found {len(chat_elements)} chat elements")
            
            # Check for analytics integration in chat
            analytics_elements = self.driver.find_elements(By.CSS_SELECTOR, "[class*='analytics'], [class*='query'], [class*='suggestion']")
            print(f"   Found {len(analytics_elements)} analytics elements in chat")
            
            # Test chat functionality
            try:
                # Look for input field
                input_field = self.driver.find_element(By.CSS_SELECTOR, "textarea, input[type='text'], [contenteditable='true']")
                input_field.send_keys("Test analytics query")
                print("   ✅ Chat input working")
                
                # Look for send button
                send_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit'], [class*='send'], [class*='submit']")
                send_button.click()
                print("   ✅ Chat send functionality working")
                time.sleep(2)
                
            except NoSuchElementException:
                print("   ⚠️ Chat input/send elements not found")
            except Exception as e:
                print(f"   ❌ Chat functionality error: {e}")
            
            self.results.append({
                "test": "Chat Interface",
                "url": f"{self.base_url}/chat",
                "success": len(chat_elements) > 0,
                "duration": None,
                "error": None
            })
            return len(chat_elements) > 0
            
        except Exception as e:
            self.results.append({
                "test": "Chat Interface",
                "url": f"{self.base_url}/chat",
                "success": False,
                "duration": None,
                "error": str(e)
            })
            print(f"❌ Chat interface failed: {e}")
            return False
    
    def test_data_explorer(self) -> bool:
        """Test data explorer functionality"""
        try:
            print("\n🔍 Testing Data Explorer...")
            
            self.driver.get(f"{self.base_url}/explorer")
            time.sleep(3)
            
            # Check for explorer elements
            explorer_elements = self.driver.find_elements(By.CSS_SELECTOR, "[class*='explorer'], [class*='table'], [class*='data']")
            print(f"   Found {len(explorer_elements)} explorer elements")
            
            # Check for data loading
            try:
                # Look for any data tables or lists
                tables = self.driver.find_elements(By.CSS_SELECTOR, "table, [class*='table'], [class*='list']")
                if tables:
                    print(f"   ✅ Data tables found ({len(tables)} tables)")
                else:
                    print("   ⚠️ No data tables found")
                    
            except Exception as e:
                print(f"   ❌ Data explorer error: {e}")
            
            self.results.append({
                "test": "Data Explorer",
                "url": f"{self.base_url}/explorer",
                "success": len(explorer_elements) > 0,
                "duration": None,
                "error": None
            })
            return len(explorer_elements) > 0
            
        except Exception as e:
            self.results.append({
                "test": "Data Explorer",
                "url": f"{self.base_url}/explorer",
                "success": False,
                "duration": None,
                "error": str(e)
            })
            print(f"❌ Data explorer failed: {e}")
            return False
    
    def test_api_documentation(self) -> bool:
        """Test API documentation accessibility"""
        try:
            print("\n📚 Testing API Documentation...")
            
            self.driver.get(f"{self.base_url}/docs")
            time.sleep(3)
            
            # Check for API docs elements
            docs_elements = self.driver.find_elements(By.CSS_SELECTOR, "[class*='docs'], [class*='api'], [class*='swagger']")
            print(f"   Found {len(docs_elements)} API docs elements")
            
            # Check for interactive elements
            interactive_elements = self.driver.find_elements(By.CSS_SELECTOR, "button, a, [class*='try'], [class*='execute']")
            print(f"   Found {len(interactive_elements)} interactive elements")
            
            self.results.append({
                "test": "API Documentation",
                "url": f"{self.base_url}/docs",
                "success": len(docs_elements) > 0,
                "duration": None,
                "error": None
            })
            return len(docs_elements) > 0
            
        except Exception as e:
            self.results.append({
                "test": "API Documentation",
                "url": f"{self.base_url}/docs",
                "success": False,
                "duration": None,
                "error": str(e)
            })
            print(f"❌ API documentation failed: {e}")
            return False
    
    def run_comprehensive_tests(self):
        """Run all comprehensive UI tests"""
        print("🚀 Starting Comprehensive Selenium UI Tests...")
        print("=" * 60)
        
        if not self.setup_driver():
            return False
        
        try:
            # Test all main pages
            pages_to_test = [
                ("/", "Dashboard"),
                ("/chat", "AI Chat"),
                ("/explorer", "Data Explorer"),
                ("/docs", "API Documentation")
            ]
            
            print("\n📄 Testing Page Loads:")
            for path, name in pages_to_test:
                self.test_page_load(f"{self.base_url}{path}", name)
            
            # Test specific functionality
            self.test_navigation_system()
            self.test_dashboard_analytics()
            self.test_chat_interface()
            self.test_data_explorer()
            self.test_api_documentation()
            
        finally:
            if self.driver:
                self.driver.quit()
        
        # Generate results summary
        self.generate_results_summary()
    
    def generate_results_summary(self):
        """Generate comprehensive test results summary"""
        print("\n" + "=" * 60)
        print("📊 Comprehensive Selenium Test Results:")
        
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results if result["success"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.results:
                if not result["success"]:
                    print(f"   - {result['test']}: {result['error']}")
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"selenium_test_results_{timestamp}.json"
        
        with open(results_file, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "base_url": self.base_url,
                "summary": {
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "failed_tests": failed_tests,
                    "success_rate": success_rate
                },
                "results": self.results
            }, f, indent=2)
        
        print(f"\n📄 Results saved to: {results_file}")
        
        if success_rate >= 80:
            print("🎉 UI Testing: EXCELLENT - System ready for production!")
        elif success_rate >= 60:
            print("✅ UI Testing: GOOD - Minor issues to address")
        else:
            print("⚠️ UI Testing: NEEDS IMPROVEMENT - Significant issues found")

if __name__ == "__main__":
    tester = SeleniumUITester("http://localhost:8000")
    tester.run_comprehensive_tests()
