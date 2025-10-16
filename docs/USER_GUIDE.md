# 7taps Analytics — User Guide

**For:** Program coordinators, course facilitators, data operators, and system administrators  
**Last Updated:** October 2025  
**Questions?** Contact Reif Tauati at [reiftauati@gmail.com](mailto:reiftauati@gmail.com)

---

## What This Platform Does

This platform tracks your learners in two ways:

### 1. Automatic Data (happens on its own)
When someone finishes a lesson or answers a question in 7taps, that activity gets sent here automatically. You don't need to do anything.

**What you get automatically:**
- Lesson completions
- Text answers to questions
- When each activity happened
- Basic info (email, name)

**What's missing:**
- Age, location, group names
- Extra fields you added in 7taps
- Ratings or feedback scores
- Any custom information

### 2. CSV Files (you upload these)
To see everything, download a CSV file from 7taps and upload it here. The CSV has all the extra details the automatic system doesn't catch.

**The platform matches people by email.** If someone's email is in both the automatic data and your CSV, their information gets combined into one profile.

---

## How It Works

```
7taps Course
    ↓
    ├─ Automatic (runs 24/7) ──────────┐
    │  - Lesson completions             │
    │  - Question answers               │
    │                                    ↓
    └─ CSV Upload (you do this) ──→  Everything combines here
       - Extra details                     ↓
       - Custom info                  One complete view
```

Use both to get the full picture.

---

## Getting Started: First-Time Setup

### Step 1: Create Your User CSV
**Where:** Create a CSV file with your learner information

Your CSV needs these columns:
- `First Name`, `Last Name`, `Email` (required)
- `Group`, `Team` (for creating cohorts)

**Example CSV format:**
```csv
First Name,Last Name,Email,Group,Team
John,Doe,john@school.edu,Wellness,January
Jane,Smith,jane@school.edu,Wellness,February
Bob,Johnson,bob@school.edu,Business,January
```

**How cohorts are created:**
- **Group + Team** → **"Wellness January"** cohort
- **Group only** → **"Wellness X"** cohort  
- **Team only** → **"X January"** cohort
- **Neither** → **"X X"** cohort

**Tip:** Use clear group names like "Wellness", "Business", or "Spring 2025" to make filtering easy later.

---

### Step 2: Upload User CSV to Create Cohorts
**Where:** Open the platform → Click **📥 CSV Upload** in the left sidebar

1. Go to: https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app
2. Click **📥 CSV Upload** on the left side
3. Click "Select CSV File" and pick your user CSV file
4. (Optional) Add a note like "Spring 2025 cohorts"
5. Click "📤 Upload CSV"
6. Wait 5-30 seconds for it to finish

**What happens:**
- The system reads your CSV file
- It creates cohorts based on Group+Team combinations
- It adds all learners to their cohorts
- Now you can set up flagged words for each cohort

**When to upload:**
- **Before course starts:** Set up cohorts and safety monitoring
- **When adding new learners:** Update cohort assignments
- **Between terms:** Create new cohorts for new groups

---

### Step 3: Check That Cohorts Were Created
**Where:** Same page, scroll down to "Upload Status"

After uploading, look at this section to see:
- How many cohorts were created (from your Group+Team combinations)
- How many people were added to each cohort
- Any errors

**Example of what you'll see:**
- ✅ **"Wellness January"** cohort created (15 people)
- ✅ **"Business February"** cohort created (8 people)
- ✅ **"X X"** cohort created (3 people without group/team)

### Step 4: Set Up Flagged Words for Each Cohort
**Where:** Click **Flagged Content** in the sidebar

1. Pick a cohort from the dropdown (like "Wellness January")
2. Add flagged words specific to that group:
   - **Safety words:** "overwhelmed", "stressed", "hopeless"
   - **Positive words:** "grateful", "connected", "confident"
   - **Engagement words:** "bored", "confused", "excited"
3. Repeat for each cohort

**Why this matters:**
- A wellness course might flag "grateful" as positive
- A business course might flag "stressed" as concerning
- Each cohort gets monitoring tailored to their content

**Tip:** Set up flagged words before learners start the course. This way monitoring is ready from day one.

---

## Daily Workflow (5 minutes)

### Step 1: Check Daily Analytics
**Where:** Click **📊 Daily Course Analytics** on the left side

