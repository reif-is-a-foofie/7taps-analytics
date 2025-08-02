# 7taps-analytics
Importing xAPI data from 7taps and doing magical stuff with it

## Development

This project uses [pre-commit](https://pre-commit.com/) to enforce formatting with [Black](https://black.readthedocs.io/en/stable/) and import sorting with [isort](https://pycqa.github.io/isort/).

Install the hook:

```
pip install pre-commit
pre-commit install
```

Run the configured checks on any files you modify before committing:

```
pre-commit run --files <changed files>
```

Alternatively, rely on the Git hook by simply running `git commit` after installing pre-commit.

A backend service for ingesting and reporting on 7taps xAPI statements. The system tracks user progress, stores raw and flattened statements, streams ETL results in real time through a Redis-backed broker, and sends reminder notifications for incomplete lessons. An embedded admin panel exposes debug endpoints, an open-source SQL UI, and a read-only database terminal for safe data exploration. Development is coordinated through JSON contracts stored in `orchestrator_contracts/`.

## Features
- Signup API for Squarespace Course Hub integration.
- Authenticated xAPI ingestion endpoint using PEM key based Basic Auth.
- Redis Streams decouple ingestion from a Dramatiq streaming worker that flattens statements in near real time.
- Incremental ETL job reconciles missed statements every few minutes.
- Dramatiq scheduler emails daily reminders with automatic retries and status logging.
- Reporting APIs for cohort completion and incompletion.
- Embedded admin UI with SQLPad or Superset plus JSON debug endpoints and a read-only DB terminal.
- Orchestrator contract system with progress and test-report endpoints for multi-agent coordination.

## Architecture
- **FastAPI** application exposing REST and debug endpoints.
- **PostgreSQL** for persistence.
- **Redis Streams** for ingestion queueing and **Dramatiq** workers for streaming ETL and scheduled jobs.
- Optional **Kafka** for higher scale streaming.
- **SQLPad** or **Apache Superset** embedded for read-only DB exploration.
- Optional **Learning Locker** for full xAPI storage.
- Deployment on **Railway** using Docker Compose.

High level flow:
```
Squarespace Course Hub -> Signup Form -> Users DB
7taps -> xAPI statements -> Redis Stream -> Streaming Worker -> Raw + Flat Tables
Incremental ETL (backup) -> Reporting + Reminder Jobs (Dramatiq)
Admin UI (SQLPad/Superset) -> Debug Endpoints + DB Terminal
```

## Development
The step-by-step development roadmap is defined in [plan.md](plan.md). Coding rules are enforced by [`.cursorrules`](.cursorrules), and module contracts live in [`orchestrator_contracts/`](orchestrator_contracts). Each module must be implemented in order and fully tested before moving on.

### Local Setup
Implementation is forthcoming; these steps will be updated as modules are completed.
1. Install Docker and Docker Compose.
2. Clone this repository.
3. Review the active module's contract in `orchestrator_contracts/`.
4. Follow instructions for the current module in `plan.md`.
5. Run `pytest` to execute tests; results surface at `/api/debug/test-report`.
6. Start the service with `docker compose up` after bootstrap modules are done.

## Contributing
- Do not create files or directories beyond those specified in `plan.md` and the required contract JSON files.
- Each module requires tests; run `pytest` before committing.
- Use conventional commit messages.
- Reference `AGENTS.md` for multi-agent workflow roles and responsibilities.

## License
MIT
