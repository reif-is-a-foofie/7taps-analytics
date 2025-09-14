# Assignments and Heartbeats

Purpose: Enable parallel work across agents with clear ownership, dependencies, deliverables, and mandatory heartbeats in line with `agents/orchestrator_agent.mdc`.

## Heartbeat Requirements
- Cadence: Every 15 minutes while working on a contract.
- Where: Update the assigned contract JSON at `project_management/contracts/<contract_id>.json`.
- Format: Append a JSON object to `heartbeats` with the following fields and update `last_heartbeat` and `current_agent`.

Heartbeat JSON template:
```json
{
  "agent": "<agent_name>",
  "contract_id": "<contract_id>",
  "timestamp": "2025-09-14T12:00:00Z",
  "files_modified": ["<file1>", "<file2>"],
  "code_metrics": {
    "lines_of_code": 0,
    "functions_implemented": 0,
    "endpoints_created": 0,
    "test_coverage": 0,
    "files_completed": 0
  },
  "progress_percentage": 0,
  "next_milestone": "<short description>",
  "current_status": "in_progress",
  "blocking_issues": [],
  "completion_estimate": "<ETA>",
  "last_activity": "<what you did since last heartbeat>"
}
```

Additionally (recommended): POST a test/validation report to `/api/debug/test-report` if the app is running.

## Assignments

- Contract: `gc14_cloud_run_service_account`
  - Agent: devops_agent
  - Path: `project_management/contracts/gc14_cloud_run_service_account.json`
  - Dependencies: gc07, gc12
  - Allowed files: `cloudbuild.yaml`, `scripts/deploy_cloud_run_ui.py`, `docs/`, `project_management/progress_reports/gc14_cloud_run_service_account.json`
  - Deliverables:
    - Add `--service-account $_CLOUD_RUN_SA` to Cloud Build deploy step
    - Document minimal IAM roles; ensure trigger substitution `_CLOUD_RUN_SA`
    - Update deploy script to accept `--service-account` (already supported via `CLOUD_RUN_SERVICE_ACCOUNT`)
  - Validation:
    - Cloud Build run shows flag present; Cloud Run service describes with expected SA

- Contract: `gc15_artifact_registry_migration`
  - Agent: devops_agent
  - Path: `project_management/contracts/gc15_artifact_registry_migration.json`
  - Dependencies: gc07, gc14
  - Allowed files: `cloudbuild.yaml`, `cloudbuild.ar.yaml`, `scripts/deploy_cloud_run_ui.py`, `docs/`, progress report JSON
  - Deliverables:
    - Create AR repo `ui` in `us-central1`
    - Add `cloudbuild.ar.yaml` to build/push to `us-central1-docker.pkg.dev/$PROJECT_ID/ui/taps-analytics-ui:TAG`
    - Update deploy to use AR image
  - Validation:
    - Image visible in AR and deploy succeeds from AR

- Contract: `gc16_secret_manager_integration`
  - Agent: devops_agent
  - Path: `project_management/contracts/gc16_secret_manager_integration.json`
  - Dependencies: gc07, gc14
  - Allowed files: `cloudbuild.yaml`, `scripts/deploy_cloud_run_ui.py`, `app/main.py`, `app/config/*.py`, `docs/`, progress report JSON
  - Deliverables:
    - Identify sensitive envs (e.g., `DATABASE_URL`, `REDIS_URL`, webhook secret)
    - Use `--set-secrets` to source from Secret Manager
    - Document creation/rotation of secrets
  - Validation:
    - No secrets present in repo/build files; runtime env populated from secrets

- Contract: `gc17_monitoring_alerts_setup`
  - Agent: devops_agent
  - Path: `project_management/contracts/gc17_monitoring_alerts_setup.json`
  - Dependencies: gc07, gc12
  - Allowed files: `scripts/setup_monitoring_alerts.sh`, `docs/`, progress report JSON
  - Deliverables:
    - Script to create alerts: Cloud Run 5xx rate, p95 latency, Pub/Sub backlog, BigQuery job error ratio
    - Document thresholds and notification channels
  - Validation:
    - `gcloud monitoring policies list` shows policies targeting service

- Contract: `gc18_contracts_cleanup`
  - Agent: project_manager
  - Path: `project_management/contracts/gc18_contracts_cleanup.json`
  - Dependencies: none
  - Allowed files: `project_management/contracts/*.json`, `project_management/README.md`, `project_management/contracts/CONTRACTS.md`
  - Deliverables:
    - Normalize `status` values; fix cross-file references/paths
    - Update README structure to match filesystem
  - Validation:
    - All references resolve; statuses consistent

- Contract: `gc19_docs_sync`
  - Agent: technical_writer
  - Path: `project_management/contracts/gc19_docs_sync.json`
  - Dependencies: gc14, gc15, gc16
  - Allowed files: `gcp_deployment_architecture.md`, `gcp_ui_config.md`, `README.md`
  - Deliverables:
    - Update service name to `taps-analytics-ui`; standardize port 8080
    - Document AR usage and service account requirements
  - Validation:
    - Docs reflect deployed state and steps are runnable

## General Rules
- Follow `.cursorrules` and file boundaries defined in each contract’s `allowed_files`.
- Produce a short progress report JSON under `project_management/progress_reports/` named after the contract when meaningful milestones are hit.
- Do not mark a contract completed until validation conditions are met and tests (where applicable) pass.

