#!/usr/bin/env python3
"""
Test script for CSV to xAPI conversion functionality.

This script demonstrates how to convert focus group CSV data to xAPI statements
and ingest them through the standard xAPI pipeline.
"""

import os
import sys
import asyncio
import json
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.csv_to_xapi_converter import (
    convert_csv_to_xapi_statements,
    get_conversion_stats,
    validate_xapi_statements
)

def create_sample_csv_data():
    """Create sample CSV data for testing."""
    return """Learner,Card,Card type,Lesson Number,Global Q#,PDF Page #,Response
Audrey Todd,Card 6 (Form): 🧠 Quick pulse check...,Form,1,1,6,Screen time Productivity Stress management Sleep Real life connection
Jeniece Harmon,Card 12 (Poll): How do you feel about your current screen habits?,Poll,1,2,12,Mostly positive but room for improvement
Isabel Palmatier,Card 18 (Quiz): What's your primary digital wellness goal?,Quiz,2,3,18,Better focus and productivity
Test User,Card 24 (Form): Describe your ideal relationship with technology,Form,2,4,24,More intentional and mindful usage"""

async def test_csv_to_xapi_conversion():
    """Test the CSV to xAPI conversion functionality."""
    
    print("🧪 Testing CSV to xAPI Conversion")
    print("=" * 50)
    
    # Create sample CSV data
    csv_data = create_sample_csv_data()
    print(f"📄 Sample CSV data created with {len(csv_data.splitlines()) - 1} rows")
    
    try:
        # Convert CSV to xAPI statements
        print("\n🔄 Converting CSV to xAPI statements...")
        xapi_statements = convert_csv_to_xapi_statements(csv_data)
        
        print(f"✅ Successfully converted {len(xapi_statements)} statements")
        
        # Get conversion statistics
        print("\n📊 Conversion Statistics:")
        stats = get_conversion_stats(xapi_statements)
        print(json.dumps(stats, indent=2))
        
        # Validate statements
        print("\n🔍 Validating xAPI statements...")
        validation = validate_xapi_statements(xapi_statements)
        print(f"✅ Valid: {validation['valid']}")
        print(f"❌ Invalid: {validation['invalid']}")
        
        if validation['errors']:
            print("⚠️  Validation errors:")
            for error in validation['errors']:
                print(f"   - {error}")
        
        # Show sample statement structure
        print("\n📋 Sample xAPI Statement Structure:")
        if xapi_statements:
            sample = xapi_statements[0]
            print(json.dumps(sample, indent=2))
        
        # Check preserved metadata
        print("\n🔗 Preserved Metadata Check:")
        if xapi_statements:
            extensions = xapi_statements[0].get('context', {}).get('extensions', {})
            preserved_keys = [
                'https://7taps.com/lesson-number',
                'https://7taps.com/lesson-name', 
                'https://7taps.com/lesson-url',
                'https://7taps.com/global-q',
                'https://7taps.com/card-type',
                'https://7taps.com/pdf-page',
                'https://7taps.com/full-card-text',
                'https://7taps.com/question-text'
            ]
            
            for key in preserved_keys:
                value = extensions.get(key, 'NOT FOUND')
                print(f"   {key}: {value}")
        
        print("\n🎉 CSV to xAPI conversion test completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during conversion: {e}")
        return False

async def test_api_endpoint():
    """Test the API endpoint for CSV to xAPI conversion."""
    
    print("\n🌐 Testing API Endpoint")
    print("=" * 30)
    
    try:
        import httpx
        
        # Create sample CSV data
        csv_data = create_sample_csv_data()
        
        # Test the API endpoint
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://seventaps-analytics-5135b3a0701a.herokuapp.com/api/csv-to-xapi/convert",
                json={
                    "csv_data": csv_data,
                    "dry_run": True  # Don't actually ingest
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ API endpoint test successful!")
                print(f"📊 Converted {result['total_statements']} statements")
                print(f"✅ Valid: {result['valid_statements']}")
                print(f"❌ Invalid: {result['invalid_statements']}")
                return True
            else:
                print(f"❌ API endpoint test failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing API endpoint: {e}")
        return False

async def main():
    """Main test function."""
    
    print("🚀 Starting CSV to xAPI Conversion Tests")
    print("=" * 60)
    
    # Test local conversion
    local_success = await test_csv_to_xapi_conversion()
    
    # Test API endpoint
    api_success = await test_api_endpoint()
    
    # Summary
    print("\n📋 Test Summary")
    print("=" * 20)
    print(f"Local Conversion: {'✅ PASS' if local_success else '❌ FAIL'}")
    print(f"API Endpoint: {'✅ PASS' if api_success else '❌ FAIL'}")
    
    if local_success and api_success:
        print("\n🎉 All tests passed! CSV to xAPI conversion is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the implementation.")

if __name__ == "__main__":
    asyncio.run(main())
