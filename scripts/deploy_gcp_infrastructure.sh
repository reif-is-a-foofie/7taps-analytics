#!/bin/bash

# Google Cloud Platform Infrastructure Deployment Script
#
# This script deploys the complete Google Cloud Platform infrastructure for
# the 7taps Analytics application, including:
#
# - Cloud Function for xAPI ingestion
# - Verification of all GCP resources
# - Health checks and validation
#
# Usage:
#   ./deploy_gcp_infrastructure.sh [OPTIONS]
#
# Options:
#   --project-id PROJECT_ID    GCP Project ID (default: taps-data)
#   --region REGION           GCP Region (default: us-central1)
#   --dry-run                 Show what would be done without making changes
#   --force                   Force redeployment even if resources exist
#   --help                    Show this help message
#
# Requirements:
# - Google Cloud SDK (gcloud) installed and authenticated
# - Service account key file (google-cloud-key.json) in project root
# - Appropriate GCP permissions for deployment
#
# Exit codes:
#   0 - Success
#   1 - General error
#   2 - Prerequisites not met
#   3 - Deployment failed

set -euo pipefail

# Default configuration
PROJECT_ID="${PROJECT_ID:-taps-data}"
REGION="${REGION:-us-central1}"
DRY_RUN=false
FORCE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Show usage information
show_help() {
    cat << EOF
Google Cloud Platform Infrastructure Deployment Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --project-id PROJECT_ID    GCP Project ID (default: taps-data)
    --region REGION           GCP Region (default: us-central1)
    --dry-run                 Show what would be done without making changes
    --force                   Force redeployment even if resources exist
    --help                    Show this help message

EXAMPLES:
    $0 --dry-run
    $0 --project-id my-project --region us-west1
    $0 --force

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --project-id)
            PROJECT_ID="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_ROOT/config/gcp_deployment_config.json"
SERVICE_ACCOUNT_KEY="$PROJECT_ROOT/google-cloud-key.json"

# Cloud Function configuration
FUNCTION_NAME="cloud-ingest-xapi"
FUNCTION_ENTRY_POINT="cloud_ingest_xapi"
MEMORY_MB=512
TIMEOUT=60
MAX_INSTANCES=100

# Validate prerequisites
validate_prerequisites() {
    log_info "Validating prerequisites..."

    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed. Please install Google Cloud SDK."
        return 1
    fi

    # Check if authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n 1 > /dev/null; then
        log_error "Not authenticated with Google Cloud. Please run 'gcloud auth login'."
        return 1
    fi

    # Check if service account key exists
    if [[ ! -f "$SERVICE_ACCOUNT_KEY" ]]; then
        log_error "Service account key file not found: $SERVICE_ACCOUNT_KEY"
        return 1
    fi

    # Check if config file exists
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Configuration file not found: $CONFIG_FILE"
        return 1
    fi

    # Check if Cloud Function source exists
    if [[ ! -f "$PROJECT_ROOT/app/api/cloud_function_ingestion.py" ]]; then
        log_error "Cloud Function source file not found: $PROJECT_ROOT/app/api/cloud_function_ingestion.py"
        return 1
    fi

    log_success "Prerequisites validation passed"
    return 0
}

# Set up GCP project
setup_gcp_project() {
    log_info "Setting up GCP project: $PROJECT_ID"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would set project to $PROJECT_ID"
        return 0
    fi

    # Set the project
    gcloud config set project "$PROJECT_ID"

    # Verify project exists and is accessible
    if ! gcloud projects describe "$PROJECT_ID" &> /dev/null; then
        log_error "Project $PROJECT_ID does not exist or is not accessible"
        return 1
    fi

    log_success "GCP project configured: $PROJECT_ID"
    return 0
}

