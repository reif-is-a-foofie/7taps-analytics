# AGENTS.md

## Purpose
- Prime coding agents with how 7taps Analytics is structured so they act proactively instead of reactively.
- Reinforce the existing multi-agent workflow (see `.cursorrules` and `docs/AGENTS.md`) while giving high-level guardrails for any agent that loads this file first.

## Architecture at a Glance
- Data path: **7taps → Cloud Function (`app/api/cloud_function_ingestion.py`) → Pub/Sub → Cloud Storage archive → BigQuery**.
- Cloud Run hosts the FastAPI app (`app/main.py`), exposing API, monitoring, and UI surfaces.
- Redis has been retired; all caching/queues now run through BigQuery + Pub/Sub. Do not reintroduce Redis dependencies.
- Dramatiq workers live in `workers/` (see `Procfile`) but only run when a queue-backed contract requires them.
- Configuration uses Pydantic Settings (`app/config.py` + `app/config/gcp_config.py`); never hardcode secrets.

## Directory Compass
- `app/api/` – FastAPI routers (ingestion, analytics, monitoring, security, CSV tools).
- `app/etl/` – Pub/Sub processors + BigQuery loaders.
- `app/ui/` & `templates/` – operator dashboards, DB terminal, debug pages.
- `tests/` – pytest suites (unit + integration); `test_*.py` in repo root are smoke/regression helpers triggered by CI or manual runs.
- `docs/` – deployment, security, and legacy references; includes extended agent playbooks.
- `project_management/` – orchestration contracts, progress reports, and module tracking (`plan.md`).
- `agents/` – role-specific `.mdc` files; individual agents must load their contract in addition to this file.

## Runtime Environments
- **Local:** Python ≥3.11. Create a venv, `pip install -r requirements.txt`, copy `.env.example` to `.env`. No Redis bootstrap is required post-migration.
- **Cloud Run:** Container built via `Dockerfile` and deployed with `cloudbuild.yaml`. Environment variables set at deploy time (`DEPLOYMENT_MODE=cloud_run`, `GOOGLE_CLOUD_PROJECT`, BigQuery dataset, etc.).
- **Cloud Functions:** `app/api/cloud_function_ingestion.py` deployed separately for raw webhook ingestion; requires matching Pub/Sub topic and service account permissions.

