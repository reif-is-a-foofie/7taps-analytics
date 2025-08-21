# 7taps Analytics - Data Access Guide

## 🚀 Quick Start

### API Base URL
```
https://seventaps-analytics-5135b3a0701a.herokuapp.com/api
```

### Interactive API Documentation
```
https://seventaps-analytics-5135b3a0701a.herokuapp.com/docs
```

## 📊 Data Access Methods

### 1. REST API (Recommended)
Use our secure API endpoints for querying data:

#### Get Connection Details
```bash
curl -X GET "https://seventaps-analytics-5135b3a0701a.herokuapp.com/api/data/connection-details"
```

#### Execute Queries
```bash
curl -X POST "https://seventaps-analytics-5135b3a0701a.herokuapp.com/api/data/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT COUNT(*) as total_statements FROM statements_new",
    "limit": 1000
  }'
```

#### Get Sample Queries
```bash
curl -X GET "https://seventaps-analytics-5135b3a0701a.herokuapp.com/api/data/sample-queries"
```

#### Get Data Status
```bash
curl -X GET "https://seventaps-analytics-5135b3a0701a.herokuapp.com/api/data/status"
```

### 2. Direct Database Connection

#### Connection Details
- **Host**: `ec2-54-83-137-254.compute-1.amazonaws.com`
- **Port**: `5432`
- **Database**: `d8vqj8qj8qj8qj8`
- **Username**: `your_username`
- **SSL Mode**: `require`

#### Connection String Format
```
postgresql://username:***@ec2-54-83-137-254.compute-1.amazonaws.com:5432/d8vqj8qj8qj8qj8?sslmode=require
```

#### Python Example
```python
import psycopg2

conn = psycopg2.connect(
    host="ec2-54-83-137-254.compute-1.amazonaws.com",
    port=5432,
    database="d8vqj8qj8qj8qj8",
    user="your_username",
    password="your_password",
    sslmode="require"
)

cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM statements_new")
result = cursor.fetchone()
print(f"Total statements: {result[0]}")
```

## 🗄️ Database Schema

### Main Tables

#### `statements_new`
Primary table containing all learning activity statements.

| Column | Type | Description |
|--------|------|-------------|
| `statement_id` | UUID | Unique statement identifier |
| `actor_id` | TEXT | Learner identifier |
| `activity_id` | TEXT | Learning activity identifier |
| `verb_id` | TEXT | Action performed (e.g., "answered", "completed") |
| `timestamp` | TIMESTAMP | When the activity occurred |
| `source` | TEXT | Data source ("xapi" or "csv") |
| `raw_json` | JSONB | Complete xAPI statement |

#### `context_extensions_new`
Metadata and context information for statements.

| Column | Type | Description |
|--------|------|-------------|
| `extension_id` | UUID | Unique extension identifier |
| `statement_id` | UUID | Reference to statement |
| `extension_key` | TEXT | Extension key (e.g., "https://7taps.com/lesson-number") |
| `extension_value` | TEXT | Extension value |

#### `results_new`
Results and outcomes from learning activities.

| Column | Type | Description |
|--------|------|-------------|
| `result_id` | UUID | Unique result identifier |
| `statement_id` | UUID | Reference to statement |
| `response` | TEXT | Learner's response |
| `success` | BOOLEAN | Whether activity was successful |
| `completion` | BOOLEAN | Whether activity was completed |

## 📈 Sample Queries

### Learner Engagement by Lesson
```sql
SELECT 
    ce.extension_value as lesson_number,
    COUNT(*) as total_activities,
    COUNT(DISTINCT s.actor_id) as unique_learners
FROM statements_new s
JOIN context_extensions_new ce ON s.statement_id = ce.statement_id
WHERE ce.extension_key = 'https://7taps.com/lesson-number'
GROUP BY ce.extension_value
ORDER BY lesson_number
```

### Card Type Engagement
```sql
SELECT 
    ce.extension_value as card_type,
    COUNT(*) as engagement_count
FROM statements_new s
JOIN context_extensions_new ce ON s.statement_id = ce.statement_id
WHERE ce.extension_key = 'https://7taps.com/card-type'
GROUP BY ce.extension_value
ORDER BY engagement_count DESC
```

### Learner Progression
```sql
SELECT 
    actor_id,
    COUNT(DISTINCT ce.extension_value) as lessons_completed,
    MAX(ce.extension_value::int) as furthest_lesson
FROM statements_new s
JOIN context_extensions_new ce ON s.statement_id = ce.statement_id
WHERE ce.extension_key = 'https://7taps.com/lesson-number'
GROUP BY actor_id
ORDER BY lessons_completed DESC
```

### Recent Activity
```sql
SELECT 
    DATE(timestamp) as activity_date,
    COUNT(*) as activities,
    COUNT(DISTINCT actor_id) as active_learners
FROM statements_new
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY DATE(timestamp)
ORDER BY activity_date DESC
```

## 🔑 Context Extension Keys

Common extension keys for filtering and analysis:

| Key | Description | Example Values |
|-----|-------------|----------------|
| `https://7taps.com/lesson-number` | Lesson number | "1", "2", "3", etc. |
| `https://7taps.com/card-type` | Type of learning card | "Poll", "Quiz", "Form", "Rate" |
| `https://7taps.com/global-q` | Global question number | "1", "2", "3", etc. |
| `https://7taps.com/pdf-page` | PDF page reference | "6", "12", "18", etc. |
| `https://7taps.com/source` | Data source | "focus_group_csv", "xapi" |

## 🛡️ Security & Limits

### API Security
- **Read-only access**: Only SELECT queries allowed
- **Query validation**: Dangerous operations blocked
- **Rate limiting**: 1000 rows max per query
- **SSL required**: All connections must use SSL

### Best Practices
1. **Use API endpoints** when possible (more secure)
2. **Limit result sets** to avoid performance issues
3. **Cache results** for repeated queries
4. **Use indexes** on frequently queried columns

## 📊 Current Data Status

- **Total Statements**: 633
- **Unique Learners**: 21
- **Data Sources**: xAPI (260), CSV (373)
- **Lessons Covered**: 1-10
- **Card Types**: Poll, Quiz, Form, Rate, Submit media

## 🔧 Troubleshooting

### Common Issues

#### Connection Refused
- Ensure SSL mode is set to "require"
- Check firewall settings
- Verify connection credentials

#### Query Timeout
- Add LIMIT clause to large queries
- Use more specific WHERE conditions
- Consider pagination for large datasets

#### Permission Denied
- Verify username and password
- Check database permissions
- Ensure SSL connection

### Support
For technical support or access credentials, contact the development team.

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [xAPI Specification](https://xapi.com/specification/)
- [Interactive API Docs](https://seventaps-analytics-5135b3a0701a.herokuapp.com/docs)
