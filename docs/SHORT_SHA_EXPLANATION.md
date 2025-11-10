# Understanding SHORT_SHA vs COMMIT_SHA

## What They Are

**COMMIT_SHA** = Full Git commit hash (40 characters)
- Example: `b28b42d6f5648ebf6db2d45d27abf13e73e4ae54`
- Provided automatically by Cloud Build when triggered from GitHub
- Unique identifier for the exact commit

**SHORT_SHA** = First 7 characters of commit hash
- Example: `b28b42d` (from the full SHA above)
- Shorter, easier to use in Docker image tags
- Still unique enough for most purposes

## Why We Need This

Our `cloudbuild.yaml` uses `${SHORT_SHA}` to tag Docker images:
```yaml
-t 'gcr.io/$PROJECT_ID/taps-analytics-ui:${SHORT_SHA}'
```

This creates images like:
- `gcr.io/pol-a-477603/taps-analytics-ui:b28b42d`

Instead of the full SHA:
- `gcr.io/pol-a-477603/taps-analytics-ui:b28b42d6f5648ebf6db2d45d27abf13e73e4ae54` ❌ (too long!)

## The Problem

Cloud Build triggers from GitHub automatically provide `$COMMIT_SHA`, but NOT `$SHORT_SHA`.

We need to extract the first 7 characters somehow.

## Solution Options

### Option 1: Use COMMIT_SHA Directly (Simplest)
Just use the full commit SHA - Docker can handle it, it's just longer.

### Option 2: Add a Build Step to Extract SHORT_SHA
Add a step that runs: `SHORT_SHA=$(echo $COMMIT_SHA | cut -c1-7)`

### Option 3: Configure Trigger Substitution
In the Cloud Build trigger UI, set:
- Variable: `SHORT_SHA`
- Value: `${COMMIT_SHA:0:7}` (if supported)

## Current Status

Right now:
- ✅ Manual triggers work (deploy.sh provides SHORT_SHA)
- ⚠️ GitHub triggers would need SHORT_SHA configured

**Recommendation**: Use COMMIT_SHA directly - it's simpler and works automatically!

