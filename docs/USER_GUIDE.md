# 7taps Analytics — User Guide

**For:** Program coordinators, course facilitators, non-technical staff  
**Last Updated:** October 2025

---

## What This Platform Does

This platform automatically tracks learner progress in your 7taps course. Every time someone completes a lesson, answers a question, or engages with content, that data flows into the system. You can then:

- See who completed lessons today
- Export daily progress reports for follow-ups
- Monitor flagged content for learner safety
- Track engagement patterns over time

**You don't need to do anything for data to arrive.** It happens automatically when learners use 7taps.

---

## Daily Workflow (5 minutes)

### Step 1: Check Daily Analytics
**URL:** https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app/ui/daily-analytics

1. Open the page (it defaults to today's date)
2. Scan the completion list:
   - ✅ Green = completed today's lesson
   - ⚠️ Yellow/blank = needs follow-up
3. Download the CSV if you're sending follow-up emails

**When to use:**
- Every morning at 9am to prep outreach
- Before cohort check-ins
- When preparing weekly reports

---

### Step 2: Review Flagged Content (if applicable)
**URL:** https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app/ui/flagged-content

1. Check the "Recent Flagged Statements" section
2. If anything appears, read the full context
3. Follow your protocol for learner safety (contact counselor, reach out directly, etc.)

**When to use:**
- Once per day (morning or end of day)
- After major lesson releases
- Anytime you receive a safety alert

---

## Weekly Workflow (15 minutes)

### Monday: Review Completion Trends
Go to **Daily Analytics** and check the past 7 days:
- Are completion rates dropping?
- Are specific users consistently missing lessons?
- Do you need to send a re-engagement email?

### Wednesday: Spot Check Flagged Words
Go to **Flagged Content** and review your custom word list:
- Are you seeing false positives? Remove those words.
- Do you need to add course-specific terms?

### Friday: Export Data for Reporting
From **Daily Analytics**, export the week's CSV and:
- Share with leadership
- Update your tracking spreadsheet
- Identify learners for 1-on-1 check-ins

---

## Common Questions

### "I don't see any data for today"
**Possible causes:**
1. Learners haven't completed lessons yet (check time of day)
2. 7taps integration is paused (contact admin)
3. The date filter is set incorrectly (reset to today)

**What to do:** Wait until afternoon, or check yesterday's data to confirm the system is working.

---

### "A learner says they completed a lesson but it's not showing"
**Possible causes:**
1. They started but didn't finish (7taps only sends data on completion)
2. There's a 5-10 minute delay in data processing
3. Their email/username doesn't match your roster

**What to do:** Wait 10 minutes and refresh. If still missing, ask them to complete the lesson again or contact support.

---

### "Flagged content seems wrong"
The AI sometimes flags things that aren't actually concerning (false positives). If you see this:
1. Review the full context
2. If it's harmless, remove that word from the flagged word list
3. The system will learn over time

**Example:** The word "exhausted" might be flagged, but if learners use it casually ("exhausted from running"), you can remove it.

---

### "I need data from last month"
Use the date picker in **Daily Analytics** to go back in time. You can export any date range as a CSV.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Dashboard won't load | Clear browser cache, try incognito mode, or contact admin |
| CSV download fails | Right-click the download button → "Save link as..." |
| Can't find a specific user | Check the group/cohort filter — they might be in a different cohort |
| Data looks duplicated | This is rare; contact admin to check for ingestion issues |

---

## Access & Permissions

**Production URL:** https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app

**Dashboards you'll use most:**
- `/ui/dashboard` — Overview and system status
- `/ui/daily-analytics` — Daily lesson completions
- `/ui/flagged-content` — Safety monitoring

**Authentication:** Most dashboards are open for demo purposes. In production, you'll log in with Google SSO.

---

## Who to Contact

| Issue Type | Contact |
|------------|---------|
| Dashboard not loading | System admin |
| Data looks wrong | System admin |
| Learner safety concern | Your org's protocol (counselor, coach, etc.) |
| Feature requests | Product owner |

---

## Tips for Success

✅ **Do:**
- Check daily analytics at a consistent time (e.g., 9am)
- Export CSVs regularly for backup/reporting
- Review flagged content within 24 hours
- Filter by cohort if you manage multiple groups

❌ **Don't:**
- Assume real-time data (expect 5-10 min delay)
- Rely solely on this platform for safety (it's a tool, not a replacement for human judgment)
- Share raw CSV files outside your org (contains PII)

---

## What Happens Behind the Scenes (FYI)

You don't need to know this to use the platform, but for context:

1. Learner completes a lesson in 7taps
2. 7taps sends the completion event to our Cloud Function
3. The system processes and stores it in BigQuery (Google's data warehouse)
4. Dashboards query BigQuery to show you the results

This happens automatically, 24/7. You just use the dashboards.

---

## Glossary

- **xAPI:** A data standard for learning events (you'll never interact with this directly)
- **BigQuery:** Google's database where all the data lives
- **CSV:** Spreadsheet file you can open in Excel/Google Sheets
- **Flagged content:** User responses that contain concerning words or phrases
- **Cohort/Group:** A subset of learners (e.g., "January 2025 cohort")

---

**Questions?** Contact your system administrator or see `docs/DATA_MANAGEMENT_SOP.md` for technical details.

