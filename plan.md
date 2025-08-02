# Plan

## Contract Creation
- Use `orchestrator_contracts/contract_schema.json` as the template for new contracts.
- Each contract must define `module`, `agent`, `allowed_files`, `required_endpoints`, and `status`.

# Development Plan

Implement the backend service in strictly ordered modules. Complete and test one module before proceeding to the next.

## a.01 Project Scaffold
**Files:**
- `requirements.txt`
- `Dockerfile`
- `docker-compose.yml`
- `app/__init__.py`
- `app/main.py`
- `app/database.py`
- `orchestrator_contracts/.gitkeep`
- `tests/__init__.py`
- `tests/test_health.py`

**Classes & Methods:**
- `create_app()` in `app/main.py` returning a FastAPI instance.
- `get_db()` in `app/database.py` providing a SQLAlchemy session.
- FastAPI route function `read_health()` returning `{ "status": "ok" }`.

**Steps:**
1. Write `requirements.txt` with FastAPI, Uvicorn, SQLAlchemy, Psycopg2, Pydantic, Alembic, Dramatiq, Redis, and pytest.
2. Create `Dockerfile` and `docker-compose.yml` defining services `fastapi-app`, `postgres-db`, and `redis`.
3. Implement `app/database.py` with SQLAlchemy engine and session maker.
4. Implement `app/main.py` with `create_app()` and `/health` endpoint.
5. Create empty `orchestrator_contracts` directory containing `.gitkeep` for module contracts.
6. Add basic test in `tests/test_health.py` asserting 200 response.

**Tests:**
- `pytest tests/test_health.py`
- `docker compose build`

## a.02 Data Models & Schemas
**Files:**
- `app/models.py`
- `app/schemas.py`
- `migrations/env.py`
- `migrations/versions/0001_init.py`
- `tests/test_models.py`

**Classes & Methods:**
- SQLAlchemy models: `User`, `Lesson`, `StatementRaw`, `StatementFlat`, `Notification`, `TaskStatus` in `app/models.py`.
- Pydantic schemas: `SignupRequest`, `UserRead`, `StatementIn`, `StatementFlatRead`, `TaskStatusRead` in `app/schemas.py`.

**Steps:**
1. Define models with columns exactly as in the PRD.
2. Create Pydantic schemas reflecting the models.
3. Configure Alembic in `migrations/env.py`.
4. Generate initial migration `0001_init.py` creating all tables.
5. Tests create an in-memory database and validate table existence.

**Tests:**
- `pytest tests/test_models.py`
- `alembic upgrade head`

## a.03 Signup API
**Files:**
- `app/api/__init__.py`
- `app/api/signup.py`
- `app/main.py` (update to include router)
- `tests/test_signup.py`

**Classes & Methods:**
- Pydantic schema `SignupRequest` (existing).
- Endpoint function `post_signup(signup: SignupRequest, db=Depends(get_db)) -> UserRead` in `app/api/signup.py`.

**Steps:**
1. Create `app/api` package with router in `signup.py`.
2. Implement POST `/api/signup` that inserts into `users` table.
3. Register router in `app/main.py` under `/api` prefix.
4. Tests: insert user and ensure returned data matches; duplicate avatar should raise 400.

**Tests:**
- `pytest tests/test_signup.py`

## a.04 xAPI Ingestion Endpoint (Queue Publisher)
**Files:**
- `app/api/xapi.py`
- `app/security.py`
- `app/streaming.py`
- `app/main.py` (update)
- `tests/test_xapi.py`

**Classes & Methods:**
- `verify_basic_credentials(credentials)` in `app/security.py` validating against PEM keys.
- `publish_statement(stream, statement_json)` in `app/streaming.py` appending to Redis Streams.
- Endpoint function `post_statement(statement: dict, credentials: HTTPBasicCredentials)` publishing to the stream.

**Steps:**
1. Implement Basic Auth that reads `PUBLIC_PEM` and `SECRET_PEM` from environment.
2. Implement `publish_statement` writing raw JSON to Redis Streams.
3. Endpoint accepts xAPI statement and publishes to stream; return `{ "queued": true }`.
4. Tests push a sample statement and assert it appears in the Redis stream.

**Tests:**
- `pytest tests/test_xapi.py`

## a.05 Streaming Worker ETL
**Files:**
- `app/etl_streaming.py`
- `tests/test_etl_streaming.py`

**Classes & Methods:**
- Dramatiq actor `process_statement(message_id, data)` consuming Redis Streams and writing to `statements_raw` and `statements_flat`.
- Helper `get_last_processed(db)` returning timestamp and count for debug endpoint.

**Steps:**
1. Implement Dramatiq worker consuming from Redis Streams.
2. Save raw JSON and flattened fields to the database.
3. Implement `get_last_processed` for later use in `/ui/test-etl-streaming`.
4. Tests simulate publishing a statement and ensure a flattened row exists within 2 seconds.

**Tests:**
- `pytest tests/test_etl_streaming.py`

## a.05b Incremental ETL Job (Backup)
**Files:**
- `app/etl_incremental.py`
- `tests/test_etl_incremental.py`

