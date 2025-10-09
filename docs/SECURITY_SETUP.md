# 🔐 Security Setup Guide for 7taps Analytics

## 🚨 CRITICAL SECURITY INFORMATION

This document outlines the **mandatory security setup** for the 7taps Analytics application, particularly for Google Cloud Platform integration.

---

## Google Cloud Service Account Key Setup

### ⚠️ SECURITY WARNING
**NEVER commit Google Cloud service account keys to version control!**

Service account keys provide full access to your GCP resources and can be extremely costly if compromised.

### ✅ Current Status
- ✅ `google-cloud-key.json` is properly gitignored
- ✅ No service account keys are committed to git history
- ✅ `.gitignore` includes comprehensive key file patterns

### 🔧 Setup Instructions

1. **Create/Access Service Account in GCP Console:**
   ```bash
   # Go to: https://console.cloud.google.com/iam-admin/serviceaccounts
   # Create a new service account or use existing one
   ```

2. **Required GCP Permissions:**
   ```yaml
   roles/cloudfunctions.invoker     # Invoke Cloud Functions
   roles/pubsub.publisher          # Publish to Pub/Sub topics
   roles/pubsub.subscriber         # Subscribe to Pub/Sub topics
   roles/storage.objectAdmin       # Cloud Storage management
   roles/bigquery.dataEditor       # BigQuery data operations
   roles/bigquery.jobUser          # BigQuery job execution
   roles/logging.logWriter         # Cloud Logging
   roles/monitoring.metricWriter   # Cloud Monitoring
   ```

3. **Download Service Account Key:**
   ```bash
   # In GCP Console:
   # 1. Select your service account
   # 2. Go to "Keys" tab
   # 3. Click "Add Key" → "Create new key" → JSON
   # 4. Download the JSON file
   ```

4. **Place Key File:**
   ```bash
   # Rename downloaded file to: google-cloud-key.json
   # Place in project root directory
   cp ~/Downloads/your-key-file.json ./google-cloud-key.json
   ```

5. **Verify Key Security:**
   ```bash
   # Ensure key file is not tracked by git
   git ls-files | grep google-cloud-key.json || echo "✅ Key file is not tracked"

   # Check file permissions (should be readable by owner only)
   ls -la google-cloud-key.json
   ```

---

## Environment Variables Configuration

### 📄 .env File Setup

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

### 🔑 Required Environment Variables

```bash
# GCP Configuration
GCP_PROJECT_ID=your-gcp-project-id
GCP_REGION=us-central1
GCP_ZONE=us-central1-a

# Database
DATABASE_URL=postgresql://user:password@host:5432/database

# Redis
REDIS_URL=redis://localhost:6379

# 7taps Integration
SEVENTAPS_PRIVATE_KEY_PATH=keys/7taps_private_key.pem
SEVENTAPS_PUBLIC_KEY_PATH=keys/7taps_public_key.pem
SEVENTAPS_WEBHOOK_SECRET=your-secure-webhook-secret

# Application
LOG_LEVEL=info
DEBUG=false
APP_PORT=8000
```

---

## Security Best Practices

### 🔒 Key Management
- **Rotate keys regularly** (recommended: every 90 days)
- **Use different keys for different environments**
- **Delete unused keys immediately**
- **Monitor key usage** in GCP Console

### 🛡️ Access Control
- **Principle of least privilege**: Grant only necessary permissions
- **Regular IAM audits**: Review service account permissions quarterly
- **VPC Service Controls**: Enable for additional network security
- **Cloud Identity-Aware Proxy**: For additional access control

### 📊 Monitoring & Alerting
- **Enable Cloud Logging** for all services
- **Set up Cloud Monitoring alerts** for unusual activity
- **Regular security audits** of GCP resources
- **Monitor service account key usage**

### 🚨 Incident Response
- **Immediate key rotation** if compromise is suspected
- **Disable compromised service accounts**
- **Audit all recent GCP activity**
- **Update all dependent systems**

---

## Deployment Security Checklist

- [ ] Service account key downloaded and placed in project root
- [ ] Key file is not committed to git (`git ls-files | grep key` should return nothing)
- [ ] `.env` file configured with secure values
- [ ] Environment variables not containing sensitive data
- [ ] GCP IAM permissions follow least privilege principle
- [ ] Cloud Logging and Monitoring enabled
- [ ] Regular key rotation scheduled
- [ ] Security monitoring alerts configured

---

## Emergency Procedures

### If Service Account Key is Compromised:
1. **IMMEDIATELY DELETE** the compromised key from GCP Console
2. **Rotate all dependent credentials**
3. **Audit all GCP resources** for unauthorized access
4. **Update deployment configurations**
5. **Notify security team** if applicable

### If Environment Variables are Exposed:
1. **Regenerate all secrets** (API keys, webhook secrets, etc.)
2. **Update all `.env` files** across all environments
3. **Check git history** for any committed sensitive data
4. **Update deployment pipelines**

---

## Security Resources

- [GCP IAM Documentation](https://cloud.google.com/iam/docs)
- [Service Account Key Best Practices](https://cloud.google.com/iam/docs/service-account-keys)
- [VPC Service Controls](https://cloud.google.com/vpc-service-controls)
- [Cloud Security Command Center](https://cloud.google.com/security-command-center)

---

## Contact Information

For security concerns or questions about this setup:
- Review GCP Security documentation
- Check internal security policies
- Contact your security team

---

**Remember: Security is everyone's responsibility. Always err on the side of caution when handling credentials and sensitive data.**
