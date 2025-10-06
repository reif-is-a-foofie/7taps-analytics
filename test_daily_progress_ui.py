"""
Playwright test for Daily Progress UI
Tests the daily progress dashboard functionality
"""

import asyncio
import json
from playwright.async_api import async_playwright

async def test_daily_progress_ui():
    """Test the daily progress dashboard UI."""
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)  # Set to True for headless
        page = await browser.new_page()
        
        try:
            print("🧪 Testing Daily Progress UI...")
            
            # Test 1: API endpoint first
            print("\n1️⃣ Testing API endpoint...")
            api_url = "https://taps-analytics-ui-245712978112.us-central1.run.app/api/daily-progress/data?date=2025-09-30"
            
            response = await page.request.get(api_url)
            print(f"   API Status: {response.status}")
            
            if response.status == 200:
                data = await response.json()
                print(f"   API Response: {json.dumps(data, indent=2)}")
            else:
                print(f"   API Error: {await response.text()}")
            
            # Test 2: UI Dashboard
            print("\n2️⃣ Testing UI Dashboard...")
            ui_url = "https://taps-analytics-ui-245712978112.us-central1.run.app/ui/daily-progress"
            
            await page.goto(ui_url)
            await page.wait_for_load_state('networkidle')
            
            # Check page title
            title = await page.title()
            print(f"   Page Title: {title}")
            
            # Check for error messages
            error_elements = await page.query_selector_all('.text-red-600, .bg-red-50')
            if error_elements:
                print("   ❌ Found error elements:")
                for element in error_elements:
                    text = await element.text_content()
                    print(f"      - {text}")
            
            # Check for success elements
            success_elements = await page.query_selector_all('.text-green-600, .bg-green-50')
            if success_elements:
                print("   ✅ Found success elements:")
                for element in success_elements:
                    text = await element.text_content()
                    print(f"      - {text}")
            
            # Check for summary cards
            cards = await page.query_selector_all('.bg-white.rounded-lg.shadow')
            print(f"   📊 Found {len(cards)} summary cards")
            
            # Check for user data
            user_lists = await page.query_selector_all('[class*="space-y-2"]')
            print(f"   👥 Found {len(user_lists)} user list sections")
            
            # Check for insights
            insights_section = await page.query_selector('h2:has-text("Key Insights")')
            if insights_section:
                print("   💡 Found insights section")
                insights_text = await insights_section.text_content()
                print(f"      - {insights_text}")
            
            # Test 3: Email Summary API
            print("\n3️⃣ Testing Email Summary API...")
            email_api_url = "https://taps-analytics-ui-245712978112.us-central1.run.app/api/daily-progress/email-summary?date=2025-09-30"
            
            email_response = await page.request.get(email_api_url)
            print(f"   Email API Status: {email_response.status}")
            
            if email_response.status == 200:
                email_data = await response.json()
                print(f"   Email API Response: {json.dumps(email_data, indent=2)}")
            else:
                print(f"   Email API Error: {await email_response.text()}")
            
            # Test 4: Check if buttons work
            print("\n4️⃣ Testing UI interactions...")
            
            # Look for email generation button
            email_button = await page.query_selector('button:has-text("Generate Email Summary")')
            if email_button:
                print("   📧 Found email generation button")
                
                # Click and check for clipboard functionality
                await email_button.click()
                await page.wait_for_timeout(1000)  # Wait for any alerts
            
            # Look for copy insights button
            copy_button = await page.query_selector('button:has-text("Copy Insights")')
            if copy_button:
                print("   📋 Found copy insights button")
            
            # Test 5: Check for data visualization
            print("\n5️⃣ Checking data visualization...")
            
            # Check completion rate
            completion_rate = await page.query_selector('.text-2xl.font-bold.text-blue-600')
            if completion_rate:
                rate_text = await completion_rate.text_content()
                print(f"   📈 Completion Rate: {rate_text}")
            
            # Check user counts
            user_counts = await page.query_selector_all('.text-2xl.font-bold')
            print(f"   🔢 Found {len(user_counts)} metric displays")
            for i, count in enumerate(user_counts):
                text = await count.text_content()
                print(f"      {i+1}. {text}")
            
            print("\n✅ Daily Progress UI Test Complete!")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            
        finally:
            await browser.close()

async def test_other_dashboards():
    """Test other dashboard endpoints for comparison."""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            print("\n🔍 Testing Other Dashboards...")
            
            dashboards = [
                ("Safety Dashboard", "https://taps-analytics-ui-245712978112.us-central1.run.app/ui/safety"),
                ("ETL Dashboard", "https://taps-analytics-ui-245712978112.us-central1.run.app/ui/etl-dashboard"),
                ("Daily Analytics (Old)", "https://taps-analytics-ui-245712978112.us-central1.run.app/ui/daily-analytics"),
            ]
            
            for name, url in dashboards:
                print(f"\n   Testing {name}...")
                try:
                    response = await page.goto(url)
                    print(f"      Status: {response.status}")
                    
                    if response.status == 200:
                        title = await page.title()
                        print(f"      Title: {title}")
                        
                        # Check for errors
                        error_text = await page.query_selector('text="Dashboard error"')
                        if error_text:
                            print(f"      ❌ Error found")
                        else:
                            print(f"      ✅ Loaded successfully")
                    else:
                        print(f"      ❌ Failed to load")
                        
                except Exception as e:
                    print(f"      ❌ Error: {e}")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    print("🚀 Starting Daily Progress UI Tests with Playwright...")
    
    # Run the tests
    asyncio.run(test_daily_progress_ui())
    asyncio.run(test_other_dashboards())
    
    print("\n🎯 All tests completed!")
