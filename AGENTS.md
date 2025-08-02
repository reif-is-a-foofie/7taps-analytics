# AGENTS.md

## Overview

This repository uses a **multi-agent development model** to safely accelerate build time by splitting work among specialized AI agents.

* **Orchestrator Agent** = Project Manager (PM)
* **Backend Agent** = APIs, ETL, streaming ingestion
* **Job Agent** = Scheduled tasks, reminders, cron
* **UI Agent** = Admin panel, DB terminal, JSON endpoints
* **Testing Agent** = Unit, integration, and regression tests

All agents **follow plan.md module sequence** and **must pass tests before committing**.
The orchestrator is **responsible for assigning modules, generating contracts, and ensuring safe parallel execution**.

---

## Agents & Responsibilities

### 1. Orchestrator Agent (Required)

* **Role:** Project Manager / Coordinator
* **Responsibilities:**
  1. Reads `plan.md` and `.cursorrules` to determine allowed modules
  2. Assigns modules to free agents
  3. Generates **agent contracts** for each module:
     * File paths allowed
     * Expected endpoints
     * Required JSON test outputs
  4. Runs `pytest` or test scripts after each module completion
  5. Approves merge to `main` when tests pass
* **File Ownership:** None (coordination only)
* **UI/JSON Endpoints:**
  * `/api/debug/progress` → Shows module assignment, test results
  * `/api/debug/active-agents` → List of current active modules/agents

---

### 2. Backend Agent

* **Owns:**
  * Streaming ETL (`app/etl_streaming.py`)
  * Incremental ETL (`app/etl_incremental.py`)
  * xAPI ingestion endpoints (`app/api/xapi.py`)
  * Database models & migrations (`app/models.py`)
* **Module Scope:** a.01 → a.05b
* **Deliverables:**
  * Functional ETL pipelines
  * `/ui/test-etl-streaming` and `/ui/test-etl-incremental` JSON endpoints
* **File Ownership:**
  ```
  app/api/xapi.py
  app/etl_*.py
  app/models.py
  app/schemas.py
  migrations/*
  ```
* **Testing:**
  * `tests/test_xapi.py`
  * `tests/test_etl_streaming.py`
  * `tests/test_etl_incremental.py`

---

### 3. Job Agent

* **Owns:**
  * Daily reminder job & notification system
  * Cron / Celery scheduling
* **Module Scope:** a.06
* **Deliverables:**
  * `/ui/test-reminders` JSON endpoint
  * Emails logged in `notifications` table
* **File Ownership:**
  ```
  app/jobs/*
  cronjob.sh
  ```
* **Testing:**
  * `tests/test_reminder.py`
  * Must simulate reminder job without sending live emails

---

### 4. UI Agent

* **Owns:**
  * Admin panel and JSON UI endpoints
  * Embedded DB terminal with endpoint library (`a.07b`)
  * `/ui/db-terminal` for safe query testing
* **Module Scope:** a.03, a.07, a.07b
* **Deliverables:**
  * HTML page or lightweight React panel for JSON output
  * Prebuilt query buttons (cohort status, completions, last N statements)
* **File Ownership:**
  ```
  app/ui/*
  app/templates/*
  app/static/*
  ```
* **Testing:**
  * `tests/test_ui.py`
  * `tests/test_db_terminal.py`

---

### 5. Testing Agent

* **Owns:**
  * All `tests/*` modules
* **Module Scope:** All modules
* **Deliverables:**
  * 100% passing `pytest` suite
  * JSON regression reports for orchestrator
* **File Ownership:**
  ```
  tests/*
  ```
* **Testing:**
  * Triggers after every agent push
  * Blocks merges if tests fail

---

## Multi-Agent Development Rules

1. **Immutable Plan:**
   * All modules and file ownership are defined in `plan.md`
   * No new files or directories without Orchestrator approval
2. **Sequential by Module, Parallel by Agent:**
   * Agents may work **in parallel** if their modules do not conflict
   * Orchestrator enforces dependency order
3. **JSON Endpoint Requirement:**
   * Every backend process must have a JSON endpoint or UI page for verification
   * Example: `/ui/test-etl-streaming` shows last processed statement
4. **Read-Only DB Terminal:**
   * `/ui/db-terminal` allows whitelisted queries only
   * No destructive operations (DROP/DELETE/UPDATE)
5. **CI/CD Flow:**
   * Orchestrator assigns → Agent implements → Testing Agent validates → Merge

---

## Orchestrator Flow

1. Reads `plan.md` → picks next eligible modules
2. Assigns module to an agent, creates **module contract**:
   ```
   Module: a.05 Streaming ETL
   Allowed files: app/etl_streaming.py, tests/test_etl_streaming.py
   Required endpoints: /ui/test-etl-streaming
   Test: pytest tests/test_etl_streaming.py
   ```
3. Waits for agent to commit changes
4. Triggers testing agent to validate
5. Approves merge if tests pass
6. Moves to next module(s) or triggers parallel work

---

## Acceptance Criteria for Multi-Agent Mode

* ✅ Agents work in parallel **without file conflicts**
* ✅ Orchestrator generates contracts for each assigned module
* ✅ Every module has **UI or JSON endpoints** for verification
* ✅ Testing Agent validates every module and blocks merges on failure
* ✅ CI/CD or orchestrator logs show **full module lifecycle**

