#!/usr/bin/env python3
"""
Test BigQuery connection and data explorer endpoints.
Verifies that the database connection works and response structure is correct.
"""

import sys
import json
import httpx
from typing import Dict, Any

# Base URL - use environment variable or default to production
BASE_URL = "https://taps-analytics-ui-euvwb5vwea-uc.a.run.app"

def test_bigquery_connection() -> Dict[str, Any]:
    """Test basic BigQuery connection."""
    print("🔍 Testing BigQuery Connection...")
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(f"{BASE_URL}/api/bigquery/test")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Connection Status: {data.get('status')}")
                print(f"   Project: {data.get('project_id')}")
                print(f"   Dataset: {data.get('dataset')}")
                print(f"   Tables Found: {data.get('tables_found')}")
                print(f"   Sample Tables: {data.get('sample_tables', [])[:5]}")
                return {"success": True, "data": data}
            else:
                print(f"❌ Connection Failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return {"success": False, "error": f"HTTP {response.status_code}", "response": response.text}
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return {"success": False, "error": str(e)}

def test_bigquery_query_endpoint() -> Dict[str, Any]:
    """Test BigQuery query endpoint with a simple query."""
    print("\n🔍 Testing BigQuery Query Endpoint...")
    try:
        # Simple test query
        test_query = "SELECT COUNT(*) as total FROM taps_data.statements LIMIT 1"
        
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{BASE_URL}/api/analytics/bigquery/query",
                params={"query": test_query}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Query Status: {data.get('success')}")
                print(f"   Row Count: {data.get('row_count')}")
                print(f"   Execution Time: {data.get('execution_time')}s")
                
                # Check response structure
                if data.get("success"):
                    response_data = data.get("data", {})
                    rows = response_data.get("rows", [])
                    print(f"   Response Structure: data.data.rows = {len(rows)} rows")
                    
                    if rows:
                        print(f"   Sample Row Keys: {list(rows[0].keys())}")
                        print(f"   Sample Row: {json.dumps(rows[0], indent=2)[:200]}...")
                    
                    return {
                        "success": True,
                        "data": data,
                        "structure_correct": "data" in data and "rows" in data.get("data", {}),
                        "row_count": data.get("row_count", 0)
                    }
                else:
                    print(f"❌ Query Failed: {data.get('error')}")
                    return {"success": False, "error": data.get("error"), "data": data}
            else:
                print(f"❌ Query Endpoint Failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return {"success": False, "error": f"HTTP {response.status_code}", "response": response.text}
    except Exception as e:
        print(f"❌ Query Error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

def test_data_explorer_query() -> Dict[str, Any]:
    """Test the exact query used by data explorer."""
    print("\n🔍 Testing Data Explorer Query...")
    try:
        # This is the exact query from get_recent_bigquery_data
        query = """
        SELECT 
            timestamp,
            actor_id,
            actor_mbox,
            verb_display,
            object_name,
            result_completion,
            result_success,
            result_score_scaled,
            result_response,
            context_platform,
            raw_json,
            'ETL Processed' as data_type,
            statement_id
        FROM taps_data.statements 
        ORDER BY timestamp DESC 
        LIMIT 10
        """
        
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{BASE_URL}/api/analytics/bigquery/query",
                params={"query": query}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Data Explorer Query Status: {data.get('success')}")
                print(f"   Row Count: {data.get('row_count')}")
                
                if data.get("success"):
                    response_data = data.get("data", {})
                    rows = response_data.get("rows", [])
                    
                    # Verify structure matches what pubsub_feed.py expects
                    has_rows = "rows" in response_data
                    has_row_count = "row_count" in data
                    
                    print(f"   Structure Check:")
                    print(f"     - data.data.rows exists: {has_rows}")
                    print(f"     - data.row_count exists: {has_row_count}")
                    print(f"     - Rows found: {len(rows)}")
                    
                    if rows:
                        print(f"   Sample Statement:")
                        sample = rows[0]
                        print(f"     - statement_id: {sample.get('statement_id', 'N/A')}")
                        print(f"     - timestamp: {sample.get('timestamp', 'N/A')}")
                        print(f"     - actor_id: {sample.get('actor_id', 'N/A')}")
                        print(f"     - verb_display: {sample.get('verb_display', 'N/A')}")
                    
                    return {
                        "success": True,
                        "structure_correct": has_rows and has_row_count,
                        "row_count": len(rows),
                        "data": data
                    }
                else:
                    print(f"❌ Query Failed: {data.get('error')}")
                    return {"success": False, "error": data.get("error")}
            else:
                print(f"❌ Query Failed: {response.status_code}")
                print(f"   Response: {response.text[:500]}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        print(f"❌ Query Error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

def test_connection_status_endpoint() -> Dict[str, Any]:
    """Test BigQuery connection status endpoint."""
    print("\n🔍 Testing Connection Status Endpoint...")
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(f"{BASE_URL}/api/analytics/bigquery/connection-status")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Connection Status: {data.get('status')}")
                print(f"   Dataset Exists: {data.get('dataset_exists')}")
                print(f"   Tables: {data.get('tables', {})}")
                return {"success": True, "data": data}
            else:
                print(f"❌ Status Endpoint Failed: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        print(f"❌ Status Error: {e}")
        return {"success": False, "error": str(e)}

def main():
    """Run all tests."""
    print("=" * 60)
    print("BigQuery Connection & Data Explorer Tests")
    print("=" * 60)
    
    results = {
        "connection": test_bigquery_connection(),
        "query_endpoint": test_bigquery_query_endpoint(),
        "data_explorer_query": test_data_explorer_query(),
        "connection_status": test_connection_status_endpoint()
    }
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = all(r.get("success", False) for r in results.values())
    
    for test_name, result in results.items():
        status = "✅ PASS" if result.get("success") else "❌ FAIL"
        print(f"{status} - {test_name}")
        if not result.get("success"):
            print(f"   Error: {result.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    if len(sys.argv) > 1:
        BASE_URL = sys.argv[1]
        print(f"Using custom base URL: {BASE_URL}")
    
    sys.exit(main())