# Enable required APIs
enable_apis() {
    log_info "Enabling required Google Cloud APIs..."

    local apis=(
        "cloudfunctions.googleapis.com"
        "pubsub.googleapis.com"
        "storage.googleapis.com"
        "bigquery.googleapis.com"
        "cloudbuild.googleapis.com"
        "iam.googleapis.com"
        "logging.googleapis.com"
        "monitoring.googleapis.com"
    )

    for api in "${apis[@]}"; do
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "DRY RUN: Would enable API $api"
            continue
        fi

        log_info "Enabling $api..."
        if ! gcloud services enable "$api" --project "$PROJECT_ID"; then
            log_error "Failed to enable API: $api"
            return 1
        fi
    done

    log_success "All required APIs enabled"
    return 0
}

# Deploy Cloud Function
deploy_cloud_function() {
    log_info "Deploying Cloud Function: $FUNCTION_NAME"

    local source_dir="$PROJECT_ROOT/app/api"
    local requirements_file="$PROJECT_ROOT/requirements.txt"

    # Create deployment command
    local deploy_cmd=(
        gcloud functions deploy "$FUNCTION_NAME"
        --project "$PROJECT_ID"
        --region "$REGION"
        --runtime python39
        --source "$source_dir"
        --entry-point "$FUNCTION_ENTRY_POINT"
        --trigger-http
        --allow-unauthenticated
        --memory "$MEMORY_MB"MB
        --timeout "$TIMEOUT"
        --max-instances "$MAX_INSTANCES"
    )

    # Add environment variables
    deploy_cmd+=(--set-env-vars "GCP_PROJECT_ID=$PROJECT_ID")
    deploy_cmd+=(--set-env-vars "PUBSUB_TOPIC=xapi-ingestion-topic")
    deploy_cmd+=(--set-env-vars "STORAGE_BUCKET=taps-data-raw-xapi")

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would deploy Cloud Function"
        log_info "Command: ${deploy_cmd[*]}"
        return 0
    fi

    # Check if function already exists
    if gcloud functions describe "$FUNCTION_NAME" --project "$PROJECT_ID" --region "$REGION" &> /dev/null; then
        if [[ "$FORCE" == "true" ]]; then
            log_warning "Cloud Function already exists, redeploying due to --force flag"
        else
            log_warning "Cloud Function already exists. Use --force to redeploy."
            return 0
        fi
    fi

    # Deploy the function
    if ! "${deploy_cmd[@]}"; then
        log_error "Failed to deploy Cloud Function"
        return 1
    fi

    # Get the function URL
    local function_url
    function_url=$(gcloud functions describe "$FUNCTION_NAME" \
        --project "$PROJECT_ID" \
        --region "$REGION" \
        --format="value(httpsTrigger.url)")

    log_success "Cloud Function deployed successfully"
    log_info "Function URL: $function_url"

    # Test the function
    log_info "Testing Cloud Function deployment..."
    if curl -s -o /dev/null -w "%{http_code}" "$function_url" | grep -q "405\|200"; then
        log_success "Cloud Function is responding correctly"
    else
        log_warning "Cloud Function may not be responding as expected"
    fi

    return 0
}

