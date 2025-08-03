# Plan (v3 MCP-Optimized)

## Overview

This plan replaces the previous roadmap with an MCP-first architecture. Model
Context Protocol (MCP) servers handle database access, Python execution,
analytics dashboards, and optional browser automation, minimizing custom code.

### Module Replacement Map

| Previous Module | v3 Approach | Notes |
| --- | --- | --- |
| a.02 Data Models & Schemas | Use `bytebase/dbhub` or `supabase-mcp-server` for schema inspection and read-only queries. | Remove local SQLAlchemy models and migrations. |
| a.03 Signup API | Leverage existing 7taps auth; custom signup module removed. | |
| a.04 xAPI Ingestion Endpoint | FastAPI proxies statements to Redis/Kafka; ETL handled by `pydantic-ai/mcp-run-python`. | |
| a.05 Streaming Worker ETL | Replace Dramatiq worker with MCP Python script consuming Redis Streams. | |
| a.06 Daily Reminder Job & Scheduler | Replace custom job with MCP Python + SMTP MCP server. | |
| a.07 Reporting APIs | Use SQLPad or Superset via MCP DB server for analytics. | |
| a.07b Admin/UI DB Terminal | Provide read-only DB terminal via SQLPad/Superset embed. | |
| a.07c Orchestrator Contracts & Progress APIs | Module remains, extended to track MCP server usage. | |
| a.08 Deployment & Streaming Infra | Docker Compose now includes MCP servers; remove custom worker images. | |

## v3 Development Plan

Implement modules in order, ensuring each exposes test endpoints and is covered
by orchestrator contracts.

### b.01 Attach MCP Servers

**Files**
- `docker-compose.yml`
- `orchestrator_contracts/b01_attach_mcp_servers.json`

**Steps**
1. Add services for Postgres DB MCP, `pydantic-ai/mcp-run-python`, and
   SQLPad/Superset.
2. Create contract `b01_attach_mcp_servers.json` specifying allowed files and
   `/health` endpoint.
3. Verify each MCP server responds to `/health` or equivalent.

**Tests**
- `docker compose build`
- `pytest` (placeholder until code exists)

### b.02 Streaming ETL via MCP Python

**Files**
- `app/etl_streaming.py`
- `tests/test_etl_streaming.py`
- `orchestrator_contracts/b02_streaming_etl.json`

**Steps**
1. Implement ETL script invoked through MCP Python, consuming Redis Streams and
   writing to Postgres via MCP DB.
2. Add `/ui/test-etl-streaming` JSON endpoint for last processed statement.
3. Record contract in `b02_streaming_etl.json`.

**Tests**
- `pytest tests/test_etl_streaming.py`

### b.03 Incremental ETL Job Agent

**Files**
- `app/etl_incremental.py`
- `tests/test_etl_incremental.py`
- `orchestrator_contracts/b03_incremental_etl.json`

**Steps**
1. Use MCP Python for periodic catch-up ETL.
2. Expose `/ui/test-etl-incremental` endpoint.
3. Contract `b03_incremental_etl.json` defines allowed files.

**Tests**
- `pytest tests/test_etl_incremental.py`

### b.04 Orchestrator MCP Integration

**Files**
- `app/api/orchestrator.py`
- `orchestrator_contracts/contract_schema.json`
- `tests/test_orchestrator.py`

**Steps**
1. Extend orchestrator APIs to log active MCP calls and test results.
2. Provide `/api/debug/progress`, `/api/debug/test-report`, and
   `/api/debug/active-agents`.

**Tests**
- `pytest tests/test_orchestrator.py`

### b.05 NLP Query Agent

**Files**
- `app/api/nlp.py`
- `tests/test_nlp.py`
- `orchestrator_contracts/b05_nlp_query.json`

**Steps**
1. Use LangChain or LlamaIndex with MCP DB to translate natural language into
   SQL.
2. Implement `/ui/nlp-query` endpoint.

**Tests**
- `pytest tests/test_nlp.py`

### b.06 SQLPad/Superset UI Integration

**Files**
- `app/ui/admin.py`
- `tests/test_ui.py`
- `orchestrator_contracts/b06_ui.json`

**Steps**
1. Embed SQLPad or Superset for read-only DB terminal at `/ui/db-terminal`.
2. Add prebuilt query endpoints as required.

**Tests**
- `pytest tests/test_ui.py`

---

### Contract Creation

Use `orchestrator_contracts/contract_schema.json` for all new module contracts.
Each contract must define `module`, `agent`, `allowed_files`, `required_endpoints`,
and `status`.

### Testing Requirement

Run `pytest` after any changes to confirm the repository is consistent, even if
no tests are defined yet.

