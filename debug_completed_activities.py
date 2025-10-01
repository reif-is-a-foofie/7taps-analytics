#!/usr/bin/env python3
"""
Quick diagnostic script for completed xAPI activities.
Run this to check if completed activities are being processed correctly.
"""

import requests
import json
import time
from datetime import datetime, timezone

def test_completed_activities():
    """Test the completed activities diagnostic endpoint."""
    
    base_url = "http://localhost:8000"
    
    print("🔍 Testing Completed Activities Diagnostic")
    print("=" * 50)
    
    # 1. Check if app is running
    try:
        health_response = requests.get(f"{base_url}/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ App is running")
        else:
            print(f"⚠️ App responded with status {health_response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ App not running: {e}")
        print("💡 Start the app with: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        return
    
    # 2. Get a sample completed statement
    print("\n📋 Getting sample completed statement...")
    try:
        sample_response = requests.get(f"{base_url}/api/debug/completed-activities/sample")
        if sample_response.status_code == 200:
            sample_data = sample_response.json()
            print("✅ Sample statement generated")
            print(f"Statement ID: {sample_data['sample_statement']['id']}")
        else:
            print(f"❌ Failed to get sample: {sample_response.status_code}")
            return
    except Exception as e:
        print(f"❌ Error getting sample: {e}")
        return
    
    # 3. Ingest the sample statement
    print("\n📤 Ingesting sample completed statement...")
    try:
        ingest_response = requests.post(
            f"{base_url}/api/xapi/ingest",
            json=sample_data['sample_statement'],
            headers={"Content-Type": "application/json"}
        )
        if ingest_response.status_code == 200:
            ingest_result = ingest_response.json()
            print("✅ Statement ingested successfully")
            print(f"Message ID: {ingest_result.get('message_id', 'N/A')}")
        else:
            print(f"❌ Ingestion failed: {ingest_response.status_code}")
            print(f"Response: {ingest_response.text}")
            return
    except Exception as e:
        print(f"❌ Error ingesting statement: {e}")
        return
    
    # 4. Wait a moment for processing
    print("\n⏳ Waiting for ETL processing (10 seconds)...")
    time.sleep(10)
    
    # 5. Run the diagnostic
    print("\n🔬 Running completed activities diagnostic...")
    try:
        diagnostic_response = requests.get(f"{base_url}/api/debug/completed-activities?hours_back=1&verbose=true")
        if diagnostic_response.status_code == 200:
            diagnostic_data = diagnostic_response.json()
            print("✅ Diagnostic completed")
            
            # Display results
            print(f"\n📊 Results:")
            print(f"  • Total completed found: {diagnostic_data['total_completed_found']}")
            print(f"  • In recent memory: {diagnostic_data['completed_in_recent_memory']}")
            print(f"  • In BigQuery: {diagnostic_data['completed_in_bigquery']}")
            print(f"  • Completion rate: {diagnostic_data['missing_completed_analysis']['completion_rate_percent']}%")
            
            # Show recommendations
            print(f"\n💡 Recommendations:")
            for rec in diagnostic_data['recommendations']:
                print(f"  • {rec}")
                
            # Show verb patterns if available
            if diagnostic_data['completed_verb_patterns'] and not diagnostic_data['completed_verb_patterns'][0].get('error'):
                print(f"\n🎯 Recent Verb Patterns:")
                for verb in diagnostic_data['completed_verb_patterns'][:5]:
                    if verb.get('is_completed'):
                        print(f"  • ✅ {verb['verb_display']} ({verb['count']} statements)")
                    else:
                        print(f"  • ⚪ {verb['verb_display']} ({verb['count']} statements)")
        else:
            print(f"❌ Diagnostic failed: {diagnostic_response.status_code}")
            print(f"Response: {diagnostic_response.text}")
    except Exception as e:
        print(f"❌ Error running diagnostic: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Diagnostic complete!")

if __name__ == "__main__":
    test_completed_activities()
