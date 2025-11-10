#!/bin/bash
# Reliable deployment flow: commit -> push -> trigger -> monitor -> verify

set -e

PROJECT_ID="pol-a-477603"
SERVICE_NAME="taps-analytics-ui"
REGION="us-central1"
PRODUCTION_URL="https://taps-analytics-ui-euvwb5vwea-uc.a.run.app"

echo "🚀 Reliable Deploy Pipeline"
echo "=========================="
echo ""

# Step 1: Commit and push
echo "📝 Step 1: Committing and pushing changes..."
if ! ./quick-commit.sh; then
    echo "❌ Commit failed. Aborting deployment."
    exit 1
fi

COMMIT_SHA=$(git rev-parse --short HEAD)
echo "✅ Committed: $COMMIT_SHA"
echo ""

# Step 2: Check for Cloud Build trigger
echo "🔍 Step 2: Checking Cloud Build trigger..."
TRIGGER_NAME="taps-analytics-deploy"
TRIGGER_EXISTS=$(gcloud builds triggers list --project=$PROJECT_ID --format="value(name)" 2>/dev/null | grep -q "^${TRIGGER_NAME}$" && echo "1" || echo "0")

if [ "$TRIGGER_EXISTS" = "0" ]; then
    echo "⚠️  No Cloud Build trigger found. Will trigger manually."
    USE_MANUAL_TRIGGER=true
else
    echo "✅ Cloud Build trigger exists: $TRIGGER_NAME"
    USE_MANUAL_TRIGGER=false
fi
echo ""

# Step 3: Trigger build
echo "☁️  Step 3: Triggering Cloud Build..."
if [ "$USE_MANUAL_TRIGGER" = true ]; then
    echo "📤 Manually triggering build..."
    BUILD_ID=$(gcloud builds submit \
        --config=cloudbuild.yaml \
        --substitutions=SHORT_SHA=$COMMIT_SHA \
        --project=$PROJECT_ID \
        --async \
        --format="value(id)" 2>&1)
    
    if [ -z "$BUILD_ID" ] || [[ "$BUILD_ID" == *"ERROR"* ]]; then
        echo "❌ Failed to trigger build: $BUILD_ID"
        exit 1
    fi
    echo "✅ Build triggered: $BUILD_ID"
else
    echo "⏳ Waiting for auto-trigger (max 30s)..."
    sleep 5
    
    # Wait for build to appear
    MAX_WAIT=30
    WAITED=0
    BUILD_ID=""
    
    while [ $WAITED -lt $MAX_WAIT ]; do
        # Get most recent build
        BUILD_ID=$(gcloud builds list \
            --project=$PROJECT_ID \
            --limit=1 \
            --format="value(id)" 2>/dev/null || echo "")
        
        if [ -n "$BUILD_ID" ]; then
            # Check if it matches our commit SHA
            BUILD_SHA=$(gcloud builds describe $BUILD_ID \
                --project=$PROJECT_ID \
                --format="value(substitutions.SHORT_SHA)" 2>/dev/null || echo "")
            
            if [ "$BUILD_SHA" = "$COMMIT_SHA" ]; then
                echo "✅ Build detected: $BUILD_ID"
                break
            fi
        fi
        
        sleep 2
        WAITED=$((WAITED + 2))
        echo -n "."
    done
    
    if [ -z "$BUILD_ID" ]; then
        echo ""
        echo "⚠️  Auto-trigger didn't fire. Manually triggering..."
        BUILD_ID=$(gcloud builds submit \
            --config=cloudbuild.yaml \
            --substitutions=SHORT_SHA=$COMMIT_SHA \
            --project=$PROJECT_ID \
            --async \
            --format="value(id)" 2>&1)
        
        if [ -z "$BUILD_ID" ] || [[ "$BUILD_ID" == *"ERROR"* ]]; then
            echo "❌ Failed to trigger build: $BUILD_ID"
            exit 1
        fi
        echo "✅ Build triggered manually: $BUILD_ID"
    fi
fi
echo ""

# Step 4: Monitor build
echo "📊 Step 4: Monitoring build progress..."
echo "Build ID: $BUILD_ID"
echo "Monitor: https://console.cloud.google.com/cloud-build/builds/$BUILD_ID?project=$PROJECT_ID"
echo ""

PREVIOUS_STATUS=""
MAX_BUILD_TIME=600  # 10 minutes
ELAPSED=0
POLL_INTERVAL=5

while true; do
    STATUS=$(gcloud builds describe $BUILD_ID \
        --project=$PROJECT_ID \
        --format="value(status)" 2>/dev/null || echo "UNKNOWN")
    
    if [ "$STATUS" != "$PREVIOUS_STATUS" ]; then
        case "$STATUS" in
            "QUEUED")
                echo "⏳ Status: QUEUED (waiting to start)..."
                ;;
            "WORKING")
                echo "🔨 Status: WORKING (building)..."
                ;;
            "SUCCESS")
                echo "✅ Status: SUCCESS (deployment complete!)"
                break
                ;;
            "FAILURE"|"CANCELLED"|"EXPIRED"|"TIMEOUT")
                echo "❌ Status: $STATUS"
                echo ""
                echo "📋 Build logs:"
                gcloud builds log $BUILD_ID --project=$PROJECT_ID | tail -50
                exit 1
                ;;
            "UNKNOWN")
                echo "⚠️  Could not fetch build status. Retrying..."
                ;;
        esac
        PREVIOUS_STATUS=$STATUS
    else
        echo -n "."
    fi
    
    if [ "$STATUS" = "SUCCESS" ]; then
        break
    fi
    
    if [ $ELAPSED -ge $MAX_BUILD_TIME ]; then
        echo ""
        echo "⏱️  Build exceeded maximum time ($MAX_BUILD_TIME seconds)"
        echo "Check logs: https://console.cloud.google.com/cloud-build/builds/$BUILD_ID?project=$PROJECT_ID"
        exit 1
    fi
    
    sleep $POLL_INTERVAL
    ELAPSED=$((ELAPSED + POLL_INTERVAL))
done

echo ""

# Step 5: Verify deployment
echo "🔍 Step 5: Verifying deployment..."
sleep 3  # Give Cloud Run a moment to update

if curl -sf "$PRODUCTION_URL/api/health" > /dev/null 2>&1; then
    echo "✅ Health check passed"
else
    echo "⚠️  Health check failed (service may still be updating)"
fi

echo ""
echo "🎉 Deployment Complete!"
echo "======================="
echo "✅ Build: $BUILD_ID"
echo "✅ Commit: $COMMIT_SHA"
echo "🔗 Production: $PRODUCTION_URL"
echo "📊 Build logs: https://console.cloud.google.com/cloud-build/builds/$BUILD_ID?project=$PROJECT_ID"
echo ""

# Show build duration
BUILD_TIME=$(gcloud builds describe $BUILD_ID \
    --project=$PROJECT_ID \
    --format="value(timing.buildDuration)" 2>/dev/null || echo "unknown")
echo "⏱️  Build time: $BUILD_TIME"