## Build, Run & Deploy
- Local app: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` (make sure required GCP env vars are set).
- Local worker (when needed): `dramatiq --processes 1 workers.worker`. Confirm worker contracts target Pub/Sub/BigQuery flows; no Redis setup is necessary.
- Full pytest sweep: `pytest` (set `PYTHONPATH=$PYTHONPATH:.` if running outside repo root).
- Targeted suites:
  - Ingestion + webhook: `pytest tests/test_xapi_ingestion_pipeline.py tests/test_seventaps_webhook.py`.
  - GCP integration (needs credentials): `pytest tests/test_cloud_function_put.py test_gcp_deployment.py`.
  - UI + monitoring smoke (matches Cloud Build): `pytest tests/test_ui_deployment.py`.
- Manual smoke helpers: `python simple_xapi_test.py` (sends sample statements) and `python test_monitoring_endpoints.py` (writes JSON summaries).
- Deploy with Cloud Build: `gcloud builds submit --config cloudbuild.yaml .` (expects authenticated `gcloud` and valid `GOOGLE_APPLICATION_CREDENTIALS`).

## Automated Test Matrix (Run Without Prompting)
- **Smoke tier (always-on):** `pytest tests/test_ui_deployment.py tests/test_production_validation.py` after any backend/UI change. Capture stdout to the project log and note pass/fail with timestamps.
- **Integration tier:** `pytest tests/test_xapi_ingestion_pipeline.py tests/test_seventaps_webhook.py tests/test_cloud_function_put.py` whenever ingestion, ETL, or GCP config changes. Include curl/JSON artifacts from `/ui/test-xapi-ingestion` and monitoring scripts.
- **Business-case tier:** Run scenario validations (`python research_driven_test_suite.py` or curated business KPI scripts) for changes that impact analytics outputs, SLAs, or stakeholder dashboards. Summarize business impact and attach supporting metrics.
- Tests should be queued automatically once edits begin; do not wait for user requests. If a command is long-running, wrap it in `sleep <seconds> &&` chains so the agent can resume other tasks while results materialize.
- Store command transcripts, generated JSON, and key metrics in `project_management/functionality_improvements.md` (or the active contract note) so humans can audit decisions.

## Proactive Checklist for Agents
- Changes under `app/api/xapi.py` or ingestion ETL → update/inspect `/ui/test-xapi-ingestion`, `/api/xapi/recent`, and rerun ingestion pytest modules.
- Touching BigQuery analytics (`app/api/bigquery_analytics.py`, `app/etl/`) → refresh schema references (`app/config/bigquery_schema.py`), ensure any legacy Redis hooks are removed/ignored, and run `tests/test_bigquery_integration.py`.
- Adjusting monitoring or deployment config (`app/api/gcp_monitoring.py`, `cloudbuild.yaml`, `config/docker-compose.yml`) → execute `test_monitoring_endpoints.py` and document next steps in the active project log if new manual checks are required.
- Introducing endpoints/UI → add a JSON or HTML inspector in `app/ui/` or `templates/`, link it from status responses, and write/extend a coverage test.
- Modifying environment or secrets handling → verify `/api/security/status` and `/api/security/validate-environment` respond without regressions.
- Agents must publish smoke results (where applicable) to `/api/debug/test-report` per `.cursorrules` step 7.
- When running long shell commands in the CLI, estimate duration and, if waiting is safe, stage follow-ups with `sleep <seconds> && <command>` so the workflow keeps moving like a collaborative teammate.

## Autonomy Ramp Roadmap (10 Steps)
1. Reload context: read `AGENTS.md`, `.cursorrules`, and the active contract in `agents/` before taking action.
2. Restate the mission: summarize the requested change, success criteria, and any blocking constraints to confirm alignment.
3. Map to plan: locate the relevant `plan.md` module and verify prerequisites or dependencies are satisfied.
4. Lock invariants: list any "must not break" rules (security, data integrity, deployment boundaries) tied to the work.
5. Prepare the environment: ensure required env vars and credentials exist (`gcloud auth list`, `.env` sanity check, etc.).
6. Stage validation commands: identify the pytest targets, scripts, or curl checks you will run before and after edits.
7. Draft execution notes: outline the sequence of file edits, migrations, and tests in scratch before touching code.
8. Implement iteratively: make minimal cohesive changes, lint/format as you go, and keep diffs scoped to the contract.
9. Self-verify: run the staged commands, capture artifacts (JSON outputs, logs), and confirm endpoints/UI behave as expected.
10. Debrief & propose: summarize changes, note remaining risks, suggest the next module or cleanup, and update any progress trackers.

## Autonomy Milestones (5 Checkpoints)
- **M1: Context Sync** – Agent automatically reloads `AGENTS.md`/contracts and posts a mission summary before editing.
- **M2: Guardrail Compliance** – Every change includes an invariants checklist with confirmations or explicit risk callouts.
- **M3: Test Discipline** – All targeted tests and smoke scripts run without prompting, with artifacts attached or linked.
- **M4: Observability Updates** – UI/status endpoints reflect new fields or behaviors as part of the same change set.
- **M5: Progress Reporting** – Agent updates the active project log (e.g., `project_management/functionality_improvements.md` or current contract notes) and proposes the next action when closing a task.

## If-Then Automation Chains (5 Playbooks)
- **Ingestion Path:** If `app/api/xapi.py` or Pub/Sub ETL changes, then run `pytest tests/test_xapi_ingestion_pipeline.py`, then curl `/ui/test-xapi-ingestion`, then log sample payload IDs in the summary.
- **Analytics Queries:** If BigQuery query logic changes, then regenerate cache schema references, then run `tests/test_bigquery_integration.py`, then capture the updated query snippet in the project log.
- **Deployment Config:** If `cloudbuild.yaml` or Cloud Run env vars change, then execute `pytest tests/test_ui_deployment.py`, then run `python test_monitoring_endpoints.py`, then document deployment deltas and next manual checks.
- **Security Surface:** If `.env` requirements or secrets handling changes, then validate `/api/security/status`, then note rotation impacts, then update `docs/SECURITY.md` or append TODOs if manual steps remain.
- **UI/UX Update:** If `app/ui/` or `templates/` changes, then run the relevant pytest suite, then open the page via `uvicorn` + curl/screenshot, then attach verification notes and list any follow-up analytics wiring.

## Code Style & Conventions
- Python: PEP 8, type hints where practical, prefer f-strings, rely on dependency injection via config helpers.
- Logging: use `structlog` utilities in `app/logging_config.py`; avoid bare `print` outside CLI utilities/tests.
- Response shape: JSON endpoints return dictionaries keyed with status + diagnostics (see `app/api/health.py`); keep backward compatibility with UI expectations.
- Templates use Jinja2 with Tailwind-style utility classes; mirror existing `templates/production_dashboard.html` patterns.
- Keep functions short; factor shared GCP logic into `app/config/` helpers or `app/api/utils/` if created.
- Apply `black` + `isort` before committing (per `.cursorrules`).

## Data & Observability
- Health endpoints: `/health`, `/api/health`, `/api/status`.
- Monitoring endpoints: `/api/monitoring`, `/api/cost`, `/api/gcp/health` (see `app/api/gcp_monitoring.py`).
- Security endpoints: `/api/security/*` (validate env + rotation status).
- UI dashboards: `/` landing dashboard, `/ui/recent-pubsub`, `/ui/data-explorer`, `/ui/db-terminal` (read-only).
- When touching pipelines, update corresponding UI cards/metrics so operators see the new fields and run related tests.

## Security & Secrets
- Never commit service-account keys (`google-cloud-key.json` stays local). Use Secret Manager or environment variables in production.
- `.env` is local only; ensure it stays gitignored. Populate required keys (`OPENAI_API_KEY`, `GCP_*` etc.). Remove any stale `REDIS_URL` entries when found.
- BigQuery and Pub/Sub credentials flow through `app/config.py`; edit defaults there rather than sprinkling env lookups.
- Follow `docs/SECURITY.md` and `SECURITY_SETUP.md` for rotation, auditing, and incident response.

## Multi-Agent Workflow Expectations
- Always read `.cursorrules` and the relevant contract in `agents/*.mdc` before coding; they define module scope and file ownership.
- The orchestrator agent handles module assignment via `project_management/contracts/`; do not self-assign work outside your contract.
- Implementation agents **never** write their own tests; coordinate with the Testing Agent per `docs/AGENTS.md` anti-spec rules.
- After completing a module, run the module’s required pytest selection, capture artifacts (JSON logs, screenshots if applicable), and report status.

## Supporting References
- `README.md` – high-level product overview and repo layout.
- `plan.md` – current module roadmap and migration notes (Cloud Run + Pub/Sub focus).
- `docs/DEPLOYMENT.md` – end-to-end deployment steps (infra + function).
- `docs/AGENTS.md` – extended rules for specialized agents.
- `gcp_deployment_architecture.md` – visual summary of the live topology.
- `research_driven_test_suite.py` / `research_test_results.json` – historical testing baseline for regression context.

Keep this file concise and update it whenever the architecture, workflows, or expectations change so agents stay aligned without repeated prompting.
