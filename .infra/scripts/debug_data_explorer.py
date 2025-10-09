#!/usr/bin/env python3
"""
Debug Data Explorer - Detailed analysis of what's happening
"""

import asyncio
from playwright.async_api import async_playwright
import json

async def debug_data_explorer():
    """Debug the Data Explorer interface in detail"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("🔍 Debugging Data Explorer Interface...")
        
        try:
            # Navigate to the Data Explorer
            await page.goto("https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app/explorer")
            await page.wait_for_load_state("networkidle")
            
            # Get all elements and their properties
            print("📋 Analyzing page elements...")
            
            # Get all input elements
            inputs = await page.query_selector_all('input')
            print(f"Found {len(inputs)} input elements:")
            for i, input_elem in enumerate(inputs):
                input_type = await input_elem.get_attribute('type')
                input_placeholder = await input_elem.get_attribute('placeholder')
                input_name = await input_elem.get_attribute('name')
                input_id = await input_elem.get_attribute('id')
                input_value = await input_elem.input_value()
                print(f"  Input {i}: type={input_type}, placeholder={input_placeholder}, name={input_name}, id={input_id}, value={input_value}")
            
            # Get all select elements
            selects = await page.query_selector_all('select')
            print(f"Found {len(selects)} select elements:")
            for i, select_elem in enumerate(selects):
                select_name = await select_elem.get_attribute('name')
                select_id = await select_elem.get_attribute('id')
                select_value = await select_elem.input_value()
                print(f"  Select {i}: name={select_name}, id={select_id}, value={select_value}")
            
            # Get all buttons
            buttons = await page.query_selector_all('button')
            print(f"Found {len(buttons)} button elements:")
            for i, button in enumerate(buttons):
                button_text = await button.text_content()
                button_type = await button.get_attribute('type')
                button_id = await button.get_attribute('id')
                print(f"  Button {i}: text='{button_text}', type={button_type}, id={button_id}")
            
            # Check for any error messages
            print("🔍 Checking for error messages...")
            error_selectors = [
                '.error', '[class*="error"]', '[id*="error"]',
                '.alert', '.alert-danger', '.alert-error',
                '[role="alert"]', '.message', '.notification'
            ]
            
            for selector in error_selectors:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    text = await element.text_content()
                    if text and text.strip():
                        print(f"  Error element ({selector}): {text.strip()}")
            
            # Check the page source for specific error patterns
            content = await page.content()
            
            if "PostgreSQL routes disabled" in content:
                print("❌ Found 'PostgreSQL routes disabled' in page content")
            
            if "501" in content:
                print("❌ Found '501' error in page content")
            
            if "BigQuery" in content:
                print("✅ Found 'BigQuery' in page content")
            
            # Try to find and click on elements that might trigger API calls
            print("🔄 Testing API calls by interacting with elements...")
            
            # Look for any element that might trigger a data load
            clickable_elements = await page.query_selector_all('input, select, button, [onclick], [data-action]')
            for i, element in enumerate(clickable_elements):
                tag_name = await element.evaluate('el => el.tagName')
                element_type = await element.get_attribute('type')
                element_id = await element.get_attribute('id')
                element_class = await element.get_attribute('class')
                
                print(f"  Clickable {i}: {tag_name}, type={element_type}, id={element_id}, class={element_class}")
                
                # Try clicking on elements that might load data
                if (element_type in ['text', 'search'] or 
                    tag_name.lower() == 'select' or
                    'lesson' in (element_id or '').lower() or
                    'user' in (element_id or '').lower()):
                    
                    try:
                        print(f"    Attempting to click element {i}...")
                        await element.click()
                        await page.wait_for_timeout(1000)
                        
                        # Check for network requests
                        print(f"    Clicked element {i}, checking for network activity...")
                        
                    except Exception as e:
                        print(f"    Error clicking element {i}: {e}")
            
            # Monitor network requests
            print("🌐 Monitoring network requests...")
            requests = []
            
            def handle_request(request):
                requests.append({
                    'url': request.url,
                    'method': request.method,
                    'headers': dict(request.headers)
                })
                print(f"  Request: {request.method} {request.url}")
            
            def handle_response(response):
                print(f"  Response: {response.status} {response.url}")
                if response.status >= 400:
                    print(f"    ❌ Error response: {response.status}")
            
            page.on('request', handle_request)
            page.on('response', handle_response)
            
            # Wait a bit to see if any requests are made
            await page.wait_for_timeout(3000)
            
            print(f"Total network requests captured: {len(requests)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Debug failed: {e}")
            return False
        finally:
            await browser.close()

async def main():
    result = await debug_data_explorer()
    if result:
        print("✅ Debug completed successfully")
    else:
        print("❌ Debug failed")

if __name__ == "__main__":
    asyncio.run(main())
