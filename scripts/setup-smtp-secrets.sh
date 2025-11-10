#!/bin/bash
# Quick setup script for SMTP email configuration in GCP
# Usage: ./scripts/setup-smtp-secrets.sh

set -e

PROJECT_ID="pol-a-477603"

echo "🔧 Setting up SMTP Email Configuration"
echo "======================================"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI not found. Please install it first."
    exit 1
fi

echo "This script will help you set up SMTP secrets in GCP Secret Manager."
echo ""
echo "📋 Prerequisites:"
echo "  1. Gmail account with 2-Step Verification enabled"
echo "  2. Gmail App Password created (16 characters)"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

echo ""
echo "📧 Gmail SMTP Configuration"
echo "---------------------------"
read -p "Enter your Gmail address: " GMAIL_ADDRESS
read -p "Enter your Gmail App Password (16 chars): " -s APP_PASSWORD
echo ""

# Validate inputs
if [[ -z "$GMAIL_ADDRESS" ]] || [[ -z "$APP_PASSWORD" ]]; then
    echo "❌ Error: Gmail address and App Password are required"
    exit 1
fi

if [[ ${#APP_PASSWORD} -ne 16 ]]; then
    echo "⚠️  Warning: App Password should be 16 characters. Continuing anyway..."
fi

echo ""
echo "Creating secrets in GCP Secret Manager..."

# Create secrets
echo "$GMAIL_ADDRESS" | gcloud secrets create alert-email-smtp-username \
    --data-file=- \
    --project=$PROJECT_ID \
    --replication-policy="automatic" 2>/dev/null || \
    echo "$GMAIL_ADDRESS" | gcloud secrets versions add alert-email-smtp-username \
        --data-file=- \
        --project=$PROJECT_ID

echo "$APP_PASSWORD" | gcloud secrets create alert-email-smtp-password \
    --data-file=- \
    --project=$PROJECT_ID \
    --replication-policy="automatic" 2>/dev/null || \
    echo "$APP_PASSWORD" | gcloud secrets versions add alert-email-smtp-password \
        --data-file=- \
        --project=$PROJECT_ID

echo "smtp.gmail.com" | gcloud secrets create alert-email-smtp-server \
    --data-file=- \
    --project=$PROJECT_ID \
    --replication-policy="automatic" 2>/dev/null || \
    echo "smtp.gmail.com" | gcloud secrets versions add alert-email-smtp-server \
        --data-file=- \
        --project=$PROJECT_ID

echo "$GMAIL_ADDRESS" | gcloud secrets create alert-email-sender \
    --data-file=- \
    --project=$PROJECT_ID \
    --replication-policy="automatic" 2>/dev/null || \
    echo "$GMAIL_ADDRESS" | gcloud secrets versions add alert-email-sender \
        --data-file=- \
        --project=$PROJECT_ID

echo "587" | gcloud secrets create alert-email-smtp-port \
    --data-file=- \
    --project=$PROJECT_ID \
    --replication-policy="automatic" 2>/dev/null || \
    echo "587" | gcloud secrets versions add alert-email-smtp-port \
        --data-file=- \
        --project=$PROJECT_ID

echo ""
echo "✅ Secrets created successfully!"
echo ""
echo "📝 Next Steps:"
echo "  1. Update cloudbuild.yaml to mount these secrets"
echo "  2. Or set them as environment variables in Cloud Run"
echo ""
echo "To set in Cloud Run directly, run:"
echo "  gcloud run services update taps-analytics-ui \\"
echo "    --set-secrets=\"ALERT_EMAIL_SMTP_SERVER=alert-email-smtp-server:latest,ALERT_EMAIL_SMTP_USERNAME=alert-email-smtp-username:latest,ALERT_EMAIL_SMTP_PASSWORD=alert-email-smtp-password:latest,ALERT_EMAIL_SENDER=alert-email-sender:latest,ALERT_EMAIL_SMTP_PORT=alert-email-smtp-port:latest\" \\"
echo "    --region=us-central1 \\"
echo "    --project=$PROJECT_ID"
echo ""

