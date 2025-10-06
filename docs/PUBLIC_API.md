# Public Data API Documentation

## Overview

The Public Data API provides secure, validated access to learning analytics data for external consumers. All endpoints use comprehensive data validation to ensure data quality and prevent false/placeholder values from reaching consumers.

**Base URL**: `http://localhost:8000/api/public`

## Authentication

Currently, the public API endpoints are open access. For production use, consider implementing API key authentication.

## Data Validation

All endpoints use the centralized data validation system that:
- Detects and removes false/placeholder values (`false`, `no data`, `null`, `undefined`, etc.)
- Validates data types and converts values appropriately
- Provides fallback values for missing or invalid data
- Logs validation issues for monitoring

## Endpoints

### 1. Health Check

**GET** `/api/public/health`

Check the health status of the public API and database connection.

**Response Example**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "database_connected": true,
    "tables_available": 15,
    "data_validation": "enabled",
    "api_version": "1.0.0"
  },
  "metadata": {
    "description": "Public API health status",
    "last_updated": "2024-01-20T23:55:00Z",
    "refresh_interval": "1 minute"
  },
  "timestamp": "2024-01-20T23:55:00Z"
}
```

### 2. Metrics Overview

**GET** `/api/public/metrics/overview`

Get comprehensive overview metrics for the learning platform.

**Response Example**:
```json
{
  "success": true,
  "data": {
    "total_users": 150,
    "total_activities": 1250,
    "total_responses": 890,
    "total_questions": 45,
    "recent_activities_7_days": 125,
    "average_completion_rate": 78.5,
    "platform_health": "active"
  },
  "metadata": {
    "description": "Overview metrics for the learning platform",
    "data_source": "users, user_activities, user_responses, questions tables",
    "last_updated": "2024-01-20T23:55:00Z",
    "refresh_interval": "5 minutes"
  },
  "timestamp": "2024-01-20T23:55:00Z"
}
```

### 3. Lesson Completion Analytics

**GET** `/api/public/analytics/lesson-completion`

Get detailed lesson completion analytics with performance statistics.

**Response Example**:
```json
{
  "success": true,
  "data": {
    "lessons": [
      {
        "lesson_number": 1,
        "lesson_name": "Introduction to Learning",
        "users_started": 150,
        "users_completed": 135,
        "completion_rate": 90.0,
        "total_interactions": 450
      },
      {
        "lesson_number": 2,
        "lesson_name": "Advanced Concepts",
        "users_started": 135,
        "users_completed": 98,
        "completion_rate": 72.6,
        "total_interactions": 325
      }
    ],
    "summary": {
      "total_lessons": 8,
      "total_users_started": 1200,
      "total_users_completed": 890,
      "average_completion_rate": 78.5,
      "best_performing_lesson": {
        "lesson_number": 1,
        "completion_rate": 90.0
      },
      "worst_performing_lesson": {
        "lesson_number": 5,
        "completion_rate": 65.2
      }
    }
  },
  "metadata": {
    "description": "Lesson completion analytics with detailed statistics",
    "data_source": "lessons, user_activities, user_responses tables",
    "last_updated": "2024-01-20T23:55:00Z",
    "refresh_interval": "10 minutes"
  },
  "timestamp": "2024-01-20T23:55:00Z"
}
```

### 4. User Engagement Analytics

**GET** `/api/public/analytics/user-engagement`

Get user engagement analytics with activity patterns and participation statistics.

**Response Example**:
```json
{
  "success": true,
  "data": {
    "user_engagement": [
      {
        "user_id": "user123",
        "total_activities": 45,
        "lessons_accessed": 8,
        "first_activity": "2024-01-15T10:30:00Z",
        "last_activity": "2024-01-20T15:45:00Z",
        "hours_engaged": 12.5
      }
    ],
    "engagement_summary": {
      "total_users": 150,
      "total_activities": 1250,
      "average_activities_per_user": 8.3,
      "engagement_categories": {
        "high": 25,
        "medium": 45,
        "low": 80
      }
    },
    "activity_trends": [
      {
        "activity_date": "2024-01-20",
        "activities": 45,
        "active_users": 32
      }
    ]
  },
  "metadata": {
    "description": "User engagement analytics with activity patterns",
    "data_source": "user_activities table",
    "last_updated": "2024-01-20T23:55:00Z",
    "refresh_interval": "15 minutes"
  },
  "timestamp": "2024-01-20T23:55:00Z"
}
```

### 5. Sample Data

**GET** `/api/public/data/sample`

Get a small sample of real data from various tables for testing and development.

**Response Example**:
```json
{
  "success": true,
  "data": {
    "sample_users": [
      {
        "id": 1,
        "user_id": "user123",
        "cohort": "2024-Q1"
      }
    ],
    "sample_activities": [
      {
        "id": 1,
        "user_id": "user123",
        "lesson_id": 1,
        "activity_type": "completed",
        "created_at": "2024-01-20T15:45:00Z"
      }
    ],
    "sample_responses": [
      {
        "id": 1,
        "user_id": "user123",
        "question_id": 1,
        "response": "Excellent course material",
        "created_at": "2024-01-20T15:45:00Z"
      }
    ],
    "sample_lessons": [
      {
        "id": 1,
        "lesson_name": "Introduction to Learning",
        "lesson_number": 1
      }
    ],
    "data_quality": {
      "total_records": 21,
      "validation_status": "validated",
      "false_indicators_removed": true
    }
  },
  "metadata": {
    "description": "Sample data for API testing and development",
    "data_source": "users, user_activities, user_responses, lessons tables",
    "last_updated": "2024-01-20T23:55:00Z",
    "refresh_interval": "1 hour",
    "note": "This is a small sample of real data for testing purposes"
  },
  "timestamp": "2024-01-20T23:55:00Z"
}
```

## Error Responses

All endpoints return consistent error responses:

```json
{
  "success": false,
  "data": {},
  "metadata": {
    "description": "Error description",
    "last_updated": "2024-01-20T23:55:00Z"
  },
  "timestamp": "2024-01-20T23:55:00Z"
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad request (invalid parameters)
- `500`: Internal server error (database connection issues)

## Usage Examples

### cURL Examples

**Health Check**:
```bash
curl -X GET "http://localhost:8000/api/public/health"
```

**Metrics Overview**:
```bash
curl -X GET "http://localhost:8000/api/public/metrics/overview"
```

**Lesson Completion Analytics**:
```bash
curl -X GET "http://localhost:8000/api/public/analytics/lesson-completion"
```

**User Engagement Analytics**:
```bash
curl -X GET "http://localhost:8000/api/public/analytics/user-engagement"
```

**Sample Data**:
```bash
curl -X GET "http://localhost:8000/api/public/data/sample"
```

### Python Examples

```python
import requests

base_url = "http://localhost:8000/api/public"

# Get metrics overview
response = requests.get(f"{base_url}/metrics/overview")
if response.status_code == 200:
    data = response.json()
    print(f"Total users: {data['data']['total_users']}")
    print(f"Platform health: {data['data']['platform_health']}")

# Get lesson completion analytics
response = requests.get(f"{base_url}/analytics/lesson-completion")
if response.status_code == 200:
    data = response.json()
    lessons = data['data']['lessons']
    for lesson in lessons:
        print(f"Lesson {lesson['lesson_number']}: {lesson['completion_rate']}% completion")
```

## Data Quality Guarantees

1. **No False Data**: All endpoints use validation to prevent false/placeholder values
2. **Type Safety**: Data is validated and converted to appropriate types
3. **Consistent Format**: All responses follow the same structure
4. **Metadata**: Each response includes metadata about data sources and refresh intervals
5. **Error Handling**: Comprehensive error handling with meaningful messages

## Rate Limiting

Currently, no rate limiting is implemented. For production use, consider implementing rate limiting based on your requirements.

## Support

For questions or issues with the Public Data API, please refer to the main application documentation or contact the development team.
