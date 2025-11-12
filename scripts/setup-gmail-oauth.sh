#!/bin/bash
# Quick setup script for Gmail OAuth credentials
# Usage: ./scripts/setup-gmail-oauth.sh

set -e

PROJECT_ID="pol-a-477603"
CLIENT_ID="410871346241-0q7892qfnnrmuov6iq5eriva3va0n6i9.apps.googleusercontent.com"

echo "🔧 Setting up Gmail OAuth Credentials"
echo "====================================="
echo ""
echo "Client ID: $CLIENT_ID"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI not found. Please install it first."
    exit 1
fi

echo "📋 Prerequisites:"
echo "  1. Get your Client Secret from Google Cloud Console"
echo "  2. Go to: APIs & Services → Credentials → OAuth 2.0 Client IDs"
echo "  3. Click on your client ID to view the secret"
echo ""
read -p "Enter your Client Secret: " -s CLIENT_SECRET
echo ""

if [[ -z "$CLIENT_SECRET" ]]; then
    echo "❌ Error: Client Secret is required"
    exit 1
fi

echo ""
echo "Creating secrets in GCP Secret Manager..."

# Create or update secrets
echo "$CLIENT_ID" | gcloud secrets create gmail-client-id \
    --data-file=- \
    --project=$PROJECT_ID \
    --replication-policy="automatic" 2>/dev/null || \
    echo "$CLIENT_ID" | gcloud secrets versions add gmail-client-id \
        --data-file=- \
        --project=$PROJECT_ID

echo "$CLIENT_SECRET" | gcloud secrets create gmail-client-secret \
    --data-file=- \
    --project=$PROJECT_ID \
    --replication-policy="automatic" 2>/dev/null || \
    echo "$CLIENT_SECRET" | gcloud secrets versions add gmail-client-secret \
        --data-file=- \
        --project=$PROJECT_ID

REDIRECT_URI="https://taps-analytics-ui-euvwb5vwea-uc.a.run.app/api/settings/gmail/callback"
echo "$REDIRECT_URI" | gcloud secrets create gmail-redirect-uri \
    --data-file=- \
    --project=$PROJECT_ID \
    --replication-policy="automatic" 2>/dev/null || \
    echo "$REDIRECT_URI" | gcloud secrets versions add gmail-redirect-uri \
        --data-file=- \
        --project=$PROJECT_ID

echo ""
echo "✅ Secrets created successfully!"
echo ""
echo "📝 Next Steps:"
echo ""
echo "Option 1: Set in Cloud Run directly (Quickest)"
echo "-----------------------------------------------"
echo "Run this command:"
echo ""
echo "gcloud run services update taps-analytics-ui \\"
echo "  --set-env-vars=\"GMAIL_CLIENT_ID=$CLIENT_ID,GMAIL_CLIENT_SECRET=$CLIENT_SECRET,GMAIL_REDIRECT_URI=$REDIRECT_URI\" \\"
echo "  --region=us-central1 \\"
echo "  --project=$PROJECT_ID"
echo ""
echo "Option 2: Use Secret Manager (More Secure)"
echo "-------------------------------------------"
echo "Update cloudbuild.yaml to mount secrets, then redeploy."
echo ""
echo "After setting environment variables:"
echo "  1. Go to /ui/settings in your app"
echo "  2. Click 'Connect Gmail Account'"
echo "  3. Authorize with Google"
echo ""

