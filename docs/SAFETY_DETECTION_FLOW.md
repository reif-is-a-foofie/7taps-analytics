# Safety Detection Flow

## Overview
The safety system analyzes all incoming xAPI statement content for potentially unsafe language, mental health concerns, and harmful content.

## Process Flow

### 1. Content Ingestion
**Entry Points:**
- `/api/xapi/ingest` - Direct xAPI statement ingestion
- `/statements` (POST/PUT) - 7taps webhook endpoint

**File:** `app/api/xapi.py`
- Function: `_prepare_statement_payload()`
- Line 94-96: Calls `analyze_xapi_statement_content(payload)`
- Stores result in `payload["ai_content_analysis"]`

### 2. Content Extraction
**File:** `app/api/ai_flagged_content.py`
- Function: `analyze_xapi_statement_content()`
- Extracts content from:
  - `result.response` - User's text response
  - `object.definition.name` - Activity name
  - `result.extensions` - Additional text fields
- Combines into: `"Response: {response} | Activity: {name} | Extension {key}: {value}"`

### 3. Safety Analysis
**File:** `app/services/ai_service_client.py` → `app/api/batch_ai_safety.py`

**Two-Stage Process:**

#### Stage 1: Obvious Flag Check (Local Rules)
**File:** `app/api/batch_ai_safety.py`
- Function: `_check_obvious_flags()`
- Uses regex patterns:
  - **Critical:** `kill myself`, `suicide`, `end my life`, `hurt myself`, `self harm`
  - **High:** `rape`, `raped`, `abuse`, `abused`, `hurt you`, `kill you`
  - **Medium:** `depressed`, `depression`, `hopeless`, `empty inside`, `nothing matters`

**If obvious flag detected:**
- ✅ Runs AI analysis **immediately** (safety first!)
- Uses Gemini 2.0 Flash model
- Returns flagged result with severity and suggested actions

**If no obvious flag:**
- ⏳ Queues for batch processing

#### Stage 2: Batch AI Analysis
**Triggers:**
- 100,000 tokens accumulated OR
- 2 hours elapsed OR
- 50 items queued

**Process:**
- Batches multiple items together
- Uses Gemini 2.5 Flash model
- Analyzes all items in one API call (cost-efficient)
- Processes results and flags any concerning content

### 4. Analysis Results
**Return Format:**
```json
{
  "is_flagged": true/false,
  "severity": "critical/high/medium/low",
  "flagged_reasons": ["specific reasons"],
  "confidence_score": 0.0-1.0,
  "suggested_actions": ["recommended actions"],
  "analysis_metadata": {
    "analysis_method": "immediate_ai" | "batch_ai" | "obvious_flag_fallback",
    "processing_time": "immediate" | "batch",
    "batch_id": "..."
  }
}
```

### 5. Storage & Display
**Storage:**
- Results stored in `payload["ai_content_analysis"]`
- Statement stored in `recent_statements` dict (in-memory, last 1000)
- Published to Pub/Sub for ETL processing

**Display:**
- `/ui/safety` dashboard shows flagged content
- Function: `get_recent_flagged_statements()` in `app/ui/safety.py`
- Reads from `recent_statements` and filters for `is_flagged: true`
- Shows both AI-flagged and trigger-word-flagged content

## Current Status

### ✅ Working Components
1. **Content Extraction** - Extracts text from xAPI statements
2. **Obvious Flag Detection** - Local regex patterns work
3. **Batch Queue** - Items queued for batch processing
4. **AI Analysis** - Gemini API integration configured

### ⚠️ Potential Issues
1. **Batch Processing** - Background processor may not be running
2. **Storage** - Results only in memory (`recent_statements`), not persisted
3. **Trigger Words** - Separate system (`trigger_word_alerts.py`) also runs
4. **Error Handling** - Falls back to keyword matching if AI fails

## Testing the Flow

### Test 1: Obvious Flag (Should Process Immediately)
```bash
curl -X POST http://localhost:8000/api/xapi/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "actor": {"mbox": "mailto:test@example.com"},
    "verb": {"id": "http://adlnet.gov/expapi/verbs/answered"},
    "object": {"id": "test-activity"},
    "result": {"response": "I want to kill myself"}
  }'
```

**Expected:** Immediate AI analysis, flagged result returned

### Test 2: Normal Content (Should Queue)
```bash
curl -X POST http://localhost:8000/api/xapi/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "actor": {"mbox": "mailto:test@example.com"},
    "verb": {"id": "http://adlnet.gov/expapi/verbs/answered"},
    "object": {"id": "test-activity"},
    "result": {"response": "I learned a lot today"}
  }'
```

**Expected:** Queued for batch processing

### Test 3: Check Batch Status
```bash
curl http://localhost:8000/api/batch-ai-safety/status
```

**Expected:** Shows queue size, last batch time, estimated tokens

### Test 4: View Flagged Content
```bash
curl http://localhost:8000/ui/safety
```

**Expected:** Dashboard showing flagged statements (if any)

## Configuration

### Required Settings
- `GOOGLE_AI_API_KEY` - Gemini API key (set in GCP Secret Manager)
- `GOOGLE_AI_API_KEY` must be configured for AI analysis to work

### Fallback Behavior
- If API key not configured → Uses keyword matching only
- If AI analysis fails → Uses obvious flag result as fallback
- If batch processing fails → Logs error, continues processing

## Next Steps to Verify

1. **Check if batch processor is running:**
   - Look for background task in `main.py`
   - Check logs for batch processing activity

2. **Test with real content:**
   - Send test statements with concerning language
   - Verify they get flagged immediately
   - Check dashboard shows flagged content

3. **Monitor batch processing:**
   - Check queue size grows
   - Verify batches process after 2 hours or 100k tokens
   - Confirm flagged items appear in dashboard

4. **Verify persistence:**
   - Check if flagged content persists beyond `recent_statements`
   - May need to store in BigQuery or database

