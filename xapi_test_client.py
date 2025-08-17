#!/usr/bin/env python3
"""
Simple xAPI Test Client for testing our LRS endpoint.
"""

import base64
import json
import uuid
from datetime import datetime

import requests


class xAPITestClient:
    """Simple xAPI test client for LRS testing."""

    def __init__(self, lrs_url, username, password):
        self.lrs_url = lrs_url.rstrip("/")
        self.username = username
        self.password = password
        self.auth_header = self._create_auth_header()

    def _create_auth_header(self):
        """Create Basic Authentication header."""
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def test_about_endpoint(self):
        """Test the /about endpoint."""
        url = f"{self.lrs_url}/about"
        headers = {"Authorization": self.auth_header}

        try:
            response = requests.get(url, headers=headers)
            print(f"✅ About endpoint: {response.status_code}")
            if response.status_code == 200:
                print(f"   Version: {response.json().get('version', 'unknown')}")
            return response
        except Exception as e:
            print(f"❌ About endpoint error: {e}")
            return None

    def test_post_statement(self, statement=None):
        """Test posting a statement."""
        url = f"{self.lrs_url}/statements"
        headers = {
            "Authorization": self.auth_header,
            "Content-Type": "application/json",
        }

        if statement is None:
            statement = self._create_sample_statement()

        try:
            response = requests.post(url, headers=headers, json=[statement])
            print(f"✅ Post statement: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   Processed: {result.get('processed_count', 0)} statements")
                print(f"   Message: {result.get('message', '')}")
            return response
        except Exception as e:
            print(f"❌ Post statement error: {e}")
            return None

    def test_get_statements(self):
        """Test getting statements."""
        url = f"{self.lrs_url}/statements"
        headers = {"Authorization": self.auth_header}

        try:
            response = requests.get(url, headers=headers)
            print(f"✅ Get statements: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   Message: {result.get('message', '')}")
            return response
        except Exception as e:
            print(f"❌ Get statements error: {e}")
            return None

    def _create_sample_statement(self):
        """Create a sample xAPI statement."""
        return {
            "id": str(uuid.uuid4()),
            "actor": {
                "objectType": "Agent",
                "account": {"homePage": "https://7taps.com", "name": "test-user-123"},
            },
            "verb": {
                "id": "http://adlnet.gov/expapi/verbs/completed",
                "display": {"en-US": "completed"},
            },
            "object": {
                "id": "https://7taps.com/courses/example-course",
                "objectType": "Activity",
                "definition": {
                    "name": {"en-US": "Example Course"},
                    "description": {"en-US": "A sample course for testing"},
                    "type": "http://adlnet.gov/expapi/activities/course",
                },
            },
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.3",
        }

    def create_completion_statement(self, user_id, course_id, score=None):
        """Create a completion statement."""
        statement = {
            "actor": {
                "objectType": "Agent",
                "account": {"homePage": "https://7taps.com", "name": user_id},
            },
            "verb": {
                "id": "http://adlnet.gov/expapi/verbs/completed",
                "display": {"en-US": "completed"},
            },
            "object": {
                "id": f"https://7taps.com/courses/{course_id}",
                "objectType": "Activity",
                "definition": {
                    "name": {"en-US": f"Course {course_id}"},
                    "type": "http://adlnet.gov/expapi/activities/course",
                },
            },
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.3",
        }

        if score is not None:
            statement["result"] = {
                "score": {"min": 0, "max": 100, "raw": score, "scaled": score / 100.0},
                "completion": True,
                "success": score >= 70,
            }

        return statement

    def create_started_statement(self, user_id, course_id):
        """Create a started statement."""
        return {
            "actor": {
                "objectType": "Agent",
                "account": {"homePage": "https://7taps.com", "name": user_id},
            },
            "verb": {
                "id": "http://adlnet.gov/expapi/verbs/started",
                "display": {"en-US": "started"},
            },
            "object": {
                "id": f"https://7taps.com/courses/{course_id}",
                "objectType": "Activity",
                "definition": {
                    "name": {"en-US": f"Course {course_id}"},
                    "type": "http://adlnet.gov/expapi/activities/course",
                },
            },
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.3",
        }

    def run_full_test(self):
        """Run a complete test suite."""
        print("🧪 Running xAPI LRS Test Suite")
        print("=" * 50)

        # Test about endpoint
        self.test_about_endpoint()
        print()

        # Test posting statements
        print("📝 Testing Statement Posting:")
        self.test_post_statement()
        print()

        # Test getting statements
        print("📖 Testing Statement Retrieval:")
        self.test_get_statements()
        print()

        # Test different statement types
        print("🎯 Testing Different Statement Types:")

        # Completion statement
        completion_stmt = self.create_completion_statement("user-456", "course-123", 85)
        self.test_post_statement(completion_stmt)

        # Started statement
        started_stmt = self.create_started_statement("user-789", "course-456")
        self.test_post_statement(started_stmt)

        print("=" * 50)
        print("✅ Test suite completed!")


def main():
    """Main test function."""
    # Configuration
    LRS_URL = "https://seventaps-analytics-5135b3a0701a.herokuapp.com"
    USERNAME = "7taps.team"
    PASSWORD = "PracticeofL!fe"

    # Create test client
    client = xAPITestClient(LRS_URL, USERNAME, PASSWORD)

    # Run tests
    client.run_full_test()


if __name__ == "__main__":
    main()
