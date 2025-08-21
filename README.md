# 7taps Analytics

**Turn raw xAPI firehoses into human-readable insights.**
This project is an experimental integration with [7taps](https://7taps.com), designed to show how learning data can be ingested, normalized, and explored across different levels of technical expertise.

Built with a mix of SQL, Redis workers, and AI-driven query generation, this repo demonstrates how to take 7taps lesson data → split it into usable tables → and surface it through dashboards, APIs, and conversational agents.

---

## 🚀 What It Does

1. **Ingest xAPI statements**
   * Listens for raw xAPI `PUT` statements from 7taps
   * Stores them in PostgreSQL with JSONB handling
   * Uses Redis Streams for reliable ingestion queueing

2. **Normalize & Split**
   * Redis workers parse statements into structured tables:
     * `users` - learner profiles and metadata
     * `lessons` - course content and progression
     * `questions` - individual prompts and assessments
     * `user_responses` - freeform text and poll answers
     * `user_activities` - completion events and engagement
   * Cleans up lesson URLs, user identifiers, and metadata for readability

3. **Serve Analytics APIs**
   * Provides endpoints for common queries:
     * Who completed which lessons?
     * Which users are dropping off?
     * What themes show up in freeform responses?
     * Engagement patterns and sentiment analysis

4. **Explore the Data**
   Multiple "tiers" of access depending on technical comfort level:
   * **API-first:** raw curl requests to `/api/` endpoints
   * **SQL terminal:** run queries directly against PostgreSQL
   * **SQLPad:** preloaded queries for common use cases
   * **Data Explorer UI:** filter responses without writing SQL
   * **Dashboards:** Plotly visualizations with real-time data
   * **AI Agent (Seven):** ask natural language questions, generate SQL automatically, and visualize results

---

## 🛠️ Tech Stack

* **Backend:** Python, FastAPI, Redis workers, Dramatiq
* **Database:** PostgreSQL (with JSONB handling for xAPI)
* **Analytics:** SQLPad, Plotly, embedded admin UI
* **AI Layer:** OpenAI API (GPT-3.5), natural language query processing
* **Integration:** xAPI → PostgreSQL schema with real-time ETL
* **Deployment:** Railway with Docker Compose

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

### Local Development
```bash
# Clone and setup
git clone <repository>
cd 7taps-analytics
pip install -r requirements.txt

# Start the application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Access Points
* **Main Dashboard:** http://localhost:8000/
* **Chat Interface:** http://localhost:8000/chat
* **API Documentation:** http://localhost:8000/docs
* **Data Explorer:** http://localhost:8000/explorer

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
* **Authentication:** current API endpoints are unsecured for demo purposes
* **Data scope:** focused on 7taps course completion and user engagement data
* **Development:** coordinated through JSON contracts in `orchestrator_contracts/`

---

## 🌱 Future Directions

* Full MCP (Model Context Protocol) agent for PostgreSQL
* Multi-tenant, secure deployment
* Automated lesson metadata sync via 7taps API
* RAG (Retrieval-Augmented Generation) for true self-learning agents
* Cleaner developer onboarding and documentation

---

## 👤 Author

Built by [Reif Tauati](https://github.com/reif-is-a-foofie)
Exploring integrations, AI agents, and ways to make data actually useful.

---

## 📄 License

MIT
