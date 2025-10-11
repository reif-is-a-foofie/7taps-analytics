# Data Management SOP

**Standard Operating Procedure for 7taps Analytics Platform**  
**Audience:** Data operators, system administrators, technical staff  
**Last Updated:** October 2025

---

## Purpose

This SOP defines how data flows through the 7taps Analytics platform, what to monitor, and how to handle common data management tasks.

---

## System Architecture Overview

```
7taps (learner activity)
  ↓
Cloud Function (ingestion endpoint)
  ↓
Pub/Sub (event streaming)
  ↓
Cloud Storage (raw backup) + BigQuery (structured analytics)
  ↓
FastAPI Dashboard (user-facing)
```

**Key principle:** Data flows automatically. Your job is to monitor health, handle exceptions, and ensure data quality.

---

## Daily Operations

### Morning Health Check (5 min)
**URL:** https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app/ui/dashboard

1. Check "System Health" status (should show green indicators)
2. Verify "Recent xAPI Statements" shows activity from the past 24h
3. Confirm "Total Users" count is reasonable (no sudden spikes/drops)

**Alert conditions:**
- ❌ No statements in 24h → Ingestion issue
- ❌ User count drops >20% → Data loss or query issue
- ⚠️ Statement errors in logs → Review error logs

---

### Weekly Data Quality Check (15 min)
**Frequency:** Every Monday morning

1. **Completeness Check**
   - Query BigQuery for lesson completions in the past 7 days
   - Compare to expected volume (based on cohort size × lessons per week)
   - Flag any days with <50% expected volume

2. **User Identity Check**
   - Scan `users` table for duplicate emails or malformed names
   - Run deduplication script if needed (contact dev)

3. **Flagged Content Review**
   - Check `/ui/flagged-content` for false positives
   - Update flagged word list as needed
   - Monitor AI detection status (Active = Gemini, Fallback = keyword only)

---

## Data Flow Monitoring

### Ingestion Endpoint
**URL:** https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app/statements  
**Method:** POST/PUT  
**Expected volume:** ~10-500 statements/day (depends on cohort size)

**How to monitor:**
1. Check Cloud Function logs in GCP Console → Cloud Functions → `xapi-ingestion`
2. Look for 2xx status codes (success) vs 4xx/5xx (errors)
3. Pub/Sub metrics: Messages published vs delivered

**Common issues:**
- **401 Unauthorized:** 7taps credentials misconfigured
- **500 Server Error:** Cloud Function crashed (check logs)
- **No traffic:** 7taps webhook not configured or paused

---

### Data Storage

#### BigQuery Tables
**Project:** `pol-chatbot`  
**Dataset:** `xapi_analytics`

| Table | Purpose | Retention |
|-------|---------|-----------|
| `users` | Learner profiles | Indefinite |
| `lessons` | Course content metadata | Indefinite |
| `questions` | Individual prompts | Indefinite |
| `user_responses` | Freeform text answers | Indefinite (PII) |
| `user_activities` | Completion events | Indefinite |

**Data retention policy:**
- Raw data in Cloud Storage: 90 days (configurable)
- BigQuery data: No automatic deletion (manual archive as needed)

---

#### Cloud Storage Backup
**Bucket:** `pol-chatbot-xapi-raw`  
**Format:** JSON files (one per xAPI statement)  
**Naming:** `YYYY-MM-DD/UUID.json`

**Purpose:** Disaster recovery and data replay. Do not delete unless >90 days old and you've confirmed BigQuery has the data.

---

## Data Quality Standards

### Acceptable Data
- ✅ User email is valid format (contains `@`)
- ✅ Lesson completion timestamp is within past 30 days
- ✅ User response text is <5000 characters
- ✅ All required xAPI fields present (`actor`, `verb`, `object`)

### Data to Flag for Review
- ⚠️ User email is malformed or generic (`test@example.com`)
- ⚠️ Response text contains only special characters or spam
- ⚠️ Duplicate completions within 1 minute (possible bot)
- ⚠️ Timestamp is in the future or >1 year old

### Data to Reject
- ❌ Missing required xAPI fields
- ❌ User email is missing or null
- ❌ Statement type is not recognized

**How to handle:**
- Review rejected statements in Cloud Function error logs
- Correct at source (7taps configuration) if systemic
- Manually insert corrected data if one-off issue

---

## Common Data Tasks

### Task 1: Export Full Dataset
**When:** End of cohort, annual reporting, external audit

**Steps:**
1. Open BigQuery Console → `pol-chatbot.xapi_analytics`
2. Run export query (see `docs/migrations/export_full_dataset.sql`)
3. Export to Cloud Storage as CSV
4. Download from Cloud Storage to local machine
5. Archive and share according to data governance policy

**Important:** Export contains PII. Follow your org's data handling protocols.

---

### Task 2: Backfill Missing Data
**When:** Cloud Function was down, Pub/Sub had issues, or data was lost

**Steps:**
1. Identify date range of missing data
2. Locate raw JSON files in Cloud Storage bucket (`pol-chatbot-xapi-raw`)
3. Re-publish to Pub/Sub using replay script:
   ```bash
   python scripts/replay_from_storage.py --start-date YYYY-MM-DD --end-date YYYY-MM-DD
   ```
4. Monitor BigQuery ingestion to confirm data appears
5. Validate completeness with count query

---

