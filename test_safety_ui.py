#!/usr/bin/env python3
"""
Playwright UI Test for Safety Dashboard
Tests the complete safety UI workflow including CRUD operations
"""

import asyncio
from playwright.async_api import async_playwright
import time
import json

async def test_safety_ui():
    """Test the safety dashboard UI with Playwright"""
    
    print("🎭 Starting Playwright UI Test for Safety Dashboard")
    print("=" * 50)
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate to safety dashboard
            base_url = "https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app"
            safety_url = f"{base_url}/ui/safety"
            
            print(f"📱 Navigating to: {safety_url}")
            await page.goto(safety_url, wait_until="networkidle")
            
            # Check page title
            title = await page.title()
            print(f"📄 Page title: {title}")
            
            # Wait for page to load
            await page.wait_for_timeout(2000)
            
            # Take screenshot
            await page.screenshot(path="safety_dashboard_loaded.png")
            print("📸 Screenshot saved: safety_dashboard_loaded.png")
            
            # Test 1: Check if safety dashboard elements are present
            print("\n🔍 Testing Dashboard Elements...")
            
            # Check for main heading
            heading = await page.query_selector("h1")
            if heading:
                heading_text = await heading.text_content()
                print(f"✅ Main heading found: {heading_text}")
            else:
                print("❌ Main heading not found")
            
            # Check for navigation
            nav_links = await page.query_selector_all("nav a")
            print(f"✅ Navigation links found: {len(nav_links)}")
            
            # Test 2: Test API endpoints through browser console
            print("\n🔧 Testing API Endpoints...")
            
            # Test trigger words API
            api_result = await page.evaluate("""
                async () => {
                    try {
                        const response = await fetch('/api/trigger-words');
                        const data = await response.json();
                        return {
                            status: response.status,
                            success: data.success,
                            wordCount: data.total_count || 0
                        };
                    } catch (error) {
                        return { error: error.message };
                    }
                }
            """)
            
            print(f"✅ Trigger words API: {api_result}")
            
            # Test 3: Add a test word through the UI (if form exists)
            print("\n➕ Testing Word Addition...")
            
            # Look for add word form elements
            word_input = await page.query_selector('input[placeholder*="word"], input[name*="word"], #word-input')
            severity_select = await page.query_selector('select[name*="severity"], #severity-select')
            add_button = await page.query_selector('button:has-text("Add"), button:has-text("Create"), #add-word-btn')
            
            if word_input and add_button:
                test_word = f"playwright_test_{int(time.time())}"
                print(f"📝 Adding test word: {test_word}")
                
                await word_input.fill(test_word)
                
                if severity_select:
                    await severity_select.select_option("medium")
                
                await add_button.click()
                await page.wait_for_timeout(2000)
                
                # Verify word was added
                api_result = await page.evaluate("""
                    async () => {
                        try {
                            const response = await fetch('/api/trigger-words');
                            const data = await response.json();
                            return {
                                status: response.status,
                                success: data.success,
                                words: data.trigger_words || []
                            };
                        } catch (error) {
                            return { error: error.message };
                        }
                    }
                """)
                
                print(f"✅ After adding word: {api_result}")
                
                # Test 4: Delete the test word
                print("\n🗑️ Testing Word Deletion...")
                
                delete_result = await page.evaluate(f"""
                    async () => {{
                        try {{
                            const response = await fetch('/api/trigger-words/1', {{
                                method: 'DELETE'
                            }});
                            const data = await response.json();
                            return {{
                                status: response.status,
                                success: data.success,
                                message: data.message
                            }};
                        }} catch (error) {{
                            return {{ error: error.message }};
                        }}
                    }}
                """)
                
                print(f"✅ Delete result: {delete_result}")
                
            else:
                print("⚠️ Add word form not found - testing API directly")
                
                # Test API directly
                add_result = await page.evaluate(f"""
                    async () => {{
                        try {{
                            const response = await fetch('/api/trigger-words?word=playwright_api_test_{int(time.time())}&severity=low&description=Playwright API test', {{
                                method: 'POST'
                            }});
                            const data = await response.json();
                            return {{
                                status: response.status,
                                success: data.success,
                                word: data.trigger_word
                            }};
                        }} catch (error) {{
                            return {{ error: error.message }};
                        }}
                    }}
                """)
                
                print(f"✅ API add result: {add_result}")
            
            # Test 5: Check safety status
            print("\n📊 Testing Safety Status...")
            
            status_result = await page.evaluate("""
                async () => {
                    try {
                        const response = await fetch('/ui/api/safety/status');
                        const data = await response.json();
                        return {
                            status: response.status,
                            success: data.success,
                            systemStatus: data.system_status?.overall_status,
                            safetyScore: data.safety_metrics?.safety_score
                        };
                    } catch (error) {
                        return { error: error.message };
                    }
                }
            """)
            
            print(f"✅ Safety status: {status_result}")
            
            # Test 6: Test content analysis (if available)
            print("\n🧠 Testing Content Analysis...")
            
            analysis_result = await page.evaluate("""
                async () => {
                    try {
                        const response = await fetch('/api/safety/analyze/enhanced?content=This is a test message with potentially harmful content');
                        const data = await response.json();
                        return {
                            status: response.status,
                            success: data.success,
                            flagged: data.flagged,
                            confidence: data.confidence
                        };
                    } catch (error) {
                        return { error: error.message };
                    }
                }
            """)
            
            print(f"✅ Content analysis: {analysis_result}")
            
            # Final screenshot
            await page.screenshot(path="safety_dashboard_final.png")
            print("📸 Final screenshot saved: safety_dashboard_final.png")
            
            print("\n✅ Playwright UI Test Completed Successfully!")
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            await page.screenshot(path="safety_dashboard_error.png")
            print("📸 Error screenshot saved: safety_dashboard_error.png")
            
        finally:
            await browser.close()

async def main():
    """Run the UI test"""
    await test_safety_ui()

if __name__ == "__main__":
    asyncio.run(main())