# Validate infrastructure
validate_infrastructure() {
    log_info "Validating GCP infrastructure..."

    local validation_passed=true

    # Validate Pub/Sub topics
    log_info "Checking Pub/Sub topics..."
    local topics=("xapi-ingestion-topic")
    for topic in "${topics[@]}"; do
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "DRY RUN: Would check topic $topic"
            continue
        fi

        if ! gcloud pubsub topics describe "$topic" --project "$PROJECT_ID" &> /dev/null; then
            log_error "Pub/Sub topic not found: $topic"
            validation_passed=false
        else
            log_success "Pub/Sub topic exists: $topic"
        fi
    done

    # Validate Pub/Sub subscriptions
    log_info "Checking Pub/Sub subscriptions..."
    local subscriptions=("xapi-storage-subscriber" "xapi-bigquery-subscriber")
    for subscription in "${subscriptions[@]}"; do
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "DRY RUN: Would check subscription $subscription"
            continue
        fi

        if ! gcloud pubsub subscriptions describe "$subscription" --project "$PROJECT_ID" &> /dev/null; then
            log_error "Pub/Sub subscription not found: $subscription"
            validation_passed=false
        else
            log_success "Pub/Sub subscription exists: $subscription"
        fi
    done

    # Validate Cloud Storage buckets
    log_info "Checking Cloud Storage buckets..."
    local buckets=("taps-data-raw-xapi")
    for bucket in "${buckets[@]}"; do
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "DRY RUN: Would check bucket $bucket"
            continue
        fi

        if ! gsutil ls -b "gs://$bucket" &> /dev/null; then
            log_error "Cloud Storage bucket not found: $bucket"
            validation_passed=false
        else
            log_success "Cloud Storage bucket exists: $bucket"
        fi
    done

    # Validate BigQuery datasets
    log_info "Checking BigQuery datasets..."
    local datasets=("taps_data")
    for dataset in "${datasets[@]}"; do
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "DRY RUN: Would check dataset $dataset"
            continue
        fi

        if ! bq show --project_id "$PROJECT_ID" "$dataset" &> /dev/null; then
            log_error "BigQuery dataset not found: $dataset"
            validation_passed=false
        else
            log_success "BigQuery dataset exists: $dataset"
        fi
    done

    # Validate Cloud Function
    log_info "Checking Cloud Function..."
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would check Cloud Function $FUNCTION_NAME"
    else
        if ! gcloud functions describe "$FUNCTION_NAME" --project "$PROJECT_ID" --region "$REGION" &> /dev/null; then
            log_error "Cloud Function not found: $FUNCTION_NAME"
            validation_passed=false
        else
            log_success "Cloud Function exists: $FUNCTION_NAME"
        fi
    fi

    if [[ "$validation_passed" == "true" ]]; then
        log_success "Infrastructure validation passed"
        return 0
    else
        log_error "Infrastructure validation failed"
        return 1
    fi
}

# Generate deployment report
generate_report() {
    log_info "Generating deployment report..."

    local report_file="$PROJECT_ROOT/gcp_deployment_report_$(date +%Y%m%d_%H%M%S).json"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would generate report at $report_file"
        return 0
    fi

    # Collect deployment information
    local deployment_info
    deployment_info=$(cat << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "project_id": "$PROJECT_ID",
  "region": "$REGION",
  "dry_run": $DRY_RUN,
  "force": $FORCE,
  "cloud_function": {
    "name": "$FUNCTION_NAME",
    "region": "$REGION",
    "memory_mb": $MEMORY_MB,
    "timeout": $TIMEOUT,
    "max_instances": $MAX_INSTANCES
  },
  "validation_passed": $(validate_infrastructure && echo "true" || echo "false")
}
EOF
)

    echo "$deployment_info" > "$report_file"
    log_success "Deployment report saved to: $report_file"

    return 0
}

# Main deployment function
main() {
    log_info "Starting Google Cloud Platform Infrastructure Deployment"
    log_info "Project: $PROJECT_ID"
    log_info "Region: $REGION"
    log_info "Dry Run: $DRY_RUN"
    log_info "Force: $FORCE"
    echo

    # Validate prerequisites
    if ! validate_prerequisites; then
        log_error "Prerequisites validation failed"
        exit 2
    fi

    # Setup GCP project
    if ! setup_gcp_project; then
        log_error "GCP project setup failed"
        exit 3
    fi

    # Enable APIs
    if ! enable_apis; then
        log_error "API enablement failed"
        exit 3
    fi

    # Deploy Cloud Function
    if ! deploy_cloud_function; then
        log_error "Cloud Function deployment failed"
        exit 3
    fi

    # Validate infrastructure
    if ! validate_infrastructure; then
        log_error "Infrastructure validation failed"
        exit 3
    fi

    # Generate report
    generate_report

    log_success "Google Cloud Platform Infrastructure Deployment Complete!"
    log_info "All GCP resources have been successfully deployed and validated"
    echo
    log_info "Next steps:"
    log_info "1. Test the Cloud Function endpoint"
    log_info "2. Monitor Pub/Sub message flow"
    log_info "3. Check BigQuery data ingestion"
    log_info "4. Review monitoring dashboards"

    exit 0
}

# Handle script interruption
trap 'log_error "Deployment interrupted by user"; exit 1' INT TERM

# Run main function
main "$@"