**Classes & Methods:**
- Function `flatten_statement(raw_json) -> dict` performing extraction.
- Function `run_incremental_etl(db)` processing only statements missing from `statements_flat`.

**Steps:**
1. Implement `flatten_statement` according to schema.
2. Implement `run_incremental_etl` selecting unprocessed rows and inserting flattened records.
3. Ensure job can run every 1–5 minutes without duplicating data.
4. Tests supply sample raw statements verifying missed rows are processed.

**Tests:**
- `pytest tests/test_etl_incremental.py`

## a.06 Daily Reminder Job & Scheduler
**Files:**
- `app/jobs/__init__.py`
- `app/jobs/reminder.py`
- `app/jobs/scheduler.py`
- `tests/test_reminder.py`

**Classes & Methods:**
- Function `get_incomplete_users(db, lesson_date) -> List[User]`.
- Dramatiq actor `send_daily_reminders()` sending emails and inserting into `notifications`.
- Dramatiq scheduler `schedule_daily_reminders()` running daily with auto-retry.
- Helper `log_task_status(db, name, status)` writing to `TaskStatus`.

**Steps:**
1. Implement helper to query users without completion for the day.
2. Implement reminder actor using injected `email_client` with retries.
3. Implement scheduler actor and status logging via `TaskStatus`.
4. Provide function returning preview data for `/ui/test-reminders`.
5. Tests mock `email_client` to assert emails sent, notifications logged, and status recorded.

**Tests:**
- `pytest tests/test_reminder.py`

## a.07 Reporting APIs
**Files:**
- `app/api/reporting.py`
- `app/main.py` (update)
- `tests/test_reporting.py`

**Classes & Methods:**
- Endpoint `get_cohort_completions(cohort_id)` returning list of completed users.
- Endpoint `get_lesson_incomplete(lesson_id)` returning list of users without completion.

**Steps:**
1. Create router with above endpoints.
2. Implement SQL queries joining tables as required.
3. Register router in `app/main.py` under `/api`.
4. Tests seed database and assert endpoints return expected JSON.

**Tests:**
- `pytest tests/test_reporting.py`

## a.07b Admin/UI DB Terminal & Debug Endpoints
**Files:**
- `app/ui/db_terminal.py`
- `app/api/debug.py`
- `tests/test_db_terminal.py`

**Classes & Methods:**
- `get_prebuilt_queries()` returning dict of names to SQL strings.
- `execute_safe_query(name: str, params: dict) -> JSON` executing whitelisted queries.
- FastAPI routes for:
  - `/ui/db-terminal`
  - `/api/debug/query`
  - `/api/debug/last-statement`
  - `/api/debug/recent-completions`
  - `/api/debug/raw-json/{id}`
  - `/api/debug/reminder-preview`
  - `/ui/test-etl-streaming`
  - `/ui/test-etl-incremental`
  - `/ui/test-reminders`
  - `/ui/admin/keys`

**Steps:**
1. Embed SQLPad or Superset in `/ui/db-terminal` for read-only queries.
2. Implement query safety allowing only prebuilt read-only queries.
3. Implement above FastAPI routes returning JSON.
4. Tests ensure prebuilt queries run, unsafe queries rejected, and endpoints return expected data structures.

**Tests:**
- `pytest tests/test_db_terminal.py`

## a.07c Orchestrator Contracts & Progress APIs
**Files:**
- `app/api/orchestrator.py`
- `orchestrator_contracts/sample.json`
- `tests/test_orchestrator.py`

**Classes & Methods:**
- Function `read_contracts() -> List[Contract]` loading JSON files.
- Function `update_contract_status(module: str, status: str)` writing to a contract file.
- FastAPI routes for:
  - `/api/debug/progress`
  - `/api/debug/active-agents`
  - `/api/debug/test-report`

**Steps:**
1. Define contract JSON schema `{module, agent, allowed_files, required_endpoints, status}`.
2. Implement helpers to read and update contracts.
3. Implement endpoints listed above.
4. Tests create a sample contract and verify endpoints report correct data.

**Tests:**
- `pytest tests/test_orchestrator.py`

## a.08 Deployment & Streaming Infra
**Files:**
- `Dockerfile` (update)
- `docker-compose.yml` (update with worker, scheduler, redis, sqlpad, optional kafka)
- `tests/test_docker.py`

**Classes & Methods:**
- None

**Steps:**
1. Update Docker artifacts for production deployment on Railway.
2. Include services: `fastapi-app`, `postgres-db`, `redis`, `worker`, `scheduler`, `sqlpad` (or `superset`), and optional `kafka` + `zookeeper`.
3. Add environment variable `ETL_MODE` to toggle streaming vs incremental ETL.
4. Tests build docker image and ensure required services exist.

**Tests:**
- `docker compose build`
- `pytest tests/test_docker.py`

---

**Testing Regimen Summary**
- Every module requires running `pytest` plus any commands listed under Tests.
- Orchestrator must create a contract JSON in `orchestrator_contracts/` before work begins on a module.
- No new files may be created beyond those explicitly listed in each module and the contract JSON files.
- Commit after tests pass for the current module.
- Each backend process must expose its corresponding UI or debug endpoint as specified above.
