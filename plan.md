# Migration Plan (Current)

The Heroku/PostgreSQL stack has been decommissioned. The codebase now runs
exclusively on Google Cloud:

- **Cloud Run** hosts the FastAPI service (`app/main.py`).
- **Cloud Functions + Pub/Sub** accept xAPI statements.
- **BigQuery** is the analytics store.
- **Redis** backs ingestion queues and caching.

Remaining work across contracts should focus on:

1. Hardening Cloud Run endpoints (gc10–gc12 complete).
2. Monitoring and documentation updates (gc13+).
3. Iterative UI polish targeting BigQuery data only.

Agents should select the next pending `gc` contract in numerical order,
checking `project_management/contracts/` for status. Heartbeats should
continue every 15 minutes when a contract is in progress.

Heroku, Railway, direct PostgreSQL access, ETL normalization, and
Learning Locker are no longer part of the plan and should not be
reintroduced.
