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

## 🚀 Quick Start

### Deployment
The project uses automatic deployment via Cloud Build. Just commit and push:

```bash
./deploy.sh
```

See [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) for complete setup and configuration.

### Production URLs
* **Analytics Dashboard:** https://taps-analytics-ui-245712978112.us-central1.run.app
* **BigQuery Console:** https://console.cloud.google.com/bigquery?project=taps-data
* **Cloud Build:** https://console.cloud.google.com/cloud-build/builds?project=taps-data

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
