# 🗄️ 7taps Analytics Database Overview

## 📊 **Database Status**
- **Host**: Heroku PostgreSQL (AWS RDS)
- **Connection**: `postgres://u19o5qm786p1d1:...@c5cnr847jq0fj3.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d7s5ke2hmuqipn`
- **Tables**: 16 tables (including legacy and views)
- **Status**: ✅ **ACTIVE** with real data

---

## 📋 **Core Tables**

### **1. Users & Authentication**
```sql
-- users table
SELECT * FROM users LIMIT 5;
```
**Schema:**
- `id` (integer, PK)
- `user_id` (varchar) - email/identifier
- `cohort` (varchar) - user grouping
- `first_seen` (timestamp)
- `last_seen` (timestamp)
- `created_at` (timestamp)

### **2. Lessons & Content**
```sql
-- lessons table
SELECT * FROM lessons ORDER BY lesson_number;
```
**Schema:**
- `id` (integer, PK)
- `lesson_url` (varchar) - course URL
- `lesson_number` (integer) - sequence
- `lesson_name` (varchar) - display name
- `created_at` (timestamp)

**Sample Data:**
- Lesson 1: "You're Here. Start Strong"
- Lesson 2: "Where is Your Attention Going?"
- Lesson 3: "Own Your Mindset"

### **3. Questions & Assessments**
```sql
-- questions table
SELECT * FROM questions WHERE lesson_id = 1;
```
**Schema:**
- `id` (integer, PK)
- `lesson_id` (integer, FK)
- `question_number` (integer)
- `question_text` (text)
- `question_type` (varchar) - 'multiple_choice', 'form', etc.
- `created_at` (timestamp)

### **4. User Activities (xAPI Events)**
```sql
-- user_activities table
SELECT activity_type, COUNT(*) FROM user_activities GROUP BY activity_type;
```
**Schema:**
- `id` (integer, PK)
- `user_id` (integer, FK)
- `lesson_id` (integer, FK)
- `question_id` (integer, FK)
- `activity_type` (varchar) - xAPI verb
- `activity_data` (jsonb) - rich event data
- `timestamp` (timestamp)
- `source` (varchar) - 'xapi', 'csv', etc.
- `raw_statement_id` (varchar)
- `created_at` (timestamp)

### **5. User Responses**
```sql
-- user_responses table
SELECT response_text, COUNT(*) FROM user_responses GROUP BY response_text ORDER BY COUNT(*) DESC LIMIT 10;
```
**Schema:**
- `id` (integer, PK)
- `user_id` (integer, FK)
- `question_id` (integer, FK)
- `response_text` (text) - actual response
- `response_value` (text) - processed value
- `is_correct` (boolean)
- `score_raw` (numeric)
- `score_scaled` (numeric)
- `duration_seconds` (integer)
- `timestamp` (timestamp)
- `source` (varchar)
- `raw_statement_id` (varchar)
- `created_at` (timestamp)
- `lesson_number` (integer)

---

## 🔍 **Sample Analytics Queries**

### **User Engagement Analytics**

#### **1. Total Users & Activity**
```sql
-- Total registered users
SELECT COUNT(DISTINCT id) as total_users FROM users;

-- Most active users
SELECT 
    u.user_id,
    COUNT(ua.id) as activity_count,
    COUNT(DISTINCT ua.lesson_id) as lessons_accessed,
    MIN(ua.timestamp) as first_activity,
    MAX(ua.timestamp) as last_activity
FROM users u
LEFT JOIN user_activities ua ON u.id = ua.user_id
GROUP BY u.id, u.user_id
ORDER BY activity_count DESC
LIMIT 10;
```

#### **2. Lesson Completion Rates**
```sql
-- Completion rates by lesson
SELECT 
    l.lesson_name,
    l.lesson_number,
    COUNT(DISTINCT ua.user_id) as users_started,
    COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END) as users_completed,
    ROUND(
        (COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END)::float / 
         NULLIF(COUNT(DISTINCT ua.user_id), 0) * 100), 2
    ) as completion_rate
FROM lessons l
LEFT JOIN user_activities ua ON l.id = ua.lesson_id
GROUP BY l.id, l.lesson_name, l.lesson_number
ORDER BY l.lesson_number;
```

#### **3. Activity Timeline**
```sql
-- Daily activity for last 30 days
SELECT 
    DATE(ua.timestamp) as activity_date,
    COUNT(*) as activity_count,
    COUNT(DISTINCT ua.user_id) as unique_users
FROM user_activities ua
WHERE ua.timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(ua.timestamp)
ORDER BY activity_date;
```

### **Response Analytics**

#### **4. Question Response Analysis**
```sql
-- Most answered questions
SELECT 
    q.question_text,
    q.question_type,
    COUNT(ur.id) as response_count,
    AVG(ur.score_scaled) as avg_score
FROM questions q
LEFT JOIN user_responses ur ON q.id = ur.question_id
GROUP BY q.id, q.question_text, q.question_type
ORDER BY response_count DESC
LIMIT 10;
```

