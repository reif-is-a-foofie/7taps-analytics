# 7taps Analytics

**Turn raw xAPI firehoses into human-readable insights.**
This project is an experimental integration with [7taps](https://7taps.com), designed to show how learning data can be ingested, normalized, and explored across different levels of technical expertise.

Built with **Google Cloud Platform**, this repo demonstrates how to take 7taps lesson data → Cloud Functions → Pub/Sub → BigQuery → Analytics dashboards with AI-driven query generation.

## 🤖 For AI Agents
**IMPORTANT**: This project uses frequent commits. See [`AGENT_REMINDER.md`](AGENT_REMINDER.md) for critical commit behavior guidelines. Use `./quick-commit.sh` or `git qc` after each logical change.

---

## 🚀 What It Does

1. **Ingest xAPI statements via Cloud Functions**
   * Receives raw xAPI `POST` statements from 7taps via Google Cloud Function
   * Publishes statements to Pub/Sub for reliable event streaming
   * Always-on architecture with zero cold start issues

2. **Archive Raw Data to Cloud Storage**
   * Pub/Sub subscriber archives raw JSON payloads to Cloud Storage
   * Provides permanent backup and replay capabilities
   * Decouples ingestion from downstream processing

3. **Transform & Load to BigQuery**
   * Pub/Sub subscriber transforms raw xAPI into structured BigQuery tables:
     * `users` - learner profiles and metadata
     * `lessons` - course content and progression
     * `questions` - individual prompts and assessments
     * `user_responses` - freeform text and poll answers
     * `user_activities` - completion events and engagement
   * Serverless ETL with automatic scaling

4. **Serve Analytics from BigQuery**
   * Provides endpoints for common queries against BigQuery:
     * Who completed which lessons?
     * Which users are dropping off?
     * What themes show up in freeform responses?
     * Engagement patterns and sentiment analysis

5. **Explore the Data**
   Multiple "tiers" of access depending on technical comfort level:
   * **API-first:** raw curl requests to `/api/` endpoints
   * **BigQuery Console:** run queries directly against structured data
   * **Data Explorer UI:** filter responses without writing SQL
   * **Analytics Dashboards:** BigQuery-powered visualizations
   * **AI Agent (September):** ask natural language questions, generate SQL automatically, and visualize results

---

## 🛠️ Tech Stack

* **Ingestion:** Google Cloud Functions (Python runtime)
* **Event Streaming:** Google Cloud Pub/Sub
* **Data Storage:** Google Cloud Storage (raw data archive)
* **Analytics Database:** Google BigQuery (structured data warehouse)
* **Backend:** Python, FastAPI for API endpoints
* **Analytics UI:** BigQuery-powered dashboards and visualizations
* **AI Layer:** OpenAI API (GPT-3.5), natural language query processing
* **Integration:** xAPI → Cloud Functions → Pub/Sub → BigQuery ETL
* **Deployment:** Google Cloud Platform (serverless)

---

## 🧩 Example Use Cases

* **Engagement Tracking**: "Which users completed lesson 5 on time?"
* **Content Insights**: "Show me all responses mentioning 'sleep'"
* **Cohort Analysis**: "What freeform answers are trending across my learners?"
* **Sentiment Monitoring**: flag problematic words or shifts in tone
* **Natural Language Queries**: "Which learners are most likely to churn?"
* **Dropoff Analysis**: "Where are users losing engagement in the course?"

---

## 📂 Repo Structure

```
7taps-analytics/
├── app/                   # Application code
│   ├── api/              # FastAPI endpoints for data access
│   ├── etl/              # Pub/Sub ETL processors
│   ├── ui/               # Admin interfaces and dashboards
│   └── main.py           # Application entry point
├── project_management/    # Contracts, reports, and project tracking
│   ├── contracts/        # Orchestrator contracts for all modules
│   └── progress_reports/ # Deployment and testing reports
├── workers/              # Dramatiq workers for background jobs
├── templates/            # HTML templates for web interfaces
├── scripts/              # Utility scripts and database tools
├── tests/                # Test suites and validation
├── config/               # Docker and deployment configuration
├── docs/                 # Documentation and guides
├── plan.md               # Development plan and deployment process
└── README.md             # This file
```

---

## 📊 User Guide - Analytics Platform

### Accessing the Platform
**Production URL:** https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app

### Available Dashboards

#### 1. Dashboard (Main)
**URL:** https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app/ui/dashboard

**What it shows:**
- System health and status
- Total users and activity metrics
- Recent xAPI statements
- Platform overview

**Use this for:** Quick health check and overall system monitoring

---

#### 2. Daily Analytics
**URL:** https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app/ui/daily-analytics

**What it shows:**
- Daily lesson completions by user
- Who completed lessons vs who needs follow-up
- Completion rates and progress tracking
- Downloadable CSV exports
- Filter by cohort/group

**Use this for:**
- Preparing daily progress emails
- Tracking lesson completion rates
- Identifying users who need follow-up
- Exporting data for reporting

**How to use:**
1. Select target date (defaults to today)
2. Optional: Filter by cohort/group name
3. View completion status for each user
4. Download CSV for email workflow

---

#### 3. Flagged Content
**URL:** https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app/ui/flagged-content

**What it shows:**
- AI-detected concerning content in user responses
- Flagged words management (add/remove custom words)
- Detection rates and safety metrics
- Recent flagged statements with context

**Use this for:**
- Monitoring learner safety and well-being
- Managing custom flagged words for your context
- Reviewing content that needs attention
- Safety compliance and reporting

**How to use:**
1. Review flagged content section for recent alerts
2. Add custom flagged words specific to your course
3. Monitor AI analysis status (Active = Gemini AI, Fallback = keyword matching)
4. Click on flagged content to see full context

---

### API Access
**Documentation:** https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app/api/docs

Key endpoints:
- `/api/daily-progress/data?date=YYYY-MM-DD&group=GROUP_NAME` - Daily progress data
- `/api/daily-analytics/cohorts` - Available cohorts/groups
- `/ui/api/daily-analytics/csv?date=YYYY-MM-DD` - Download daily CSV
- `/api/health` - System health check

---

### xAPI Integration (7taps)
**Ingestion URL:** https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app/statements
**Methods:** POST, PUT
**Auth:** Basic Authentication (credentials provided separately)
**Format:** xAPI v1.0.3 compliant JSON

7taps automatically sends lesson completion events to this endpoint.

---

## 🚀 For Developers

### Deployment
```bash
./deploy.sh
```

See [`docs/DEPLOYMENT_GUIDE.md`](docs/DEPLOYMENT_GUIDE.md) for complete setup and configuration.

### Natural Language Queries
Try asking September (the AI agent) questions like:
* "Show engagement dropoff"
* "Find problematic users"
* "Energy levels over time"
* "Screen time patterns"
* "Learning priorities"
* "Reflection themes"

---

## 🧠 AI-Powered Analytics

The system includes **September**, an AI analytics assistant that can:
* **Understand natural language** - Ask "sleep" and get sleep-related insights
* **Generate SQL automatically** - Converts questions to database queries
* **Create visualizations** - Plotly charts for engagement, sentiment, and behavior
* **Provide contextual analysis** - Explains patterns and trends in the data

September has access to the complete database context and can answer questions about:
* User engagement patterns
* Content effectiveness
* Behavioral insights
* Sentiment analysis
* Learning priorities

---

## ⚠️ Notes

* **Experimental project** - This repo is exploratory and designed for learning/demo purposes
* **Authentication:** Cloud Function endpoints are configured for demo purposes
* **Data scope:** focused on 7taps course completion and user engagement data
* **Development:** coordinated through JSON contracts in `project_management/contracts/`
* **Security:** GCP service account key located at `google-cloud-key.json` (never commit to version control)

---

## 🌱 Future Directions

* Enhanced BigQuery ML models for predictive analytics
* Multi-tenant, secure deployment with Cloud IAM
* Automated lesson metadata sync via 7taps API
* RAG (Retrieval-Augmented Generation) for true self-learning agents
* Real-time streaming analytics with Dataflow
* Auto-scaling Cloud Functions based on ingestion volume

---

## 👤 Author

Built by [Reif Tauati](https://github.com/reif-is-a-foofie)
Exploring integrations, AI agents, and ways to make data actually useful.

---

## 📄 License

MIT
