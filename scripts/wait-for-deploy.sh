#!/bin/bash
# Wait for Cloud Build to complete after git push
# Usage: ./scripts/wait-for-deploy.sh [commit_sha]

set -e

PROJECT_ID="pol-a-477603"
SERVICE_NAME="taps-analytics-ui"
REGION="us-central1"
MAX_WAIT_TIME=600  # 10 minutes max
POLL_INTERVAL=5    # Check every 5 seconds

COMMIT_SHA="${1:-$(git rev-parse --short HEAD)}"
echo "🔍 Waiting for deployment of commit: $COMMIT_SHA"
echo ""

# Wait for build to start (up to 30 seconds)
echo "⏳ Waiting for Cloud Build to start..."
BUILD_STARTED=false
for i in {1..6}; do
    sleep 5
    LATEST_BUILD=$(gcloud builds list \
        --project=$PROJECT_ID \
        --limit=1 \
        --format="value(id,status,createTime)" 2>/dev/null | head -1)
    
    if [ -n "$LATEST_BUILD" ]; then
        BUILD_ID=$(echo $LATEST_BUILD | awk '{print $1}')
        BUILD_STATUS=$(echo $LATEST_BUILD | awk '{print $2}')
        BUILD_TIME=$(echo $LATEST_BUILD | awk '{print $3}')
        
        # Check if build was created recently (within last 2 minutes)
        BUILD_AGE=$(($(date +%s) - $(date -d "$BUILD_TIME" +%s 2>/dev/null || echo 0)))
        
        if [ "$BUILD_AGE" -lt 120 ] && [ "$BUILD_STATUS" != "SUCCESS" ] && [ "$BUILD_STATUS" != "FAILURE" ]; then
            BUILD_STARTED=true
            echo "✅ Build started: $BUILD_ID"
            break
        fi
    fi
done

if [ "$BUILD_STARTED" = false ]; then
    echo "⚠️  No recent build found. Checking latest build status..."
    LATEST_BUILD=$(gcloud builds list \
        --project=$PROJECT_ID \
        --limit=1 \
        --format="value(id,status)" 2>/dev/null | head -1)
    
    if [ -n "$LATEST_BUILD" ]; then
        BUILD_ID=$(echo $LATEST_BUILD | awk '{print $1}')
        BUILD_STATUS=$(echo $LATEST_BUILD | awk '{print $2}')
        echo "   Latest build: $BUILD_ID - Status: $BUILD_STATUS"
        
        if [ "$BUILD_STATUS" = "SUCCESS" ]; then
            echo "✅ Latest build already completed successfully!"
            BUILD_STARTED=true
        elif [ "$BUILD_STATUS" = "FAILURE" ]; then
            echo "❌ Latest build failed. Check logs:"
            echo "   gcloud builds log $BUILD_ID --project=$PROJECT_ID"
            exit 1
        fi
    else
        echo "❌ No builds found. Trigger may not have fired."
        echo "   Check: https://console.cloud.google.com/cloud-build/triggers?project=$PROJECT_ID"
        exit 1
    fi
fi

# Monitor build until completion
if [ "$BUILD_STARTED" = true ] && [ "$BUILD_STATUS" != "SUCCESS" ]; then
    echo ""
    echo "⏳ Monitoring build progress..."
    START_TIME=$(date +%s)
    
    while true; do
        CURRENT_TIME=$(date +%s)
        ELAPSED=$((CURRENT_TIME - START_TIME))
        
        if [ $ELAPSED -gt $MAX_WAIT_TIME ]; then
            echo "❌ Timeout: Build took longer than $MAX_WAIT_TIME seconds"
            exit 1
        fi
        
        BUILD_INFO=$(gcloud builds describe $BUILD_ID \
            --project=$PROJECT_ID \
            --format="value(status,logUrl)" 2>/dev/null || echo "")
        
        if [ -n "$BUILD_INFO" ]; then
            CURRENT_STATUS=$(echo $BUILD_INFO | awk '{print $1}')
            LOG_URL=$(echo $BUILD_INFO | awk '{print $2}')
            
            if [ "$CURRENT_STATUS" = "SUCCESS" ]; then
                echo ""
                echo "✅ Build completed successfully!"
                echo "   Build ID: $BUILD_ID"
                echo "   Duration: ${ELAPSED}s"
                echo "   Logs: $LOG_URL"
                break
            elif [ "$CURRENT_STATUS" = "FAILURE" ] || [ "$CURRENT_STATUS" = "CANCELLED" ] || [ "$CURRENT_STATUS" = "EXPIRED" ]; then
                echo ""
                echo "❌ Build failed with status: $CURRENT_STATUS"
                echo "   Build ID: $BUILD_ID"
                echo "   Logs: $LOG_URL"
                echo ""
                echo "View logs: gcloud builds log $BUILD_ID --project=$PROJECT_ID"
                exit 1
            else
                # Show progress
                printf "\r   Status: $CURRENT_STATUS (${ELAPSED}s elapsed)..."
            fi
        fi
        
        sleep $POLL_INTERVAL
    done
fi

# Verify deployment
echo ""
echo "🔍 Verifying Cloud Run deployment..."
sleep 5  # Give Cloud Run a moment to update

SERVICE_STATUS=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format="value(status.conditions[0].status,status.latestReadyRevisionName)" 2>/dev/null || echo "")

if [ -n "$SERVICE_STATUS" ]; then
    READY_STATUS=$(echo $SERVICE_STATUS | awk '{print $1}')
    REVISION=$(echo $SERVICE_STATUS | awk '{print $2}')
    
    if [ "$READY_STATUS" = "True" ]; then
        echo "✅ Service is ready!"
        echo "   Revision: $REVISION"
        echo "   URL: https://taps-analytics-ui-euvwb5vwea-uc.a.run.app"
        
        # Test health endpoint
        echo ""
        echo "🏥 Testing health endpoint..."
        HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
            "https://taps-analytics-ui-euvwb5vwea-uc.a.run.app/api/health" || echo "000")
        
        if [ "$HEALTH_RESPONSE" = "200" ]; then
            echo "✅ Health check passed!"
        else
            echo "⚠️  Health check returned: $HEALTH_RESPONSE"
        fi
    else
        echo "⚠️  Service status: $READY_STATUS"
        echo "   Revision: $REVISION"
    fi
else
    echo "⚠️  Could not verify service status"
fi

echo ""
echo "✅ Deployment verification complete!"

