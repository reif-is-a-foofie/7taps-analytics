#!/usr/bin/env python3
"""
Live deployment diagnostic script for completed xAPI activities.
Tests the live Cloud Run deployment instead of localhost.
"""

import requests
import json
import time
from datetime import datetime, timezone

# Your live deployment URL pattern
LIVE_URL = "https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app"

def test_completed_activities_live():
    """Test the completed activities diagnostic on live deployment."""
    
    print("🔍 Testing Completed Activities Diagnostic - LIVE DEPLOYMENT")
    print("=" * 60)
    print(f"🌐 Target URL: {LIVE_URL}")
    
    # 1. Check if live app is running
    try:
        health_response = requests.get(f"{LIVE_URL}/health", timeout=10)
        if health_response.status_code == 200:
            print("✅ Live app is running")
            health_data = health_response.json()
            print(f"   Status: {health_data.get('status', 'unknown')}")
        else:
            print(f"⚠️ Live app responded with status {health_response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Live app not accessible: {e}")
        print("💡 Check if the deployment is active and accessible")
        return
    
    # 2. Get a sample completed statement
    print("\n📋 Getting sample completed statement from live deployment...")
    try:
        sample_response = requests.get(f"{LIVE_URL}/api/debug/completed-activities/sample", timeout=10)
        if sample_response.status_code == 200:
            sample_data = sample_response.json()
            print("✅ Sample statement generated from live deployment")
            print(f"Statement ID: {sample_data['sample_statement']['id']}")
        else:
            print(f"❌ Failed to get sample from live: {sample_response.status_code}")
            print(f"Response: {sample_response.text}")
            return
    except Exception as e:
        print(f"❌ Error getting sample from live: {e}")
        return
    
    # 3. Ingest the sample statement to live deployment
    print("\n📤 Ingesting sample completed statement to live deployment...")
    try:
        ingest_response = requests.post(
            f"{LIVE_URL}/api/xapi/ingest",
            json=sample_data['sample_statement'],
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        if ingest_response.status_code == 200:
            ingest_result = ingest_response.json()
            print("✅ Statement ingested successfully to live deployment")
            print(f"Message ID: {ingest_result.get('message_id', 'N/A')}")
        else:
            print(f"❌ Live ingestion failed: {ingest_response.status_code}")
            print(f"Response: {ingest_response.text}")
            return
    except Exception as e:
        print(f"❌ Error ingesting to live deployment: {e}")
        return
    
    # 4. Wait for ETL processing on live deployment
    print("\n⏳ Waiting for live ETL processing (15 seconds)...")
    time.sleep(15)
    
    # 5. Run the diagnostic on live deployment
    print("\n🔬 Running completed activities diagnostic on live deployment...")
    try:
        diagnostic_response = requests.get(
            f"{LIVE_URL}/api/debug/completed-activities?hours_back=1&verbose=true",
            timeout=15
        )
        if diagnostic_response.status_code == 200:
            diagnostic_data = diagnostic_response.json()
            print("✅ Live diagnostic completed")
            
            # Display results
            print(f"\n📊 Live Deployment Results:")
            print(f"  • Total completed found: {diagnostic_data['total_completed_found']}")
            print(f"  • In recent memory: {diagnostic_data['completed_in_recent_memory']}")
            print(f"  • In BigQuery: {diagnostic_data['completed_in_bigquery']}")
            
            if 'missing_completed_analysis' in diagnostic_data:
                analysis = diagnostic_data['missing_completed_analysis']
                print(f"  • Total activities: {analysis.get('total_activities_in_period', 'N/A')}")
                print(f"  • Completion rate: {analysis.get('completion_rate_percent', 'N/A')}%")
            
            # Show recommendations
            print(f"\n💡 Live Deployment Recommendations:")
            for rec in diagnostic_data['recommendations']:
                print(f"  • {rec}")
                
            # Show verb patterns if available
            if diagnostic_data['completed_verb_patterns'] and not diagnostic_data['completed_verb_patterns'][0].get('error'):
                print(f"\n🎯 Recent Verb Patterns (Live):")
                for verb in diagnostic_data['completed_verb_patterns'][:5]:
                    if verb.get('is_completed'):
                        print(f"  • ✅ {verb['verb_display']} ({verb['count']} statements)")
                    else:
                        print(f"  • ⚪ {verb['verb_display']} ({verb['count']} statements)")
        else:
            print(f"❌ Live diagnostic failed: {diagnostic_response.status_code}")
            print(f"Response: {diagnostic_response.text}")
    except Exception as e:
        print(f"❌ Error running live diagnostic: {e}")
    
    # 6. Check live BigQuery connection
    print("\n🔗 Testing live BigQuery connection...")
    try:
        bq_response = requests.get(f"{LIVE_URL}/api/bigquery/test", timeout=10)
        if bq_response.status_code == 200:
            bq_data = bq_response.json()
            print("✅ Live BigQuery connection working")
            print(f"   Status: {bq_data.get('status', 'unknown')}")
        else:
            print(f"⚠️ Live BigQuery test failed: {bq_response.status_code}")
    except Exception as e:
        print(f"❌ Live BigQuery test error: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 Live deployment diagnostic complete!")
    print(f"🌐 Full diagnostic URL: {LIVE_URL}/api/debug/completed-activities")

if __name__ == "__main__":
    test_completed_activities_live()
