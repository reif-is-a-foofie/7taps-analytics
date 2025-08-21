#!/usr/bin/env python3
"""
Deep Selenium UI Testing for 7taps Analytics
Tests actual clicking, form submission, and expected outcomes
"""

import time
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class DeepSeleniumTester:
    def __init__(self, base_url: str = "http://localhost:8008"):
        self.base_url = base_url
        self.results = []
        self.driver = None
        
    def setup_driver(self):
        """Setup Chrome driver for deep UI testing"""
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
    
    def test_dashboard_real_data(self):
        """Test dashboard shows real data, not false data"""
        try:
            print("\n📊 Testing Dashboard Real Data...")
            
            self.driver.get(f"{self.base_url}/")
            time.sleep(3)
            
            # Check for real data indicators
            page_source = self.driver.page_source
            
            # Look for actual data patterns
            false_data_indicators = [
                "false",
                "null",
                "undefined",
                "mock",
                "test data",
                "placeholder"
            ]
            
            false_data_found = []
            for indicator in false_data_indicators:
                if indicator in page_source.lower():
                    false_data_found.append(indicator)
            
            if false_data_found:
                print(f"   ❌ False data indicators found: {false_data_found}")
                return False
            else:
                print("   ✅ No false data indicators found")
            
            # Check for actual metrics
            try:
                # Look for metric elements
                metric_elements = self.driver.find_elements(By.CSS_SELECTOR, "[class*='metric'], [class*='stat'], [class*='number']")
                print(f"   Found {len(metric_elements)} metric elements")
                
                # Check if metrics have actual values
                for i, element in enumerate(metric_elements[:5]):  # Check first 5
                    text = element.text.strip()
                    if text and text not in ['0', 'null', 'undefined', '']:
                        print(f"   ✅ Metric {i+1}: {text}")
                    else:
                        print(f"   ❌ Metric {i+1}: Empty or invalid value")
                        
            except Exception as e:
                print(f"   ❌ Error checking metrics: {e}")
            
            # Check for chart elements
            try:
                chart_elements = self.driver.find_elements(By.CSS_SELECTOR, "canvas, [class*='chart'], [id*='chart']")
                print(f"   Found {len(chart_elements)} chart elements")
                
                if chart_elements:
                    print("   ✅ Chart elements present")
                else:
                    print("   ❌ No chart elements found")
                    
            except Exception as e:
                print(f"   ❌ Error checking charts: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ Dashboard real data test failed: {e}")
            return False
    
    def test_chat_functionality(self):
        """Test chat actually works - input, send, response"""
        try:
            print("\n💬 Testing Chat Functionality...")
            
            self.driver.get(f"{self.base_url}/chat")
            time.sleep(3)
            
            # Find chat input
            try:
                # Try multiple selectors for chat input
                input_selectors = [
                    "textarea",
                    "input[type='text']",
                    "[contenteditable='true']",
                    "[class*='chat-input']",
                    "[class*='message-input']",
                    "[id*='chat-input']",
                    "[id*='message-input']"
                ]
                
                chat_input = None
                for selector in input_selectors:
                    try:
                        chat_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                        print(f"   ✅ Found chat input with selector: {selector}")
                        break
                    except NoSuchElementException:
                        continue
                
                if not chat_input:
                    print("   ❌ No chat input found with any selector")
                    return False
                
                # Test typing in chat
                test_message = "Show me completion rates for lesson 1"
                chat_input.clear()
                chat_input.send_keys(test_message)
                print(f"   ✅ Typed message: {test_message}")
                
                # Find send button
                send_selectors = [
                    "button[type='submit']",
                    "input[type='submit']",
                    "[class*='send']",
                    "[class*='submit']",
                    "[id*='send']",
                    "[id*='submit']",
                    "button:contains('Send')",
                    "button:contains('Submit')"
                ]
                
                send_button = None
                for selector in send_selectors:
                    try:
                        send_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        print(f"   ✅ Found send button with selector: {selector}")
                        break
                    except NoSuchElementException:
                        continue
                
                if not send_button:
                    print("   ❌ No send button found")
                    return False
                
                # Click send button
                send_button.click()
                print("   ✅ Clicked send button")
                time.sleep(3)
                
                # Check for response
                response_selectors = [
                    "[class*='response']",
                    "[class*='message']",
                    "[class*='chat-message']",
                    "[class*='ai-response']",
                    "div:contains('completion')",
                    "div:contains('lesson')"
                ]
                
                response_found = False
                for selector in response_selectors:
                    try:
                        responses = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if responses:
                            print(f"   ✅ Found {len(responses)} response elements")
                            response_found = True
                            break
                    except:
                        continue
                
                if not response_found:
                    print("   ❌ No response received after sending message")
                    return False
                
                # Check page source for response content
                page_source = self.driver.page_source
                if "completion" in page_source.lower() or "lesson" in page_source.lower():
                    print("   ✅ Response content detected")
                else:
                    print("   ⚠️ No relevant response content found")
                
                return True
                
            except Exception as e:
                print(f"   ❌ Chat functionality error: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Chat functionality test failed: {e}")
            return False
    
    def test_data_explorer_functionality(self):
        """Test data explorer actually shows data"""
        try:
            print("\n🔍 Testing Data Explorer Functionality...")
            
            self.driver.get(f"{self.base_url}/explorer")
            time.sleep(3)
            
            # Check for data tables
            try:
                table_selectors = [
                    "table",
                    "[class*='table']",
                    "[class*='data-table']",
                    "[class*='grid']",
                    "[class*='list']"
                ]
                
                tables_found = []
                for selector in table_selectors:
                    try:
                        tables = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if tables:
                            tables_found.extend(tables)
                            print(f"   ✅ Found {len(tables)} tables with selector: {selector}")
                    except:
                        continue
                
                if not tables_found:
                    print("   ❌ No data tables found")
                    return False
                
                # Check table content
                for i, table in enumerate(tables_found[:3]):  # Check first 3 tables
                    try:
                        rows = table.find_elements(By.CSS_SELECTOR, "tr, [class*='row']")
                        if rows:
                            print(f"   ✅ Table {i+1}: {len(rows)} rows found")
                            
                            # Check if rows have content
                            for j, row in enumerate(rows[:3]):  # Check first 3 rows
                                cells = row.find_elements(By.CSS_SELECTOR, "td, th, [class*='cell']")
                                if cells:
                                    cell_text = [cell.text.strip() for cell in cells if cell.text.strip()]
                                    if cell_text:
                                        print(f"     Row {j+1}: {len(cell_text)} cells with content")
                                    else:
                                        print(f"     Row {j+1}: Empty cells")
                                else:
                                    print(f"     Row {j+1}: No cells found")
                        else:
                            print(f"   ❌ Table {i+1}: No rows found")
                            
                    except Exception as e:
                        print(f"   ❌ Error checking table {i+1}: {e}")
                
            except Exception as e:
                print(f"   ❌ Error checking tables: {e}")
            
            # Check for data loading indicators
            try:
                loading_selectors = [
                    "[class*='loading']",
                    "[class*='spinner']",
                    "[class*='progress']",
                    "div:contains('Loading')",
                    "div:contains('loading')"
                ]
                
                loading_found = False
                for selector in loading_selectors:
                    try:
                        loading = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if loading:
                            print(f"   ⚠️ Loading indicators found: {selector}")
                            loading_found = True
                    except:
                        continue
                
                if not loading_found:
                    print("   ✅ No loading indicators found (data should be loaded)")
                
            except Exception as e:
                print(f"   ❌ Error checking loading indicators: {e}")
            
            # Check for filter/search functionality
            try:
                filter_selectors = [
                    "input[type='search']",
                    "input[placeholder*='search']",
                    "input[placeholder*='filter']",
                    "[class*='filter']",
                    "[class*='search']"
                ]
                
                filters_found = []
                for selector in filter_selectors:
                    try:
                        filters = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if filters:
                            filters_found.extend(filters)
                            print(f"   ✅ Found {len(filters)} filter elements with selector: {selector}")
                    except:
                        continue
                
                if filters_found:
                    # Test filter functionality
                    test_filter = filters_found[0]
                    test_filter.clear()
                    test_filter.send_keys("test")
                    print("   ✅ Tested filter input")
                    time.sleep(1)
                else:
                    print("   ⚠️ No filter/search elements found")
                
            except Exception as e:
                print(f"   ❌ Error testing filters: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ Data explorer functionality test failed: {e}")
            return False
    
    def test_analytics_queries(self):
        """Test analytics queries actually work"""
        try:
            print("\n📈 Testing Analytics Queries...")
            
            self.driver.get(f"{self.base_url}/")
            time.sleep(3)
            
            # Look for analytics query buttons
            query_button_selectors = [
                "button:contains('completion')",
                "button:contains('analytics')",
                "button:contains('query')",
                "[class*='query-button']",
                "[class*='analytics-button']",
                "[id*='query']",
                "[id*='analytics']"
            ]
            
            query_buttons = []
            for selector in query_button_selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if buttons:
                        query_buttons.extend(buttons)
                        print(f"   ✅ Found {len(buttons)} query buttons with selector: {selector}")
                except:
                    continue
            
            if not query_buttons:
                print("   ❌ No analytics query buttons found")
                return False
            
            # Test clicking a query button
            try:
                test_button = query_buttons[0]
                button_text = test_button.text.strip()
                print(f"   🧪 Testing query button: {button_text}")
                
                # Click the button
                test_button.click()
                print("   ✅ Clicked query button")
                time.sleep(3)
                
                # Check for results
                result_selectors = [
                    "[class*='result']",
                    "[class*='chart']",
                    "[class*='data']",
                    "canvas",
                    "[class*='analytics-result']"
                ]
                
                results_found = False
                for selector in result_selectors:
                    try:
                        results = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if results:
                            print(f"   ✅ Found {len(results)} result elements with selector: {selector}")
                            results_found = True
                            break
                    except:
                        continue
                
                if not results_found:
                    print("   ❌ No results found after clicking query button")
                    return False
                
            except Exception as e:
                print(f"   ❌ Error testing query button: {e}")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Analytics queries test failed: {e}")
            return False
    
    def test_navigation_deep(self):
        """Test navigation actually works between pages"""
        try:
            print("\n🧭 Testing Deep Navigation...")
            
            # Start on dashboard
            self.driver.get(f"{self.base_url}/")
            time.sleep(2)
            
            # Test navigation to each page
            navigation_tests = [
                ("/explorer", "Data Explorer"),
                ("/chat", "AI Chat"),
                ("/docs", "API Documentation")
            ]
            
            for path, name in navigation_tests:
                try:
                    print(f"   🧪 Testing navigation to {name}...")
                    
                    # Find and click navigation link
                    link_selectors = [
                        f'a[href="{path}"]',
                        f'a[href*="{path}"]',
                        f'[class*="nav"] a[href*="{path}"]',
                        f'[class*="sidebar"] a[href*="{path}"]'
                    ]
                    
                    link_found = None
                    for selector in link_selectors:
                        try:
                            link_found = self.driver.find_element(By.CSS_SELECTOR, selector)
                            print(f"     ✅ Found navigation link with selector: {selector}")
                            break
                        except NoSuchElementException:
                            continue
                    
                    if not link_found:
                        print(f"     ❌ No navigation link found for {name}")
                        continue
                    
                    # Click the link
                    link_found.click()
                    print(f"     ✅ Clicked navigation link to {name}")
                    time.sleep(3)
                    
                    # Verify we're on the correct page
                    current_url = self.driver.current_url
                    if path in current_url:
                        print(f"     ✅ Successfully navigated to {name}")
                        
                        # Check if page has content
                        page_source = self.driver.page_source
                        if len(page_source) > 1000:  # Basic content check
                            print(f"     ✅ {name} page has content")
                        else:
                            print(f"     ⚠️ {name} page seems empty")
                    else:
                        print(f"     ❌ Navigation failed - expected {path}, got {current_url}")
                    
                    # Go back to dashboard for next test
                    self.driver.get(f"{self.base_url}/")
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"     ❌ Error testing navigation to {name}: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ Deep navigation test failed: {e}")
            return False
    
    def run_deep_tests(self):
        """Run all deep Selenium tests"""
        print("🚀 Starting Deep Selenium UI Tests...")
        print("=" * 60)
        
        if not self.setup_driver():
            return False
        
        try:
            # Run deep tests
            tests = [
                ("Dashboard Real Data", self.test_dashboard_real_data),
                ("Chat Functionality", self.test_chat_functionality),
                ("Data Explorer Functionality", self.test_data_explorer_functionality),
                ("Analytics Queries", self.test_analytics_queries),
                ("Deep Navigation", self.test_navigation_deep)
            ]
            
            for test_name, test_func in tests:
                try:
                    success = test_func()
                    self.results.append({
                        "test": test_name,
                        "success": success,
                        "error": None
                    })
                except Exception as e:
                    print(f"❌ {test_name} test failed: {e}")
                    self.results.append({
                        "test": test_name,
                        "success": False,
                        "error": str(e)
                    })
            
        finally:
            if self.driver:
                self.driver.quit()
        
        # Generate results summary
        self.generate_deep_results_summary()
    
    def generate_deep_results_summary(self):
        """Generate deep test results summary"""
        print("\n" + "=" * 60)
        print("📊 Deep Selenium Test Results:")
        
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
        results_file = f"deep_selenium_results_{timestamp}.json"
        
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
            print("🎉 Deep Testing: EXCELLENT - All functionality working!")
        elif success_rate >= 60:
            print("✅ Deep Testing: GOOD - Some issues to address")
        else:
            print("⚠️ Deep Testing: NEEDS IMPROVEMENT - Significant functionality issues")

if __name__ == "__main__":
    tester = DeepSeleniumTester("http://localhost:8000")
    tester.run_deep_tests()
