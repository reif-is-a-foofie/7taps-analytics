# Manual GitHub to Cloud Build Setup

Since the automated triggers are failing, here's the **manual setup** that will definitely work:

## 🔗 **Step 1: Install GitHub App**

1. **Visit**: https://github.com/apps/google-cloud-build/installations/new
2. **Select**: `reif-is-a-foofie` account
3. **Choose**: "Selected repositories"
4. **Select**: `7taps-analytics`
5. **Click**: "Install"

## 🎯 **Step 2: Create Triggers via Console**

### **Production Trigger**:
1. Go to: https://console.cloud.google.com/cloud-build/triggers?project=taps-data
2. Click **"Create Trigger"**
3. Fill in:
   - **Name**: `safety-api-production`
   - **Repository**: `reif-is-a-foofie/7taps-analytics`
   - **Branch**: `^main$`
   - **Configuration**: `Cloud Build configuration file (yaml or json)`
   - **Location**: `/cloudbuild.yaml`

### **Staging Trigger**:
1. Click **"Create Trigger"** again
2. Fill in:
   - **Name**: `safety-api-staging`
   - **Repository**: `reif-is-a-foofie/7taps-analytics`
   - **Branch**: `^dev$`
   - **Configuration**: `Cloud Build configuration file (yaml or json)`
   - **Location**: `/cloudbuild-staging.yaml`

## 🧪 **Step 3: Test Deployment**

```bash
# Test staging deployment
echo "Testing staging deployment" >> README.md
mario

# Check deployment status
gcloud builds list --limit=5
```

## 🚀 **Alternative: Use GitHub Actions**

If Cloud Build continues to have issues, we can use GitHub Actions instead:

1. **Create**: `.github/workflows/deploy.yml`
2. **Deploy**: Directly to Cloud Run
3. **Trigger**: On push to main/dev branches

This approach bypasses Cloud Build entirely and gives you the same 30-90 second deployment speed.

Would you like me to set up GitHub Actions as an alternative?
