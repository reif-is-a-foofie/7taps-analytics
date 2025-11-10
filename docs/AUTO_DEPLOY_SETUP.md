# Auto-Deploy Setup Guide

## ✅ Current Status
- Build monitoring: ✅ Working
- Latest build: ✅ Completed successfully
- Auto-deploy trigger: ⚠️ Needs setup

## 🚀 Setting Up Auto-Deploy on GitHub Push

### Step 1: Connect GitHub Repository (One-Time)

1. Go to: https://console.cloud.google.com/cloud-build/triggers/add?project=pol-a-477603

2. Click **"Connect Repository"** if you haven't already:
   - Select **GitHub (Cloud Build GitHub App)**
   - Authorize Cloud Build to access your repositories
   - Select: `reif-is-a-foofie/7taps-analytics`

### Step 2: Create Trigger

Configure the trigger:

- **Name**: `taps-analytics-deploy`
- **Event**: Push to a branch
- **Branch**: `^main$` (regex pattern)
- **Configuration**: Cloud Build configuration file
- **Location**: `cloudbuild.yaml`
- **Substitution variables** (click "Show advanced"):
  - **SHORT_SHA**: `${COMMIT_SHA:0:7}` 
    - This extracts the first 7 characters of the commit SHA automatically
    - **Note**: Use the substitution expression `${COMMIT_SHA:0:7}` in the trigger configuration

### Step 3: Verify

After creating the trigger:
- Push a test commit to `main` branch
- Check Cloud Build console for automatic build
- Build should trigger within seconds of push

## 📋 Manual Trigger (Fallback)

If auto-trigger doesn't fire, `deploy.sh` will automatically:
1. Detect missing trigger
2. Manually trigger build
3. Show verbose output
4. Monitor until completion

## 🔍 Monitoring

- **Build Status**: https://console.cloud.google.com/cloud-build/builds?project=pol-a-477603
- **Trigger Status**: https://console.cloud.google.com/cloud-build/triggers?project=pol-a-477603

## ⚙️ How It Works

1. **GitHub Push** → Webhook fires
2. **Cloud Build Trigger** → Detects push to `main`
3. **Substitution** → `SHORT_SHA` = first 7 chars of `COMMIT_SHA`
4. **Build** → Uses `cloudbuild.yaml` with substitutions
5. **Deploy** → Automatically deploys to Cloud Run

## 🎯 Expected Behavior

- ✅ Every push to `main` → Automatic deployment
- ✅ Build time: ~30-40 seconds (with base image)
- ✅ No manual steps required
- ✅ Verbose output in Cloud Build logs

