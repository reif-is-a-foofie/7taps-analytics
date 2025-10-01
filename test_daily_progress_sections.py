"""
Piece-by-piece UI testing for Daily Progress Dashboard
Tests each section systematically including cohort selection
"""

import asyncio
import json
from playwright.async_api import async_playwright

async def test_daily_progress_sections():
    """Test each section of the daily progress UI systematically."""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Set to True for headless
        page = await browser.new_page()
        
        try:
            print("🧪 Testing Daily Progress UI - Section by Section...")
            
            # Test 1: Basic Page Load
            print("\n1️⃣ Testing Basic Page Load...")
            ui_url = "https://taps-analytics-ui-245712978112.us-central1.run.app/ui/daily-progress"
            
            response = await page.goto(ui_url)
            print(f"   Page Status: {response.status}")
            
            if response.status != 200:
                print(f"   ❌ Page failed to load: {response.status}")
                return
            
            await page.wait_for_load_state('networkidle')
            print("   ✅ Page loaded successfully")
            
            # Test 2: Check Page Title and Header
            print("\n2️⃣ Testing Page Title and Header...")
            title = await page.title()
            print(f"   Page Title: '{title}'")
            
            header = await page.query_selector('h1')
            if header:
                header_text = await header.text_content()
                print(f"   Main Header: '{header_text}'")
            else:
                print("   ❌ No main header found")
            
            # Test 3: Check for Error Messages
            print("\n3️⃣ Testing for Error Messages...")
            error_selectors = [
                '.text-red-600', '.bg-red-50', '.text-red-800', 
                '[class*="error"]', 'text="Dashboard error"', 'text="Error"'
            ]
            
            errors_found = 0
            for selector in error_selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    for element in elements:
                        text = await element.text_content()
                        if text and ('error' in text.lower() or 'failed' in text.lower()):
                            print(f"   ❌ Error found: {text}")
                            errors_found += 1
            
            if errors_found == 0:
                print("   ✅ No error messages found")
            
            # Test 4: Check Summary Cards Section
            print("\n4️⃣ Testing Summary Cards...")
            cards = await page.query_selector_all('.bg-white.rounded-lg.shadow')
            print(f"   Found {len(cards)} cards total")
            
            # Look for specific metric cards
            card_titles = ['Total Learners', 'Completed', 'Partial', 'Completion Rate']
            for title in card_titles:
                card = await page.query_selector(f'text="{title}"')
                if card:
                    # Get the metric value
                    metric = await page.query_selector(f'text="{title}" + .text-2xl')
                    if metric:
                        value = await metric.text_content()
                        print(f"   ✅ {title}: {value}")
                    else:
                        print(f"   ⚠️ {title}: Found but no metric value")
                else:
                    print(f"   ❌ {title}: Not found")
            
            # Test 5: Check Insights Section
            print("\n5️⃣ Testing Insights Section...")
            insights_header = await page.query_selector('text="Key Insights"')
            if insights_header:
                print("   ✅ Insights header found")
                
                # Look for insight items
                insight_items = await page.query_selector_all('li')
                print(f"   Found {len(insight_items)} list items")
                
                for i, item in enumerate(insight_items[:5]):  # Check first 5
                    text = await item.text_content()
                    if text and len(text.strip()) > 0:
                        print(f"      {i+1}. {text}")
            else:
                print("   ❌ Insights section not found")
            
            # Test 6: Check Quote-Worthy Section
            print("\n6️⃣ Testing Quote-Worthy Responses...")
            quotes_header = await page.query_selector('text="Quote-Worthy"')
            if quotes_header:
                print("   ✅ Quote section found")
                
                quotes = await page.query_selector_all('.border-l-4.border-blue-500')
                print(f"   Found {len(quotes)} quote items")
                
                for i, quote in enumerate(quotes):
                    text = await quote.text_content()
                    print(f"      {i+1}. {text[:100]}...")
            else:
                print("   ⚠️ Quote section not found (may be empty)")
            
            # Test 7: Check Action Buttons
            print("\n7️⃣ Testing Action Buttons...")
            email_button = await page.query_selector('button:has-text("Generate Email Summary")')
            copy_button = await page.query_selector('button:has-text("Copy Insights")')
            
            if email_button:
                print("   ✅ Email summary button found")
            else:
                print("   ❌ Email summary button not found")
                
            if copy_button:
                print("   ✅ Copy insights button found")
            else:
                print("   ❌ Copy insights button not found")
            
            # Test 8: Test Cohort Selection (Critical!)
            print("\n8️⃣ Testing Cohort Selection...")
            
            # Look for cohort/group selector
            cohort_selectors = [
                'select', '[name="group"]', '[name="cohort"]', 
                'text="Group"', 'text="Cohort"', '.form-select'
            ]
            
            cohort_found = False
            for selector in cohort_selectors:
                element = await page.query_selector(selector)
                if element:
                    print(f"   ✅ Found cohort selector: {selector}")
                    cohort_found = True
                    
                    # Try to get options
                    options = await page.query_selector_all(f'{selector} option')
                    print(f"   Found {len(options)} cohort options")
                    
                    for option in options:
                        text = await option.text_content()
                        value = await option.get_attribute('value')
                        print(f"      - {text} (value: {value})")
                    break
            
            if not cohort_found:
                print("   ❌ No cohort selection found - THIS IS A PROBLEM!")
                print("   📝 Need to add cohort dropdown to the UI")
            
            # Test 9: Test API Data Integration
            print("\n9️⃣ Testing API Data Integration...")
            
            # Check if we can see actual data numbers
            numbers = await page.query_selector_all('.text-2xl.font-bold')
            print(f"   Found {len(numbers)} metric numbers")
            
            for i, num in enumerate(numbers):
                value = await num.text_content()
                color_class = await num.get_attribute('class')
                print(f"      {i+1}. {value} (color: {color_class.split()[-1] if color_class else 'unknown'})")
            
            # Test 10: Test with Different Cohorts
            print("\n🔟 Testing Cohort Filtering...")
            
            # Test API with different cohorts
            cohorts_to_test = [None, "7taps", "test"]
            
            for cohort in cohorts_to_test:
                cohort_param = f"&group={cohort}" if cohort else ""
                api_url = f"https://taps-analytics-ui-245712978112.us-central1.run.app/api/daily-progress/data?date=2025-09-30{cohort_param}"
                
                response = await page.request.get(api_url)
                if response.status == 200:
                    data = await response.json()
                    total_users = data.get('summary', {}).get('total_users', 0)
                    completion_rate = data.get('summary', {}).get('completion_rate', 0)
                    print(f"   Cohort '{cohort or 'All'}': {total_users} users, {completion_rate}% completion")
                else:
                    print(f"   Cohort '{cohort or 'All'}': API error {response.status}")
            
            print("\n✅ Section-by-Section Test Complete!")
            
            # Summary
            print("\n📊 SUMMARY:")
            print("   - Page loads: ✅")
            print("   - Data displays: ✅" if len(numbers) > 0 else "   - Data displays: ❌")
            print("   - Cohort selection: ✅" if cohort_found else "   - Cohort selection: ❌ (NEEDS FIX)")
            print("   - Action buttons: ✅" if email_button and copy_button else "   - Action buttons: ❌")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    print("🚀 Starting Section-by-Section UI Tests...")
    asyncio.run(test_daily_progress_sections())
    print("\n🎯 All tests completed!")
