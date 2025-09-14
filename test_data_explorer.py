#!/usr/bin/env python3
"""
Interactive Data Explorer Test using Playwright
Tests the actual Data Explorer interface by clicking buttons and interacting with elements
"""

import asyncio
from playwright.async_api import async_playwright
import json

async def test_data_explorer():
    """Test the Data Explorer interface interactively"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Set to False to see the browser
        page = await browser.new_page()
        
        print("🌐 Testing Data Explorer Interface...")
        
        try:
            # Navigate to the Data Explorer
            print("📱 Loading Data Explorer...")
            await page.goto("https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app/explorer")
            
            # Wait for page to load
            await page.wait_for_load_state("networkidle")
            
            # Take a screenshot to see the current state
            await page.screenshot(path="data_explorer_initial.png")
            print("📸 Initial screenshot saved as data_explorer_initial.png")
            
            # Check for error messages
            print("🔍 Checking for error messages...")
            error_elements = await page.query_selector_all('.error, [class*="error"], [id*="error"]')
            for element in error_elements:
                text = await element.text_content()
                if text and 'error' in text.lower():
                    print(f"❌ Found error: {text.strip()}")
            
            # Try to interact with the Data Table dropdown
            print("📊 Testing Data Table dropdown...")
            try:
                data_table_dropdown = await page.query_selector('select, [role="combobox"], input[type="text"]')
                if data_table_dropdown:
                    await data_table_dropdown.click()
                    await page.wait_for_timeout(1000)
                    print("✅ Clicked on data table dropdown")
                else:
                    print("❌ Could not find data table dropdown")
            except Exception as e:
                print(f"❌ Error clicking data table dropdown: {e}")
            
            # Try to interact with the Max Results input
            print("🔢 Testing Max Results input...")
            try:
                max_results_input = await page.query_selector('input[type="number"], input[placeholder*="100"]')
                if max_results_input:
                    await max_results_input.click()
                    await max_results_input.fill("50")
                    await page.wait_for_timeout(1000)
                    print("✅ Updated max results to 50")
                else:
                    print("❌ Could not find max results input")
            except Exception as e:
                print(f"❌ Error with max results input: {e}")
            
            # Try to interact with the Lessons filter
            print("📚 Testing Lessons filter...")
            try:
                lessons_filter = await page.query_selector('input[placeholder*="lesson"], select[name*="lesson"]')
                if lessons_filter:
                    await lessons_filter.click()
                    await page.wait_for_timeout(2000)  # Wait for data to load
                    print("✅ Clicked on lessons filter")
                    
                    # Check if lessons loaded
                    lessons_text = await lessons_filter.input_value()
                    if "loading" in lessons_text.lower():
                        print("⏳ Lessons still loading...")
                    else:
                        print(f"📋 Lessons loaded: {lessons_text}")
                else:
                    print("❌ Could not find lessons filter")
            except Exception as e:
                print(f"❌ Error with lessons filter: {e}")
            
            # Try to interact with the Users filter
            print("👥 Testing Users filter...")
            try:
                users_filter = await page.query_selector('input[placeholder*="user"], select[name*="user"]')
                if users_filter:
                    await users_filter.click()
                    await page.wait_for_timeout(2000)  # Wait for data to load
                    print("✅ Clicked on users filter")
                    
                    # Check if users loaded
                    users_text = await users_filter.input_value()
                    if "loading" in users_text.lower():
                        print("⏳ Users still loading...")
                    else:
                        print(f"👤 Users loaded: {users_text}")
                else:
                    print("❌ Could not find users filter")
            except Exception as e:
                print(f"❌ Error with users filter: {e}")
            
            # Try to click the Clear All button
            print("🧹 Testing Clear All button...")
            try:
                clear_all_button = await page.query_selector('button:has-text("Clear All"), input[value*="Clear"]')
                if clear_all_button:
                    await clear_all_button.click()
                    await page.wait_for_timeout(1000)
                    print("✅ Clicked Clear All button")
                else:
                    print("❌ Could not find Clear All button")
            except Exception as e:
                print(f"❌ Error with Clear All button: {e}")
            
            # Check for any new error messages after interactions
            print("🔍 Checking for new error messages after interactions...")
            error_elements = await page.query_selector_all('.error, [class*="error"], [id*="error"]')
            for element in error_elements:
                text = await element.text_content()
                if text and 'error' in text.lower():
                    print(f"❌ Found error after interactions: {text.strip()}")
            
            # Take a final screenshot
            await page.screenshot(path="data_explorer_final.png")
            print("📸 Final screenshot saved as data_explorer_final.png")
            
            # Get the page content to see what's actually rendered
            content = await page.content()
            
            # Look for specific error messages
            if "PostgreSQL routes disabled" in content:
                print("🔍 Found PostgreSQL error message in page content")
            
            if "501" in content:
                print("🔍 Found 501 error in page content")
            
            return True
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            return False
        finally:
            await browser.close()

async def main():
    """Main test function"""
    print("🚀 Starting Interactive Data Explorer Test")
    print("=" * 60)
    
    success = await test_data_explorer()
    
    print("=" * 60)
    if success:
        print("🎉 Interactive test completed!")
    else:
        print("💥 Test failed!")

if __name__ == "__main__":
    asyncio.run(main())