1. Click **📊 Daily Course Analytics** (opens to today's date)
2. **(Optional) Filter by group:**
   - Find the dropdown at the top
   - Pick a group (like "January 2025" or "Class A") to see just that group
   - Leave it blank to see everyone
3. **(Optional) Pick a different date:**
   - Click the date to see a different day
   - Good for checking past days or planning ahead
4. Look at who completed lessons:
   - ✅ Green = finished today's lesson
   - ⚠️ Yellow/blank = didn't finish (follow up with them)
5. Download the CSV to save the list
   - The file will only have the group/date you picked

**When to do this:**
- Every morning at 9am before reaching out to learners
- Before meeting with a specific group
- When making weekly reports

---

### Step 2: Check Flagged Content
**Where:** Look for Flagged Content (in the sidebar or main page)

1. Open "Recent Flagged Statements"
2. If you see anything, read the full answer to understand the context
3. Follow your safety plan (call a counselor, reach out to the learner, etc.)

**When to do this:**
- Once per day (morning or evening)
- After releasing big lessons
- Any time you get a safety alert

---

## Weekly Workflow (15 minutes)

### Monday: Check Completion Trends
Go to **📊 Daily Course Analytics** and look at the past 7 days:
- Use the date picker to go back day by day
- **Tip:** Pick a group to compare how different groups are doing
  - "Which group finishes the most lessons?"
  - "Is Group A dropping off more than Group B?"
- Are fewer people finishing lessons this week?
- Are the same people missing lessons over and over?
- Do you need to send a reminder email?

### Wednesday: Check Flagged Words
Go to **Flagged Content** and look at your word list:
- Are harmless words getting flagged? Remove them.
- Do you need to add new words specific to your course?

### Friday: Download Data for Reports
From **📊 Daily Course Analytics**, get the week's data:
1. Pick a group (if you manage more than one)
2. Pick the dates you need
3. Download the CSV for each day
4. Use the files to:
   - Share reports with your boss
   - Update your tracking spreadsheet
   - Find people who need 1-on-1 check-ins
   - Compare how groups are doing

---

## Common Questions

### "I don't see any data for today"
**Why this might happen:**
1. People haven't finished lessons yet (check what time it is)
2. 7taps connection is off (ask your admin)
3. The date is set wrong (make sure it says today)

**What to do:** Wait until later in the day, or check yesterday to make sure the system is working.

---

### "Someone says they finished a lesson but I don't see it"
**Why this might happen:**
1. They started but didn't finish (7taps only sends data when they're done)
2. It takes 5-10 minutes to show up
3. Their email doesn't match what you have

**What to do:** Wait 10 minutes and refresh. Still missing? Ask them to finish the lesson again.

---

### "Flagged content looks fine to me"
Sometimes the system flags normal stuff by mistake. If this happens:
1. Read the full answer to see the context
2. If it's harmless, remove that word from your list
3. The system gets better over time

**Example:** The word "exhausted" might get flagged, but if someone says "exhausted from running," that's fine. Remove "exhausted" from your list.

---

### "I need data from last month"
Use the date picker in **📊 Daily Course Analytics**:
1. Click the date at the top
2. Pick the date you want (like September 15, 2024)
3. The page will update with that day's info
4. Download the CSV to save it
5. Do this for each day you need, or pick a group to see just that group

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Dashboard won't load | Clear your browser history, try a private window, or ask your admin |
| CSV won't download | Right-click the download button → Pick "Save link as..." |
| Can't find someone | 1. Clear the group filter (pick "All") to see everyone<br>2. Check if they're in a different group<br>3. Open the CSV and search for their email |
| I'm seeing the same person twice | This is rare; ask your admin to check it |

---

## Getting Access

**Website:** https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app

**Pages you'll use most:**
- `/ui/dashboard` — Main page and system status
- `/ui/daily-analytics` — Daily lesson completions
- `/ui/flagged-content` — Safety monitoring

**Logging in:** Right now, most pages are open. Later, you'll log in with your Google account.

---

## Who to Ask for Help

| Problem | Who to Contact |
|------------|---------|
| Dashboard not working | Your system admin |
| Data looks wrong | Your system admin |
| Safety concern about a learner | Follow your safety plan (counselor, coach, etc.) |
| Want a new feature | Reif Tauati at [reiftauati@gmail.com](mailto:reiftauati@gmail.com) |

---

## Tips

✅ **Do this:**
- Check analytics at the same time every day (like 9am)
- **Use group filters** if you manage more than one group
- Download CSVs often for your records
- Check flagged content within 24 hours
- Use clear group names in 7taps so they're easy to find here

❌ **Don't do this:**
- Expect instant data (it takes 5-10 minutes to show up)
- Use this as your only safety tool (it helps, but you still need to use your judgment)
- Share CSV files outside your team (they have private information)

---

## How It Works (Background Info)

You don't need to know this to use the platform, but here's what happens:

1. Someone finishes a lesson in 7taps
2. 7taps sends that info to our system
3. The system saves it in a database
4. The dashboard shows you the results

This all happens automatically. You just check the dashboard.

---

## Words to Know

- **CSV:** A spreadsheet file you can open in Excel or Google Sheets
- **Flagged content:** Answers that have words you're watching for safety reasons
- **Group/Cohort:** A set of learners (like "January 2025 class" or "Group A")
- **Filter:** Show only specific people or dates (like picking just one group)

---

# For Technical Staff

The following sections are for system administrators and data operators who manage the platform.

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

## Daily Operations (Technical)

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
   - Run deduplication script if needed

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

### Task 3: Investigate Missing Learner Data
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

## Technical Troubleshooting

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
- Review and update this guide
- Test disaster recovery procedure (restore from Cloud Storage backup)

---

## Useful Resources

- **BigQuery Console:** https://console.cloud.google.com/bigquery?project=pol-chatbot
- **Cloud Functions:** https://console.cloud.google.com/functions?project=pol-chatbot
- **Pub/Sub:** https://console.cloud.google.com/cloudpubsub?project=pol-chatbot
- **Cloud Storage:** https://console.cloud.google.com/storage?project=pol-chatbot
- **Dashboard:** https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app
- **API Docs:** https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app/api/docs

---

## Appendix: Key SQL Queries

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

**For technical implementation details, see `docs/DEPLOYMENT_GUIDE.md` and `docs/plan.md`.**

