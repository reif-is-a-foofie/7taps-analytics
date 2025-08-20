#!/usr/bin/env python3
"""
Script to backfill sample data for lessons 6-8 to make them show up in the dashboard.

This script will:
1. Create sample user responses for lessons 6-8
2. Link them to existing users
3. Ensure the dashboard shows engagement data for these lessons
"""

import os
import sys
import asyncio
import json
import requests
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent.parent / "app"))

# Heroku app URL
HEROKU_URL = "https://seventaps-analytics-5135b3a0701a.herokuapp.com"

# Sample responses for different lesson types
SAMPLE_RESPONSES = {
    6: [  # Focus = Superpower
        "I'm trying to focus on one task at a time",
        "I turn off notifications when working",
        "I use the Pomodoro technique",
        "I create a dedicated workspace",
        "I practice mindfulness before starting work"
    ],
    7: [  # Social Media + You
        "I limit my social media time to 30 minutes per day",
        "I unfollow accounts that make me feel bad",
        "I use social media for learning and connection",
        "I take breaks from social media on weekends",
        "I'm more mindful about what I post"
    ],
    8: [  # Less Stress. More Calm
        "I practice deep breathing exercises",
        "I take regular breaks throughout the day",
        "I prioritize sleep and rest",
        "I spend time in nature",
        "I practice gratitude daily"
    ]
}

async def backfill_lesson_data():
    """Backfill sample data for lessons 6-8."""
    try:
        print("🚀 Starting backfill for lessons 6-8...")
        
        # First, get existing users
        print("📋 Getting existing users...")
        users_response = requests.get(f"{HEROKU_URL}/api/data-explorer/table/users?limit=50")
        if users_response.status_code != 200:
            print(f"❌ Failed to get users: {users_response.text}")
            return False
        
        users_data = users_response.json()
        if not users_data.get('data'):
            print("❌ No users found in database")
            return False
        
        user_ids = [user['user_id'] for user in users_data['data']]
        print(f"✅ Found {len(user_ids)} users")
        
        # Create sample responses for each lesson
        for lesson_number in [6, 7, 8]:
            print(f"📝 Creating sample data for lesson {lesson_number}...")
            
            # Get 3-5 random users for this lesson
            lesson_users = random.sample(user_ids, min(5, len(user_ids)))
            
            for i, user_id in enumerate(lesson_users):
                # Create multiple responses per user (2-4 responses)
                num_responses = random.randint(2, 4)
                
                for response_num in range(num_responses):
                    # Create a sample response
                    response_data = {
                        "user_id": user_id,
                        "lesson_number": lesson_number,
                        "response_text": random.choice(SAMPLE_RESPONSES[lesson_number]),
                        "response_value": random.choice(["1", "2", "3", "4", "5"]),
                        "is_correct": random.choice([True, False]),
                        "score_raw": random.randint(70, 100),
                        "score_scaled": random.uniform(0.7, 1.0),
                        "duration_seconds": random.randint(30, 180),
                        "timestamp": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                        "source": "backfill_script"
                    }
                    
                    # Insert via API
                    response = requests.post(
                        f"{HEROKU_URL}/api/data-explorer/insert/user-response",
                        json=response_data,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        print(f"  ✅ User {user_id}: Response {response_num + 1}")
                    else:
                        print(f"  ❌ User {user_id}: Failed to insert response {response_num + 1}")
                        print(f"     Error: {response.text}")
        
        print("🎉 Backfill completed!")
        
        # Verify the data
        print("🔍 Verifying data...")
        for lesson_number in [6, 7, 8]:
            verify_response = requests.get(f"{HEROKU_URL}/api/data-explorer/table/user_responses?lesson_number={lesson_number}&limit=5")
            if verify_response.status_code == 200:
                data = verify_response.json()
                count = len(data.get('data', []))
                print(f"  Lesson {lesson_number}: {count} responses")
            else:
                print(f"  Lesson {lesson_number}: Failed to verify")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during backfill: {e}")
        return False

async def create_insert_endpoint():
    """Create a temporary endpoint to insert user responses if it doesn't exist."""
    try:
        print("🔧 Checking if insert endpoint exists...")
        
        # Try to access the endpoint
        test_response = requests.post(
            f"{HEROKU_URL}/api/data-explorer/insert/user-response",
            json={"test": "data"},
            timeout=10
        )
        
        if test_response.status_code == 404:
            print("⚠️  Insert endpoint not found. Creating temporary endpoint...")
            
            # We'll need to add this endpoint to the data_explorer.py file
            # For now, let's use a different approach - direct database insertion
            return await insert_direct_to_db()
        else:
            print("✅ Insert endpoint exists")
            return True
            
    except Exception as e:
        print(f"❌ Error checking endpoint: {e}")
        return False

async def insert_direct_to_db():
    """Insert data directly to database using existing endpoints."""
    try:
        print("🗄️  Using direct database insertion...")
        
        # Get database connection info
        db_response = requests.get(f"{HEROKU_URL}/test-db")
        if db_response.status_code != 200:
            print("❌ Cannot connect to database")
            return False
        
        # For now, let's use the existing focus group import endpoint
        # We'll create a simple CSV with our sample data
        csv_data = []
        headers = ["Learner", "Card", "Card type", "Lesson Number", "Global Q#", "PDF Page #", "Response"]
        
        # Create sample data
        sample_users = ["Sample_User_1", "Sample_User_2", "Sample_User_3", "Sample_User_4", "Sample_User_5"]
        
        for lesson_number in [6, 7, 8]:
            for user in sample_users:
                for q_num in range(1, 4):  # 3 questions per lesson
                    csv_data.append([
                        user,
                        f"Card {q_num} (Form): Sample question for lesson {lesson_number}",
                        "Form",
                        str(lesson_number),
                        str(q_num),
                        str(10 + q_num),
                        random.choice(SAMPLE_RESPONSES[lesson_number])
                    ])
        
        # Convert to CSV string
        csv_string = "\n".join([",".join(headers)] + [",".join(row) for row in csv_data])
        
        # Import via focus group endpoint
        import_response = requests.post(
            f"{HEROKU_URL}/api/import/focus-group",
            json={
                "csv_data": csv_string,
                "cohort_name": "backfill_lessons_6_8"
            },
            timeout=300
        )
        
        if import_response.status_code == 200:
            print("✅ Successfully imported sample data")
            return True
        else:
            print(f"❌ Failed to import: {import_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error in direct insertion: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(backfill_lesson_data())
