#!/usr/bin/env python3
"""Test script to send a completed xAPI statement to the /statements endpoint."""

import requests
import json
import uuid
from datetime import datetime, timezone

# Test configuration
URL = "https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app/statements"
CREDENTIALS = ("7taps.team", "PracticeofLife")
CONTENT_TYPE = "application/json"

def create_completed_statement():
    """Create a test xAPI statement for a completed action."""
    statement_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    
    statement = {
        "id": statement_id,
        "timestamp": timestamp,
        "actor": {
            "mbox": "mailto:test@example.com",
            "name": "Test User",
            "objectType": "Agent"
        },
        "verb": {
            "id": "http://adlnet.gov/expapi/verbs/completed",
            "display": {
                "en-US": "completed"
            }
        },
        "object": {
            "id": "https://courses.practiceoflife.com/m/test-lesson-completed",
            "definition": {
                "name": {
                    "en-US": "Test Lesson - Completed"
                },
                "description": {
                    "en-US": "A test lesson that was completed"
                }
            },
            "objectType": "Activity"
        },
        "result": {
            "completion": True,
            "success": True,
            "score": {
                "scaled": 1.0
            }
        },
        "context": {
            "platform": "7taps",
            "language": "en-US"
        }
    }
    
    return statement

def test_post_method():
    """Test POST method with completed statement."""
    print("🧪 Testing POST method with completed statement...")
    
    statement = create_completed_statement()
    
    try:
        response = requests.post(
            URL,
            json=statement,
            auth=CREDENTIALS,
            headers={"Content-Type": CONTENT_TYPE},
            timeout=30
        )
        
        print(f"📤 POST Response Status: {response.status_code}")
        print(f"📤 POST Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ POST request successful!")
            try:
                response_data = response.json()
                print(f"📤 POST Response Body: {json.dumps(response_data, indent=2)}")
            except:
                print(f"📤 POST Response Text: {response.text}")
        else:
            print(f"❌ POST request failed!")
            print(f"📤 POST Response Text: {response.text}")
            
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ POST request error: {e}")
        return False

def test_put_method():
    """Test PUT method with completed statement."""
    print("\n🧪 Testing PUT method with completed statement...")
    
    statement = create_completed_statement()
    statement_id = statement["id"]
    
    # Add statementId as query parameter for PUT
    put_url = f"{URL}?statementId={statement_id}"
    
    try:
        response = requests.put(
            put_url,
            json=statement,
            auth=CREDENTIALS,
            headers={"Content-Type": CONTENT_TYPE},
            timeout=30
        )
        
        print(f"📤 PUT Response Status: {response.status_code}")
        print(f"📤 PUT Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ PUT request successful!")
            try:
                response_data = response.json()
                print(f"📤 PUT Response Body: {json.dumps(response_data, indent=2)}")
            except:
                print(f"📤 PUT Response Text: {response.text}")
        else:
            print(f"❌ PUT request failed!")
            print(f"📤 PUT Response Text: {response.text}")
            
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ PUT request error: {e}")
        return False

def check_dashboard():
    """Check if the completed statement appears on the dashboard."""
    print("\n🔍 Checking dashboard for completed statement...")
    
    dashboard_url = "https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app/ui/data-explorer"
    
    try:
        response = requests.get(dashboard_url, timeout=30)
        
        if response.status_code == 200:
            print("✅ Dashboard accessible!")
            # Look for completed verbs in the response
            if "completed" in response.text.lower():
                print("🎯 Found 'completed' verb in dashboard!")
            else:
                print("⚠️  No 'completed' verb found in dashboard yet")
                
            # Look for our test statement ID
            statement_id = create_completed_statement()["id"]
            if statement_id in response.text:
                print(f"🎯 Found our test statement ID: {statement_id}")
            else:
                print("⚠️  Our test statement ID not found yet")
                
        else:
            print(f"❌ Dashboard check failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Dashboard check error: {e}")

def main():
    """Run the complete test."""
    print("🚀 Starting completed statement test...")
    print(f"🎯 Target URL: {URL}")
    print(f"🔐 Credentials: {CREDENTIALS[0]}:{CREDENTIALS[1]}")
    
    # Test both methods
    post_success = test_post_method()
    put_success = test_put_method()
    
    # Check dashboard
    check_dashboard()
    
    # Summary
    print("\n📊 Test Summary:")
    print(f"   POST Method: {'✅ Success' if post_success else '❌ Failed'}")
    print(f"   PUT Method: {'✅ Success' if put_success else '❌ Failed'}")
    
    if post_success or put_success:
        print("\n🎉 At least one method worked! Check the dashboard:")
        print("   https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app/ui/data-explorer")
    else:
        print("\n💥 Both methods failed - there's an issue with the endpoint")

if __name__ == "__main__":
    main()
