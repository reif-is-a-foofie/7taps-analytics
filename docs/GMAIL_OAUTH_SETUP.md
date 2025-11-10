# Gmail OAuth Setup Guide

## Quick Setup (Much Easier Than SMTP!)

Instead of configuring SMTP, you can now just **log in with Google**! 🎉

## Step 1: Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project: `pol-a-477603`
3. Navigate to **APIs & Services** → **Credentials**
4. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
5. If prompted, configure the OAuth consent screen:
   - User Type: **Internal** (if using Google Workspace) or **External**
   - App name: **POL Analytics**
   - User support email: Your email
   - Developer contact: Your email
   - Click **Save and Continue**
   - Scopes: Click **Add or Remove Scopes** → Search for `gmail.send` → Select it → **Update** → **Save and Continue**
   - Test users: Add your email address → **Save and Continue**
6. Create OAuth Client ID:
   - Application type: **Web application**
   - Name: **POL Analytics Email**
   - Authorized redirect URIs:
     - `https://taps-analytics-ui-euvwb5vwea-uc.a.run.app/api/settings/gmail/callback`
     - `http://localhost:8000/api/settings/gmail/callback` (for local testing)
   - Click **Create**
7. **Copy the Client ID and Client Secret** (you'll need these!)

## Step 2: Set Environment Variables

### Option A: GCP Secret Manager (Recommended)

```bash
# Create secrets
echo "YOUR_CLIENT_ID" | gcloud secrets create gmail-client-id --data-file=- --project=pol-a-477603
echo "YOUR_CLIENT_SECRET" | gcloud secrets create gmail-client-secret --data-file=- --project=pol-a-477603

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding gmail-client-id \
    --member="serviceAccount:YOUR_SERVICE_ACCOUNT@pol-a-477603.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=pol-a-477603

gcloud secrets add-iam-policy-binding gmail-client-secret \
    --member="serviceAccount:YOUR_SERVICE_ACCOUNT@pol-a-477603.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=pol-a-477603
```

Then update `cloudbuild.yaml` to mount these secrets.

### Option B: Cloud Run Environment Variables (Quick)

1. Go to [Cloud Run Console](https://console.cloud.google.com/run)
2. Select service: `taps-analytics-ui`
3. Click **Edit & Deploy New Revision**
4. Go to **Variables & Secrets** tab
5. Add:
   - `GMAIL_CLIENT_ID` = Your Client ID
   - `GMAIL_CLIENT_SECRET` = Your Client Secret
   - `GMAIL_REDIRECT_URI` = `https://taps-analytics-ui-euvwb5vwea-uc.a.run.app/api/settings/gmail/callback`
6. Click **Deploy**

## Step 3: Connect Gmail in the App

1. Go to `/ui/settings` in your app
2. Click **🔗 Connect Gmail Account**
3. You'll be redirected to Google to authorize
4. Click **Allow**
5. You'll be redirected back - Gmail is now connected! ✅

## That's It!

No SMTP configuration needed. The app will automatically:
- Use Gmail OAuth to send emails
- Refresh tokens automatically
- Fall back to SMTP if OAuth isn't configured

## Troubleshooting

### "Gmail OAuth not configured" error
- Make sure `GMAIL_CLIENT_ID` and `GMAIL_CLIENT_SECRET` are set
- Check that redirect URI matches exactly in Google Cloud Console

### "Redirect URI mismatch" error
- Make sure the redirect URI in Google Cloud Console matches:
  - Production: `https://taps-analytics-ui-euvwb5vwea-uc.a.run.app/api/settings/gmail/callback`
  - Local: `http://localhost:8000/api/settings/gmail/callback`

### OAuth consent screen issues
- Make sure you've added yourself as a test user
- If using external users, the app may need verification (for production)

## Security Notes

- OAuth tokens are stored securely in BigQuery
- Tokens are automatically refreshed when expired
- You can revoke access anytime from [Google Account Settings](https://myaccount.google.com/permissions)

