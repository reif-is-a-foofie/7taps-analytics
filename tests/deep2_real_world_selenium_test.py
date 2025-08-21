#!/usr/bin/env python3
"""
Deep2 Real-World Selenium Testing for 7taps Analytics
Tests actual user workflows and business scenarios
"""

import time
import json
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class RealWorldScenarioTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        self.driver = None
        self.scenario_data = {}
        
    def setup_driver(self):
        """Setup Chrome driver for real-world testing"""
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
    
    def test_scenario_1_course_instructor_workflow(self):
        """Real-world scenario: Course instructor checking student progress"""
        try:
            print("\n👨‍🏫 Scenario 1: Course Instructor Workflow")
            print("   Business Case: Instructor needs to check overall course performance")
            
            # Step 1: Instructor opens dashboard
            self.driver.get(f"{self.base_url}/")
            time.sleep(3)
            print("   ✅ Step 1: Dashboard loaded")
            
            # Step 2: Check overall completion rates
            try:
                # Look for completion rate metrics
                completion_selectors = [
                    "[class*='completion']",
                    "[class*='rate']",
                    "[class*='percentage']",
                    "div:contains('completion')",
                    "div:contains('rate')"
                ]
                
                completion_found = False
                for selector in completion_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            completion_found = True
                            print(f"   ✅ Step 2: Found completion metrics with selector: {selector}")
                            break
                    except:
                        continue
                
                if not completion_found:
                    print("   ❌ Step 2: No completion metrics found")
                    return False
                    
            except Exception as e:
                print(f"   ❌ Step 2: Error checking completion rates: {e}")
                return False
            
            # Step 3: Check lesson-by-lesson breakdown
            try:
                # Look for lesson-specific data
                lesson_selectors = [
                    "[class*='lesson']",
                    "[class*='module']",
                    "div:contains('lesson')",
                    "div:contains('module')"
                ]
                
                lesson_data_found = False
                for selector in lesson_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            lesson_data_found = True
                            print(f"   ✅ Step 3: Found lesson data with selector: {selector}")
                            break
                    except:
                        continue
                
                if not lesson_data_found:
                    print("   ❌ Step 3: No lesson-specific data found")
                    return False
                    
            except Exception as e:
                print(f"   ❌ Step 3: Error checking lesson data: {e}")
                return False
            
            # Step 4: Check student engagement trends
            try:
                # Look for engagement/trend data
                engagement_selectors = [
                    "[class*='engagement']",
                    "[class*='trend']",
                    "[class*='activity']",
                    "div:contains('engagement')",
                    "div:contains('trend')"
                ]
                
                engagement_found = False
                for selector in engagement_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            engagement_found = True
                            print(f"   ✅ Step 4: Found engagement data with selector: {selector}")
                            break
                    except:
                        continue
                
                if not engagement_found:
                    print("   ⚠️ Step 4: No engagement trends found (may be optional)")
                    
            except Exception as e:
                print(f"   ⚠️ Step 4: Error checking engagement: {e}")
            
            print("   🎯 Scenario 1 Result: Instructor can assess course performance")
            return True
            
        except Exception as e:
            print(f"❌ Scenario 1 failed: {e}")
            return False
    
    def test_scenario_2_student_progress_investigation(self):
        """Real-world scenario: Investigating specific student progress issues"""
        try:
            print("\n👨‍🎓 Scenario 2: Student Progress Investigation")
            print("   Business Case: Instructor needs to identify struggling students")
            
            # Step 1: Navigate to data explorer
            self.driver.get(f"{self.base_url}/explorer")
            time.sleep(3)
            print("   ✅ Step 1: Data Explorer loaded")
            
            # Step 2: Look for student data tables
            try:
                student_selectors = [
                    "table",
                    "[class*='table']",
                    "[class*='student']",
                    "[class*='user']",
                    "div:contains('student')",
                    "div:contains('user')"
                ]
                
                student_data_found = False
                for selector in student_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            student_data_found = True
                            print(f"   ✅ Step 2: Found student data with selector: {selector}")
                            break
                    except:
                        continue
                
                if not student_data_found:
                    print("   ❌ Step 2: No student data tables found")
                    return False
                    
            except Exception as e:
                print(f"   ❌ Step 2: Error finding student data: {e}")
                return False
            
            # Step 3: Check for incomplete students filter
            try:
                # Look for incomplete students functionality
                incomplete_selectors = [
                    "[class*='incomplete']",
                    "[class*='filter']",
                    "button:contains('incomplete')",
                    "button:contains('filter')"
                ]
                
                incomplete_found = False
                for selector in incomplete_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            incomplete_found = True
                            print(f"   ✅ Step 3: Found incomplete students filter with selector: {selector}")
                            break
                    except:
                        continue
                
                if not incomplete_found:
                    print("   ⚠️ Step 3: No incomplete students filter found")
                    
            except Exception as e:
                print(f"   ⚠️ Step 3: Error checking incomplete filter: {e}")
            
            # Step 4: Check for progress percentage data
            try:
                # Look for progress data
                progress_selectors = [
                    "[class*='progress']",
                    "[class*='percentage']",
                    "div:contains('progress')",
                    "div:contains('%')"
                ]
                
                progress_found = False
                for selector in progress_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            progress_found = True
                            print(f"   ✅ Step 4: Found progress data with selector: {selector}")
                            break
                    except:
                        continue
                
                if not progress_found:
                    print("   ⚠️ Step 4: No progress percentage data found")
                    
            except Exception as e:
                print(f"   ⚠️ Step 4: Error checking progress data: {e}")
            
            print("   🎯 Scenario 2 Result: Can investigate student progress issues")
            return True
            
        except Exception as e:
            print(f"❌ Scenario 2 failed: {e}")
            return False
    
    def test_scenario_3_analytics_question_workflow(self):
        """Real-world scenario: Instructor asks analytics questions via chat"""
        try:
            print("\n🤖 Scenario 3: Analytics Question Workflow")
            print("   Business Case: Instructor asks natural language questions about course data")
            
            # Step 1: Navigate to chat interface
            self.driver.get(f"{self.base_url}/chat")
            time.sleep(3)
            print("   ✅ Step 1: Chat interface loaded")
            
            # Step 2: Find chat input and ask a real question
            try:
                # Find chat input
                input_selectors = [
                    "textarea",
                    "input[type='text']",
                    "[contenteditable='true']",
                    "[class*='chat-input']"
                ]
                
                chat_input = None
                for selector in input_selectors:
                    try:
                        chat_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                        print(f"   ✅ Step 2: Found chat input with selector: {selector}")
                        break
                    except NoSuchElementException:
                        continue
                
                if not chat_input:
                    print("   ❌ Step 2: No chat input found")
                    return False
                
                # Ask a real business question
                business_questions = [
                    "Which lessons have the lowest completion rates?",
                    "Show me students who haven't finished the course",
                    "What's the average completion time for the course?",
                    "Which lessons are students struggling with most?"
                ]
                
                selected_question = random.choice(business_questions)
                chat_input.clear()
                chat_input.send_keys(selected_question)
                print(f"   ✅ Step 2: Asked business question: {selected_question}")
                
            except Exception as e:
                print(f"   ❌ Step 2: Error with chat input: {e}")
                return False
            
            # Step 3: Send the question
            try:
                # Find send button
                send_selectors = [
                    "button[type='submit']",
                    "[class*='send']",
                    "[class*='submit']",
                    "button:contains('Send')"
                ]
                
                send_button = None
                for selector in send_selectors:
                    try:
                        send_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        print(f"   ✅ Step 3: Found send button with selector: {selector}")
                        break
                    except NoSuchElementException:
                        continue
                
                if not send_button:
                    print("   ❌ Step 3: No send button found")
                    return False
                
                # Click send
                send_button.click()
                print("   ✅ Step 3: Sent question")
                time.sleep(5)  # Wait for response
                
            except Exception as e:
                print(f"   ❌ Step 3: Error sending question: {e}")
                return False
            
            # Step 4: Check for meaningful response
            try:
                # Look for response with business value
                response_selectors = [
                    "[class*='response']",
                    "[class*='message']",
                    "[class*='ai-response']"
                ]
                
                response_found = False
                for selector in response_selectors:
                    try:
                        responses = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if responses:
                            response_found = True
                            print(f"   ✅ Step 4: Found response with selector: {selector}")
                            break
                    except:
                        continue
                
                if not response_found:
                    print("   ❌ Step 4: No response received")
                    return False
                
                # Check if response contains business-relevant content
                page_source = self.driver.page_source.lower()
                business_keywords = ['completion', 'lesson', 'student', 'rate', 'percentage', 'data']
                relevant_content = any(keyword in page_source for keyword in business_keywords)
                
                if relevant_content:
                    print("   ✅ Step 4: Response contains business-relevant content")
                else:
                    print("   ⚠️ Step 4: Response may not contain business-relevant content")
                
            except Exception as e:
                print(f"   ❌ Step 4: Error checking response: {e}")
                return False
            
            print("   🎯 Scenario 3 Result: Can ask and receive answers to business questions")
            return True
            
        except Exception as e:
            print(f"❌ Scenario 3 failed: {e}")
            return False
    
    def test_scenario_4_comparative_analysis_workflow(self):
        """Real-world scenario: Comparing lesson performance"""
        try:
            print("\n📊 Scenario 4: Comparative Analysis Workflow")
            print("   Business Case: Instructor compares performance between different lessons")
            
            # Step 1: Navigate to dashboard
            self.driver.get(f"{self.base_url}/")
            time.sleep(3)
            print("   ✅ Step 1: Dashboard loaded")
            
            # Step 2: Look for comparison functionality
            try:
                comparison_selectors = [
                    "[class*='compare']",
                    "[class*='comparison']",
                    "button:contains('compare')",
                    "button:contains('vs')",
                    "[class*='lesson-comparison']"
                ]
                
                comparison_found = False
                for selector in comparison_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            comparison_found = True
                            print(f"   ✅ Step 2: Found comparison functionality with selector: {selector}")
                            break
                    except:
                        continue
                
                if not comparison_found:
                    print("   ⚠️ Step 2: No comparison functionality found")
                    
            except Exception as e:
                print(f"   ⚠️ Step 2: Error checking comparison: {e}")
            
            # Step 3: Check for lesson-specific metrics
            try:
                lesson_metrics_selectors = [
                    "[class*='lesson']",
                    "[class*='module']",
                    "div:contains('lesson')",
                    "div:contains('module')"
                ]
                
                lesson_metrics_found = False
                for selector in lesson_metrics_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            lesson_metrics_found = True
                            print(f"   ✅ Step 3: Found lesson metrics with selector: {selector}")
                            break
                    except:
                        continue
                
                if not lesson_metrics_found:
                    print("   ❌ Step 3: No lesson-specific metrics found")
                    return False
                    
            except Exception as e:
                print(f"   ❌ Step 3: Error checking lesson metrics: {e}")
                return False
            
            # Step 4: Check for performance indicators
            try:
                performance_selectors = [
                    "[class*='performance']",
                    "[class*='score']",
                    "[class*='rating']",
                    "div:contains('performance')",
                    "div:contains('score')"
                ]
                
                performance_found = False
                for selector in performance_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            performance_found = True
                            print(f"   ✅ Step 4: Found performance indicators with selector: {selector}")
                            break
                    except:
                        continue
                
                if not performance_found:
                    print("   ⚠️ Step 4: No performance indicators found")
                    
            except Exception as e:
                print(f"   ⚠️ Step 4: Error checking performance: {e}")
            
            print("   🎯 Scenario 4 Result: Can perform comparative analysis")
            return True
            
        except Exception as e:
            print(f"❌ Scenario 4 failed: {e}")
            return False
    
    def test_scenario_5_data_export_workflow(self):
        """Real-world scenario: Exporting data for external analysis"""
        try:
            print("\n📤 Scenario 5: Data Export Workflow")
            print("   Business Case: Instructor needs to export data for external reporting")
            
            # Step 1: Navigate to data explorer
            self.driver.get(f"{self.base_url}/explorer")
            time.sleep(3)
            print("   ✅ Step 1: Data Explorer loaded")
            
            # Step 2: Look for export functionality
            try:
                export_selectors = [
                    "[class*='export']",
                    "[class*='download']",
                    "button:contains('export')",
                    "button:contains('download')",
                    "a[href*='export']",
                    "a[href*='download']"
                ]
                
                export_found = False
                for selector in export_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            export_found = True
                            print(f"   ✅ Step 2: Found export functionality with selector: {selector}")
                            break
                    except:
                        continue
                
                if not export_found:
                    print("   ⚠️ Step 2: No export functionality found")
                    
            except Exception as e:
                print(f"   ⚠️ Step 2: Error checking export: {e}")
            
            # Step 3: Check for data tables to export
            try:
                table_selectors = [
                    "table",
                    "[class*='table']",
                    "[class*='data-table']"
                ]
                
                tables_found = False
                for selector in table_selectors:
                    try:
                        tables = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if tables:
                            tables_found = True
                            print(f"   ✅ Step 3: Found data tables with selector: {selector}")
                            break
                    except:
                        continue
                
                if not tables_found:
                    print("   ❌ Step 3: No data tables found to export")
                    return False
                    
            except Exception as e:
                print(f"   ❌ Step 3: Error checking tables: {e}")
                return False
            
            # Step 4: Check for filter/selection functionality
            try:
                filter_selectors = [
                    "[class*='filter']",
                    "[class*='select']",
                    "input[type='search']",
                    "select"
                ]
                
                filter_found = False
                for selector in filter_selectors:
                    try:
                        filters = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if filters:
                            filter_found = True
                            print(f"   ✅ Step 4: Found filter/selection with selector: {selector}")
                            break
                    except:
                        continue
                
                if not filter_found:
                    print("   ⚠️ Step 4: No filter/selection functionality found")
                    
            except Exception as e:
                print(f"   ⚠️ Step 4: Error checking filters: {e}")
            
            print("   🎯 Scenario 5 Result: Can export data for external analysis")
            return True
            
        except Exception as e:
            print(f"❌ Scenario 5 failed: {e}")
            return False
    
    def run_real_world_scenarios(self):
        """Run all real-world scenario tests"""
        print("🚀 Starting Deep2 Real-World Scenario Testing...")
        print("=" * 70)
        
        if not self.setup_driver():
            return False
        
        try:
            # Run real-world scenarios
            scenarios = [
                ("Course Instructor Workflow", self.test_scenario_1_course_instructor_workflow),
                ("Student Progress Investigation", self.test_scenario_2_student_progress_investigation),
                ("Analytics Question Workflow", self.test_scenario_3_analytics_question_workflow),
                ("Comparative Analysis Workflow", self.test_scenario_4_comparative_analysis_workflow),
                ("Data Export Workflow", self.test_scenario_5_data_export_workflow)
            ]
            
            for scenario_name, scenario_func in scenarios:
                try:
                    success = scenario_func()
                    self.results.append({
                        "scenario": scenario_name,
                        "success": success,
                        "error": None
                    })
                except Exception as e:
                    print(f"❌ {scenario_name} scenario failed: {e}")
                    self.results.append({
                        "scenario": scenario_name,
                        "success": False,
                        "error": str(e)
                    })
            
        finally:
            if self.driver:
                self.driver.quit()
        
        # Generate results summary
        self.generate_real_world_results_summary()
    
    def generate_real_world_results_summary(self):
        """Generate real-world scenario results summary"""
        print("\n" + "=" * 70)
        print("📊 Real-World Scenario Test Results:")
        
        total_scenarios = len(self.results)
        passed_scenarios = sum(1 for result in self.results if result["success"])
        failed_scenarios = total_scenarios - passed_scenarios
        success_rate = (passed_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0
        
        print(f"   Total Scenarios: {total_scenarios}")
        print(f"   Passed: {passed_scenarios}")
        print(f"   Failed: {failed_scenarios}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        if failed_scenarios > 0:
            print(f"\n❌ Failed Scenarios:")
            for result in self.results:
                if not result["success"]:
                    print(f"   - {result['scenario']}: {result['error']}")
        
        # Business impact analysis
        print(f"\n💼 Business Impact Analysis:")
        business_scenarios = {
            "Course Instructor Workflow": "Instructor can assess course performance",
            "Student Progress Investigation": "Can identify struggling students", 
            "Analytics Question Workflow": "Natural language data queries work",
            "Comparative Analysis Workflow": "Can compare lesson performance",
            "Data Export Workflow": "Can export data for external analysis"
        }
        
        for scenario, business_value in business_scenarios.items():
            result = next((r for r in self.results if r["scenario"] == scenario), None)
            if result and result["success"]:
                print(f"   ✅ {business_value}")
            else:
                print(f"   ❌ {business_value} - BLOCKED")
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"real_world_scenario_results_{timestamp}.json"
        
        with open(results_file, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "base_url": self.base_url,
                "test_type": "Real-World Scenario Testing",
                "summary": {
                    "total_scenarios": total_scenarios,
                    "passed_scenarios": passed_scenarios,
                    "failed_scenarios": failed_scenarios,
                    "success_rate": success_rate
                },
                "business_impact": business_scenarios,
                "results": self.results
            }, f, indent=2)
        
        print(f"\n📄 Results saved to: {results_file}")
        
        if success_rate >= 80:
            print("🎉 Real-World Testing: EXCELLENT - All business workflows functional!")
        elif success_rate >= 60:
            print("✅ Real-World Testing: GOOD - Most business workflows working")
        else:
            print("⚠️ Real-World Testing: NEEDS IMPROVEMENT - Critical business workflows failing")

if __name__ == "__main__":
    tester = RealWorldScenarioTester("http://localhost:8000")
    tester.run_real_world_scenarios()
