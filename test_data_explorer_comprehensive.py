#!/usr/bin/env python3
"""
Comprehensive Data Explorer Test - Tests the full functionality
"""

import asyncio
from playwright.async_api import async_playwright
import json

async def test_data_explorer_comprehensive():
    """Test the Data Explorer interface comprehensively"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("🔍 Comprehensive Data Explorer Test...")
        
        try:
            # Navigate to the Data Explorer
            print("📱 Loading Data Explorer...")
            await page.goto("https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app/explorer")
            await page.wait_for_load_state("networkidle")
            
            # Wait for the page to fully load
            await page.wait_for_timeout(3000)
            
            # Check if the page loaded correctly
            title = await page.title()
            print(f"📄 Page title: {title}")
            
            # Check for any error messages on the page
            error_elements = await page.query_selector_all('.error, [class*="error"], [id*="error"]')
            for element in error_elements:
                text = await element.text_content()
                if text and 'error' in text.lower():
                    print(f"❌ Found error: {text.strip()}")
            
            # Check if the Data Table dropdown has options
            print("📊 Checking Data Table dropdown...")
            table_select = await page.query_selector('#table-select')
            if table_select:
                options = await table_select.query_selector_all('option')
                print(f"   Found {len(options)} options in table select")
                for i, option in enumerate(options):
                    text = await option.text_content()
                    value = await option.get_attribute('value')
                    print(f"   Option {i}: '{text}' (value: {value})")
                
                # Try to select "User Responses" if it exists
                try:
                    await table_select.select_option(value="user_responses")
                    print("   ✅ Selected 'user_responses' option")
                    await page.wait_for_timeout(2000)  # Wait for data to load
                except Exception as e:
                    print(f"   ❌ Could not select user_responses: {e}")
            else:
                print("   ❌ Could not find table-select element")
            
            # Check if the lessons filter has loaded data
            print("📚 Checking Lessons filter...")
            lesson_filter = await page.query_selector('#lesson-filter')
            if lesson_filter:
                options = await lesson_filter.query_selector_all('option')
                print(f"   Found {len(options)} options in lesson filter")
                for i, option in enumerate(options[:5]):  # Show first 5 options
                    text = await option.text_content()
                    value = await option.get_attribute('value')
                    print(f"   Option {i}: '{text}' (value: {value})")
                
                if len(options) > 1:  # More than just "Loading lessons..."
                    print("   ✅ Lessons filter has loaded data")
                else:
                    print("   ⏳ Lessons filter still loading or empty")
            else:
                print("   ❌ Could not find lesson-filter element")
            
            # Check if the users filter has loaded data
            print("👥 Checking Users filter...")
            user_filter = await page.query_selector('#user-filter')
            if user_filter:
                options = await user_filter.query_selector_all('option')
                print(f"   Found {len(options)} options in user filter")
                for i, option in enumerate(options[:5]):  # Show first 5 options
                    text = await option.text_content()
                    value = await option.get_attribute('value')
                    print(f"   Option {i}: '{text}' (value: {value})")
                
                if len(options) > 1:  # More than just "Loading users..."
                    print("   ✅ Users filter has loaded data")
                else:
                    print("   ⏳ Users filter still loading or empty")
            else:
                print("   ❌ Could not find user-filter element")
            
            # Check if there's a data container with actual data
            print("📋 Checking for data display...")
            data_container = await page.query_selector('#data-container, .data-container, [class*="data"]')
            if data_container:
                content = await data_container.text_content()
                if content and len(content.strip()) > 0:
                    print(f"   ✅ Data container has content: {content[:100]}...")
                else:
                    print("   ⏳ Data container is empty")
            else:
                print("   ❌ Could not find data container")
            
            # Check for any JavaScript errors in the console
            print("🔍 Checking for JavaScript errors...")
            console_messages = []
            
            def handle_console(msg):
                console_messages.append(f"{msg.type}: {msg.text}")
                if msg.type == 'error':
                    print(f"   ❌ JS Error: {msg.text}")
            
            page.on('console', handle_console)
            
            # Wait a bit to capture any console messages
            await page.wait_for_timeout(2000)
            
            if not console_messages:
                print("   ✅ No JavaScript errors found")
            else:
                print(f"   📝 Found {len(console_messages)} console messages")
            
            # Take a final screenshot
            await page.screenshot(path="data_explorer_comprehensive.png")
            print("📸 Screenshot saved as data_explorer_comprehensive.png")
            
            return True
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False
        finally:
            await browser.close()

async def main():
    result = await test_data_explorer_comprehensive()
    if result:
        print("✅ Comprehensive test completed")
    else:
        print("❌ Comprehensive test failed")

if __name__ == "__main__":
    asyncio.run(main())