### Task 3: Add/Remove Flagged Words
**When:** False positives appear, or new safety concerns emerge

**Steps:**
1. Go to `/ui/flagged-content`
2. Scroll to "Manage Flagged Words"
3. Add word → Click "Add Word"
4. Remove word → Click red X next to word
5. Changes take effect immediately (no restart needed)

**Best practices:**
- Use lowercase only (system is case-insensitive)
- Avoid common words that cause false positives ("tired", "bad day")
- Add course-specific terms as needed

---

### Task 4: Investigate Missing Learner Data
**When:** Learner reports completion but data doesn't show

**Steps:**
1. Get learner's email and lesson name
2. Query BigQuery:
   ```sql
   SELECT * FROM `pol-chatbot.xapi_analytics.user_activities`
   WHERE user_email = 'learner@example.com'
   AND lesson_title LIKE '%Lesson Title%'
   ORDER BY completed_at DESC
   ```
3. If no results → Check Cloud Storage raw data for that date
4. If raw data exists but BigQuery doesn't → Re-run ETL for that statement
5. If raw data missing → 7taps didn't send it (check their logs)

---

## Troubleshooting

### Issue: No Data for Today
**Symptoms:** Dashboards show no activity, BigQuery queries return 0 rows

**Diagnosis:**
1. Check Cloud Function logs for errors
2. Check Pub/Sub subscription backlog (should be 0-10 messages)
3. Verify 7taps webhook is active

**Resolution:**
- If Cloud Function error → Check credentials, fix code, redeploy
- If Pub/Sub backlog >1000 → Increase subscription capacity or clear backlog
- If webhook inactive → Contact 7taps support

---

### Issue: Duplicate User Records
**Symptoms:** Same learner appears multiple times with different IDs

**Diagnosis:**
1. Query BigQuery `users` table:
   ```sql
   SELECT user_email, COUNT(*) as count
   FROM `pol-chatbot.xapi_analytics.users`
   GROUP BY user_email
   HAVING count > 1
   ```
2. Check if email case differs (`User@example.com` vs `user@example.com`)

**Resolution:**
- Run user normalization script:
  ```bash
  python scripts/normalize_users.py
  ```
- Merge duplicate records (preserve most recent metadata)

---

### Issue: Flagged Content Overflow
**Symptoms:** Too many false positives, flagged content list is unmanageable

**Diagnosis:**
1. Review most common flagged words
2. Identify patterns (e.g., "stressed" flags 200+ times)

**Resolution:**
- Remove overly broad words from flagged list
- Switch AI detection mode to "Contextual" (uses Gemini to understand nuance)
- Consult with safety team on acceptable thresholds

---

## Data Security & Privacy

### PII Handling
**What counts as PII:**
- User email
- User name
- Freeform response text (may contain identifying info)

**How we protect it:**
- Data at rest encrypted (GCP default)
- BigQuery access restricted to authorized users only
- Export files encrypted before sharing
- No PII in logs or error messages

### Compliance
- **GDPR:** User can request data deletion (contact dev to run deletion script)
- **FERPA (if applicable):** Student data treated as education records
- **Internal policy:** Follow your org's data retention and access policies

---

## Scheduled Maintenance

### Monthly Tasks
- Review BigQuery storage costs (archive old data if >$X threshold)
- Audit user access logs (who queried what)
- Update flagged word list based on feedback

### Quarterly Tasks
- Full data quality audit (completeness, accuracy, consistency)
- Review and update this SOP
- Test disaster recovery procedure (restore from Cloud Storage backup)

---

## Escalation Path

| Issue Severity | Response Time | Contact |
|----------------|---------------|---------|
| **Critical** (no data flowing) | <1 hour | System admin + dev team |
| **High** (partial data loss, incorrect results) | <4 hours | System admin |
| **Medium** (flagged content issues, slow queries) | <24 hours | Data operator |
| **Low** (cosmetic issues, feature requests) | <1 week | Product owner |

---

## Useful Resources

- **BigQuery Console:** https://console.cloud.google.com/bigquery?project=pol-chatbot
- **Cloud Functions:** https://console.cloud.google.com/functions?project=pol-chatbot
- **Pub/Sub:** https://console.cloud.google.com/cloudpubsub?project=pol-chatbot
- **Cloud Storage:** https://console.cloud.google.com/storage?project=pol-chatbot
- **Dashboard:** https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app
- **API Docs:** https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app/api/docs

---

## Appendix: Key Queries

### Check Daily Ingestion Volume
```sql
SELECT
  DATE(completed_at) as date,
  COUNT(*) as completions
FROM `pol-chatbot.xapi_analytics.user_activities`
WHERE completed_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY date
ORDER BY date DESC
```

### Find Duplicate Users
```sql
SELECT
  LOWER(user_email) as email,
  COUNT(DISTINCT user_id) as id_count
FROM `pol-chatbot.xapi_analytics.users`
GROUP BY email
HAVING id_count > 1
```

### Export Flagged Content
```sql
SELECT
  user_email,
  lesson_title,
  response_text,
  created_at
FROM `pol-chatbot.xapi_analytics.user_responses`
WHERE flagged = TRUE
ORDER BY created_at DESC
LIMIT 100
```

---

**Version:** 1.0  
**Next Review:** January 2026  
**Owner:** System Administrator

For technical implementation details, see `docs/DEPLOYMENT_GUIDE.md` and `docs/plan.md`.

