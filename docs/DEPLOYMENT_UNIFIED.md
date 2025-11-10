# How Auto-Deploy and Manual Deploy Work Together

## Overview

Both **auto-deploy** (GitHub trigger) and **manual deploy** (`deploy.sh`) use the **same** `cloudbuild.yaml` configuration file. This ensures consistency.

## How It Works

### 1. Auto-Deploy (GitHub Trigger)

**Triggered by:** Push to `main` branch on GitHub

**Flow:**
```
GitHub Push → Cloud Build Trigger → cloudbuild.yaml → Deploy to Cloud Run
```

**Details:**
- Cloud Build trigger watches `main` branch
- On push, automatically runs `cloudbuild.yaml`
- Cloud Build provides `$SHORT_SHA` automatically (first 7 chars of commit)
- No manual intervention needed

**Configuration:**
- Trigger name: `taps-analytics-deploy`
- Branch pattern: `^main$`
- Config file: `cloudbuild.yaml`
- Substitutions: None needed (Cloud Build auto-provides `SHORT_SHA`)

### 2. Manual Deploy (`deploy.sh`)

**Triggered by:** Running `./deploy.sh`

**Flow:**
```
deploy.sh → Commit & Push → Check Trigger → Wait for Auto OR Manual Trigger → cloudbuild.yaml → Deploy
```

**Details:**
1. Commits changes via `quick-commit.sh`
2. Pushes to GitHub `main` branch
3. Checks if Cloud Build trigger exists
4. **If trigger exists:** Waits for auto-trigger (up to 30s)
5. **If no trigger or timeout:** Manually triggers with `gcloud builds submit`
6. Both paths use the **same** `cloudbuild.yaml`

**Why Both Use Same Config:**
- Ensures consistency between auto and manual deployments
- Same secrets, same environment variables
- Same deployment settings
- No configuration drift

## Secrets and Environment Variables

### Current Setup (in `cloudbuild.yaml`)

```yaml
--set-secrets: GOOGLE_AI_API_KEY, GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET
--set-env-vars: GMAIL_REDIRECT_URI
```

**Both auto-deploy and manual deploy:**
- ✅ Use the same secrets from Secret Manager
- ✅ Use the same environment variables
- ✅ Deploy to the same Cloud Run service
- ✅ Use the same image tags (`${SHORT_SHA}`)

## Key Points

1. **Single Source of Truth:** `cloudbuild.yaml` is used by both methods
2. **No Duplication:** Secrets/env vars defined once, used everywhere
3. **Consistency:** Auto and manual deployments are identical
4. **Fallback:** Manual deploy falls back if auto-trigger doesn't fire

## Troubleshooting

### Auto-Deploy Not Working
- Check trigger exists: `gcloud builds triggers list`
- Verify GitHub connection in Cloud Console
- Check trigger branch pattern matches `^main$`

### Manual Deploy Issues
- `deploy.sh` automatically detects and uses trigger if available
- Falls back to manual trigger if needed
- Both use same `cloudbuild.yaml` so results are identical

### Secrets Not Available
- Secrets must be in Secret Manager
- Must be mounted in `cloudbuild.yaml` via `--set-secrets`
- Both auto and manual deploy will use them automatically

## Best Practices

1. **Always use `cloudbuild.yaml`** - Don't set secrets directly in Cloud Run
2. **Use Secret Manager** - Store sensitive values there
3. **Mount in cloudbuild.yaml** - Both methods will use them
4. **Test both paths** - Verify auto and manual deploy work

