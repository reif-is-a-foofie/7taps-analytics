#!/bin/bash
# Setup Cloud Build trigger for automatic deployments
# Usage: ./scripts/setup-trigger.sh

set -e

PROJECT_ID="pol-a-477603"
TRIGGER_NAME="taps-analytics-deploy"
REPO_OWNER="reif-is-a-foofie"
REPO_NAME="7taps-analytics"
BRANCH_PATTERN="^main$"
BUILD_CONFIG="cloudbuild.yaml"

echo "🔧 Setting up Cloud Build Trigger"
echo "=================================="
echo ""

# Check if trigger already exists
EXISTING_TRIGGER=$(gcloud builds triggers list \
    --project=$PROJECT_ID \
    --format="value(name)" 2>/dev/null | grep "^${TRIGGER_NAME}$" || echo "")

if [ -n "$EXISTING_TRIGGER" ]; then
    echo "✅ Trigger '$TRIGGER_NAME' already exists"
    echo ""
    echo "Current configuration:"
    gcloud builds triggers describe $TRIGGER_NAME \
        --project=$PROJECT_ID \
        --format="table(name,github.owner,github.name,branch,status)" 2>/dev/null || true
    echo ""
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing trigger."
        exit 0
    fi
    echo "Deleting existing trigger..."
    gcloud builds triggers delete $TRIGGER_NAME --project=$PROJECT_ID --quiet
fi

echo "Creating Cloud Build trigger..."
echo "  Name: $TRIGGER_NAME"
echo "  Repository: $REPO_OWNER/$REPO_NAME"
echo "  Branch: $BRANCH_PATTERN"
echo "  Config: $BUILD_CONFIG"
echo ""

# Try to create trigger via GitHub App (most common)
if gcloud builds triggers create github \
    --name="$TRIGGER_NAME" \
    --repo-name="$REPO_NAME" \
    --repo-owner="$REPO_OWNER" \
    --branch-pattern="$BRANCH_PATTERN" \
    --build-config="$BUILD_CONFIG" \
    --project=$PROJECT_ID 2>&1; then
    echo ""
    echo "✅ Trigger created successfully!"
else
    echo ""
    echo "⚠️  Could not create trigger via CLI (GitHub App may not be connected)"
    echo ""
    echo "Please create it manually:"
    echo "1. Go to: https://console.cloud.google.com/cloud-build/triggers/add?project=$PROJECT_ID"
    echo "2. Configure:"
    echo "   - Name: $TRIGGER_NAME"
    echo "   - Event: Push to branch"
    echo "   - Repository: $REPO_OWNER/$REPO_NAME"
    echo "   - Branch: $BRANCH_PATTERN"
    echo "   - Config: $BUILD_CONFIG"
    echo ""
    exit 1
fi

echo ""
echo "✅ Setup complete!"
echo "The trigger will automatically deploy when you push to main branch."
echo "Test it by running: ./deploy.sh"

