# SMTP Email Setup Guide

## Overview
The POL Analytics platform sends email alerts for flagged content using SMTP (Simple Mail Transfer Protocol). This guide explains how to configure email sending.

## Quick Setup: Gmail SMTP (Recommended)

### Step 1: Create a Gmail App Password

1. Go to [Google Account Settings](https://myaccount.google.com/)
2. Navigate to **Security** → **2-Step Verification** (enable if not already enabled)
3. Scroll down to **App Passwords**
4. Click **Select app** → Choose **Mail**
5. Click **Select device** → Choose **Other (Custom name)**
6. Enter: `POL Analytics`
7. Click **Generate**
8. **Copy the 16-character password** (you won't see it again!)

### Step 2: Set Environment Variables in GCP

You need to set these environment variables in Google Cloud Run:

#### Option A: Using GCP Secret Manager (Recommended for Production)

```bash
# Create secrets
gcloud secrets create alert-email-smtp-server --data-file=- <<< "smtp.gmail.com"
gcloud secrets create alert-email-smtp-username --data-file=- <<< "your-email@gmail.com"
gcloud secrets create alert-email-smtp-password --data-file=- <<< "your-16-char-app-password"
gcloud secrets create alert-email-sender --data-file=- <<< "your-email@gmail.com"

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding alert-email-smtp-server \
    --member="serviceAccount:YOUR_SERVICE_ACCOUNT@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

Then update `cloudbuild.yaml` to mount secrets as environment variables.

#### Option B: Using Cloud Run Environment Variables (Quick Setup)

1. Go to [Cloud Run Console](https://console.cloud.google.com/run)
2. Select your service: `taps-analytics-ui`
3. Click **Edit & Deploy New Revision**
4. Go to **Variables & Secrets** tab
5. Add these environment variables:

```
ALERT_EMAIL_SMTP_SERVER=smtp.gmail.com
ALERT_EMAIL_SMTP_PORT=587
ALERT_EMAIL_SMTP_USERNAME=your-email@gmail.com
ALERT_EMAIL_SMTP_PASSWORD=your-16-char-app-password
ALERT_EMAIL_SENDER=your-email@gmail.com
ALERT_EMAIL_SMTP_USE_TLS=true
```

6. Click **Deploy**

### Step 3: Test Email Configuration

1. Go to `/ui/settings` in the app
2. Click **Test Connection** button
3. Check your email inbox for the test message

## Alternative SMTP Services

### SendGrid

```
ALERT_EMAIL_SMTP_SERVER=smtp.sendgrid.net
ALERT_EMAIL_SMTP_PORT=587
ALERT_EMAIL_SMTP_USERNAME=apikey
ALERT_EMAIL_SMTP_PASSWORD=your-sendgrid-api-key
ALERT_EMAIL_SENDER=your-verified-sender@example.com
```

### Mailgun

```
ALERT_EMAIL_SMTP_SERVER=smtp.mailgun.org
ALERT_EMAIL_SMTP_PORT=587
ALERT_EMAIL_SMTP_USERNAME=your-mailgun-username
ALERT_EMAIL_SMTP_PASSWORD=your-mailgun-password
ALERT_EMAIL_SENDER=your-verified-sender@yourdomain.com
```

### Amazon SES

```
ALERT_EMAIL_SMTP_SERVER=email-smtp.us-east-1.amazonaws.com
ALERT_EMAIL_SMTP_PORT=587
ALERT_EMAIL_SMTP_USERNAME=your-ses-smtp-username
ALERT_EMAIL_SMTP_PASSWORD=your-ses-smtp-password
ALERT_EMAIL_SENDER=your-verified-sender@example.com
```

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ALERT_EMAIL_SMTP_SERVER` | Yes | - | SMTP server hostname |
| `ALERT_EMAIL_SMTP_USERNAME` | Yes | - | SMTP username |
| `ALERT_EMAIL_SMTP_PASSWORD` | Yes | - | SMTP password or App Password |
| `ALERT_EMAIL_SMTP_PORT` | No | `587` | SMTP port (587 for TLS, 465 for SSL) |
| `ALERT_EMAIL_SMTP_USE_TLS` | No | `true` | Enable TLS encryption |
| `ALERT_EMAIL_SENDER` | No | `no-reply@practiceoflife.com` | From email address |

## Troubleshooting

### "SMTP not configured" error
- Check that all required environment variables are set
- Verify variables are accessible in Cloud Run environment
- Check Cloud Run logs for detailed error messages

### "Authentication failed" error
- For Gmail: Make sure you're using an App Password, not your regular password
- Verify 2-Step Verification is enabled
- Check that "Less secure app access" is enabled (if not using App Password)

### "Connection refused" error
- Verify SMTP server hostname is correct
- Check firewall rules allow outbound connections on port 587/465
- Ensure Cloud Run has internet access

### Emails not being received
- Check spam/junk folder
- Verify recipient email addresses are correct
- Check SMTP service sending limits (Gmail: 500/day for free accounts)
- Review Cloud Run logs for delivery errors

## Security Best Practices

1. **Never commit SMTP credentials to Git**
2. **Use GCP Secret Manager for production**
3. **Use App Passwords instead of main passwords**
4. **Rotate passwords regularly**
5. **Monitor email sending logs for suspicious activity**

## Gmail Sending Limits

- **Free Gmail**: 500 emails/day
- **Google Workspace**: 2,000 emails/day (can be increased)
- **Rate limit**: ~100 emails/hour

For higher limits, consider using SendGrid or Amazon SES.

