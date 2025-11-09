# xAPI Ingestion Endpoint - Configuration Instructions

## Endpoint Details

**URL:** `https://taps-analytics-ui-euvwb5vwea-uc.a.run.app/statements`

**Authentication:** Basic Authentication
- **Username:** `7taps.team`
- **Password:** `PracticeofLife`

**Supported Methods:** 
- ✅ PUT
- ✅ POST

**Content-Type:** `application/json`

## Test Results

✅ **PUT Request:** HTTP 200 - Successfully processed  
✅ **POST Request:** HTTP 200 - Successfully processed  
✅ **Authentication:** Correctly rejects invalid/missing credentials (401)

## Example Request

### Using cURL (PUT):
```bash
curl -X PUT https://taps-analytics-ui-euvwb5vwea-uc.a.run.app/statements \
  -H "Content-Type: application/json" \
  -u "7taps.team:PracticeofLife" \
  -d '{
    "actor": {
      "mbox": "mailto:user@example.com",
      "name": "John Doe"
    },
    "verb": {
      "id": "http://adlnet.gov/expapi/verbs/experienced",
      "display": {
        "en-US": "experienced"
      }
    },
    "object": {
      "id": "http://example.com/activity/123",
      "definition": {
        "name": {
          "en-US": "Activity Name"
        }
      }
    },
    "timestamp": "2025-11-09T02:45:00Z"
  }'
```

### Using cURL (POST):
```bash
curl -X POST https://taps-analytics-ui-euvwb5vwea-uc.a.run.app/statements \
  -H "Content-Type: application/json" \
  -u "7taps.team:PracticeofLife" \
  -d '[{
    "actor": {
      "mbox": "mailto:user@example.com"
    },
    "verb": {
      "id": "http://adlnet.gov/expapi/verbs/experienced"
    },
    "object": {
      "id": "http://example.com/activity/123"
    }
  }]'
```

## Expected Response

**Success Response (HTTP 200):**
```json
{
  "status": "success",
  "processed_count": 1,
  "statements": [
    {
      "statement_id": "7f72fb06-4383-459c-9736-766f8d560751",
      "message_id": "16850119978887980",
      "timestamp": "2025-11-09T02:45:00+00:00"
    }
  ],
  "message": "Successfully queued 1 xAPI statements from 7taps (PUT)",
  "timestamp": "2025-11-09T02:46:23.686012+00:00"
}
```

**Error Response - Invalid Credentials (HTTP 401):**
```json
{
  "detail": "Invalid credentials"
}
```

## Notes

- The endpoint accepts both single statements and arrays of statements
- Statements are queued to Google Cloud Pub/Sub for processing
- Duplicate detection is enabled (re-sending the same statement will return "duplicate" status)
- All statements are validated against xAPI specification
- Processing is asynchronous - statements are queued immediately and processed in the background

## Support

If you encounter any issues, please verify:
1. The URL is correct: `https://taps-analytics-ui-euvwb5vwea-uc.a.run.app/statements`
2. Credentials are exactly: `7taps.team:PracticeofLife`
3. Content-Type header is set to `application/json`
4. The request body contains valid xAPI statement(s)