#### **5. Response Patterns**
```sql
-- Common response patterns
SELECT 
    response_text,
    COUNT(*) as frequency,
    COUNT(DISTINCT user_id) as unique_users
FROM user_responses 
WHERE response_text IS NOT NULL
GROUP BY response_text
ORDER BY frequency DESC
LIMIT 15;
```

### **Cohort Analysis**

#### **6. Cohort Performance**
```sql
-- Performance by cohort
SELECT 
    u.cohort,
    COUNT(DISTINCT u.id) as cohort_size,
    COUNT(ua.id) as total_activities,
    COUNT(DISTINCT ua.lesson_id) as lessons_accessed,
    AVG(ur.score_scaled) as avg_score
FROM users u
LEFT JOIN user_activities ua ON u.id = ua.user_id
LEFT JOIN user_responses ur ON u.id = ur.user_id
WHERE u.cohort IS NOT NULL
GROUP BY u.cohort
ORDER BY cohort_size DESC;
```

---

## 📈 **Advanced Analytics Queries**

### **Learning Path Analysis**
```sql
-- User learning progression
WITH user_progress AS (
    SELECT 
        ua.user_id,
        l.lesson_number,
        l.lesson_name,
        MIN(ua.timestamp) as first_access,
        MAX(ua.timestamp) as last_access,
        COUNT(*) as activity_count
    FROM user_activities ua
    JOIN lessons l ON ua.lesson_id = l.id
    GROUP BY ua.user_id, l.lesson_number, l.lesson_name
)
SELECT 
    lesson_number,
    lesson_name,
    COUNT(DISTINCT user_id) as users_reached,
    AVG(activity_count) as avg_activities,
    AVG(EXTRACT(EPOCH FROM (last_access - first_access))/3600) as avg_hours_spent
FROM user_progress
GROUP BY lesson_number, lesson_name
ORDER BY lesson_number;
```

### **Engagement Scoring**
```sql
-- User engagement score
SELECT 
    u.user_id,
    COUNT(ua.id) as total_activities,
    COUNT(DISTINCT ua.lesson_id) as lessons_accessed,
    COUNT(ur.id) as total_responses,
    AVG(ur.score_scaled) as avg_score,
    CASE 
        WHEN COUNT(ua.id) > 50 THEN 'High'
        WHEN COUNT(ua.id) > 20 THEN 'Medium'
        ELSE 'Low'
    END as engagement_level
FROM users u
LEFT JOIN user_activities ua ON u.id = ua.user_id
LEFT JOIN user_responses ur ON u.id = ur.user_id
GROUP BY u.id, u.user_id
ORDER BY total_activities DESC;
```

---

## 🎯 **Quick Access Queries**

### **Dashboard Metrics**
```sql
-- Key metrics for dashboard
SELECT 
    (SELECT COUNT(DISTINCT id) FROM users) as total_users,
    (SELECT COUNT(*) FROM user_activities) as total_activities,
    (SELECT COUNT(*) FROM user_responses) as total_responses,
    (SELECT COUNT(DISTINCT lesson_id) FROM user_activities) as active_lessons,
    (SELECT AVG(score_scaled) FROM user_responses WHERE score_scaled IS NOT NULL) as avg_score;
```

### **Recent Activity**
```sql
-- Recent user activity
SELECT 
    u.user_id,
    ua.activity_type,
    l.lesson_name,
    ua.timestamp
FROM user_activities ua
JOIN users u ON ua.user_id = u.id
LEFT JOIN lessons l ON ua.lesson_id = l.id
ORDER BY ua.timestamp DESC
LIMIT 20;
```

---

## 🔧 **Database Access**

### **SQLPad Access**
- **URL**: http://localhost:3000 (when running locally)
- **Credentials**: admin@7taps.com / admin123
- **Pre-configured**: PostgreSQL connection to Heroku database

### **API Endpoints**
- **Health Check**: http://localhost:8000/health
- **Analytics API**: http://localhost:8000/api/analytics/
- **Data Explorer**: http://localhost:8000/explorer
- **API Docs**: http://localhost:8000/docs

### **Direct Database Access**
```bash
# Connect via psql (if you have access)
psql "postgres://u19o5qm786p1d1:...@c5cnr847jq0fj3.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d7s5ke2hmuqipn"
```

---

## 📊 **Data Volume Summary**
- **Users**: Multiple active users with engagement data
- **Lessons**: 3+ lessons with structured content
- **Activities**: Rich xAPI event data from multiple sources
- **Responses**: User interaction data with scores and timestamps
- **Legacy Data**: Historical xAPI statements in normalized format

---

## 🚀 **Next Steps**
1. **Explore Data**: Use SQLPad to run sample queries
2. **Build Dashboards**: Create visualizations from query results
3. **Analyze Patterns**: Identify learning trends and user behavior
4. **Optimize Queries**: Add indexes for frequently used queries
5. **Data Pipeline**: Set up automated analytics reporting

---

*Last Updated: 2025-08-21*
*Database: Heroku PostgreSQL (Production)*
