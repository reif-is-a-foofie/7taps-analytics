#!/bin/bash

# Complete CI/CD setup script
echo "🚀 Complete CI/CD Setup for 7taps Analytics"
echo "============================================="

PROJECT_ID="taps-data"
REPO_OWNER="reif-is-a-foofie"
REPO_NAME="7taps-analytics"

echo "📋 Project: $PROJECT_ID"
echo "📋 Repository: $REPO_OWNER/$REPO_NAME"
echo ""

# Step 1: Enable APIs
echo "🔧 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com --project=$PROJECT_ID --quiet
gcloud services enable run.googleapis.com --project=$PROJECT_ID --quiet
gcloud services enable artifactregistry.googleapis.com --project=$PROJECT_ID --quiet
echo "✅ APIs enabled"
echo ""

# Step 2: Check if GitHub App is already installed
echo "🔍 Checking GitHub App installation..."
TRIGGERS_COUNT=$(gcloud builds triggers list --project=$PROJECT_ID --format="value(name)" | wc -l)

if [ $TRIGGERS_COUNT -gt 0 ]; then
    echo "✅ GitHub App already installed, triggers exist"
    gcloud builds triggers list --project=$PROJECT_ID
else
    echo "📱 GitHub App not installed yet"
    echo ""
    echo "🔗 Please visit: https://github.com/apps/google-cloud-build/installations/new"
    echo ""
    echo "Steps:"
    echo "1. Select 'reif-is-a-foofie' account"
    echo "2. Choose 'Selected repositories'"
    echo "3. Select '7taps-analytics'"
    echo "4. Click 'Install'"
    echo ""
    
    # Try to open browser
    if command -v open &> /dev/null; then
        open "https://github.com/apps/google-cloud-build/installations/new"
        echo "🌐 Opened browser automatically"
    fi
    
    echo ""
    read -p "Press Enter AFTER completing the GitHub App installation..."
    echo ""
fi

# Step 3: Create triggers (with retry logic)
echo "🎯 Creating deployment triggers..."

# Function to create trigger with retry
create_trigger() {
    local name=$1
    local branch=$2
    local config=$3
    local description=$4
    
    echo "Creating $name trigger..."
    
    for i in {1..3}; do
        if gcloud builds triggers create github \
            --repo-owner=$REPO_OWNER \
            --repo-name=$REPO_NAME \
            --branch-pattern="$branch" \
            --build-config=$config \
            --name="$name" \
            --description="$description" \
            --project=$PROJECT_ID --quiet; then
            echo "✅ $name trigger created"
            return 0
        else
            echo "⏳ Attempt $i failed, retrying in 5 seconds..."
            sleep 5
        fi
    done
    
    echo "❌ Failed to create $name trigger after 3 attempts"
    return 1
}

# Create production trigger
create_trigger "safety-api-production" "^main$" "cloudbuild.yaml" "Deploy safety-api to production on main branch push"

# Create staging trigger  
create_trigger "safety-api-staging" "^dev$" "cloudbuild-staging.yaml" "Deploy safety-api to staging on dev branch push"

# Step 4: Verify setup
echo ""
echo "📋 Verifying setup..."
gcloud builds triggers list --project=$PROJECT_ID

echo ""
echo "🎉 CI/CD Setup Complete!"
echo ""
echo "📋 Your workflow:"
echo "1. Make changes in Cursor"
echo "2. Run: mario"
echo "3. Changes deploy automatically in 30-90 seconds"
echo ""
echo "🔗 Monitor deployments:"
echo "https://console.cloud.google.com/cloud-build/triggers?project=$PROJECT_ID"
echo ""
echo "🧪 Test deployment:"
echo "echo 'Testing deployment' >> README.md && mario"
