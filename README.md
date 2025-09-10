# 7taps Analytics

**Turn raw xAPI firehoses into human-readable insights.**
This project is an experimental integration with [7taps](https://7taps.com), designed to show how learning data can be ingested, normalized, and explored across different levels of technical expertise.

Built with **Google Cloud Platform**, this repo demonstrates how to take 7taps lesson data → Cloud Functions → Pub/Sub → BigQuery → Analytics dashboards with AI-driven query generation.

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
   * **AI Agent (Seven):** ask natural language questions, generate SQL automatically, and visualize results

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
├── app/
│   ├── api/              # FastAPI endpoints for data access
│   ├── etl/              # Redis workers and ETL processes
│   ├── ui/               # Admin interfaces and dashboards
│   └── main.py           # Application entry point
├── workers/              # Dramatiq workers for background jobs
├── templates/            # HTML templates for web interfaces
├── scripts/              # Utility scripts and database tools
├── tests/                # Test suites and validation
├── orchestrator_contracts/ # JSON contracts for module development
├── config/               # Docker and deployment configuration
└── docs/                 # Documentation and guides
```

---

## 🚀 Quick Start

### Google Cloud Deployment
```bash
# Clone and setup
git clone <repository>
cd 7taps-analytics

# Deploy Cloud Function for xAPI ingestion
gcloud functions deploy cloud-ingest-xapi \
  --runtime python39 \
  --trigger-http \
  --allow-unauthenticated \
  --source . \
  --entry-point cloud_ingest_xapi

# Set up Pub/Sub topic and subscriptions
gcloud pubsub topics create xapi-ingestion-topic
gcloud pubsub subscriptions create xapi-storage-subscriber \
  --topic xapi-ingestion-topic
gcloud pubsub subscriptions create xapi-bigquery-subscriber \
  --topic xapi-ingestion-topic

# Create BigQuery dataset
bq mk taps_data
```

### Access Points
* **Cloud Function:** https://us-central1-taps-data.cloudfunctions.net/cloud-ingest-xapi
* **BigQuery Console:** https://console.cloud.google.com/bigquery
* **Cloud Storage:** https://console.cloud.google.com/storage
* **Pub/Sub Monitoring:** https://console.cloud.google.com/cloudpubsub

### Natural Language Queries
Try asking Seven (the AI agent) questions like:
* "Show engagement dropoff"
* "Find problematic users"
* "Energy levels over time"
* "Screen time patterns"
* "Learning priorities"
* "Reflection themes"

---

## 🧠 AI-Powered Analytics

The system includes **Seven**, an AI analytics assistant that can:
* **Understand natural language** - Ask "sleep" and get sleep-related insights
* **Generate SQL automatically** - Converts questions to database queries
* **Create visualizations** - Plotly charts for engagement, sentiment, and behavior
* **Provide contextual analysis** - Explains patterns and trends in the data

Seven has access to the complete database context and can answer questions about:
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
* **Development:** coordinated through JSON contracts in `orchestrator_contracts/`
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
