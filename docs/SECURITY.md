# Security Guide for 7taps Analytics

## API Key Management

### Current Status
- ✅ Environment variables properly configured
- ✅ .gitignore excludes .env files
- ✅ Secure secrets management system implemented
- ✅ API key validation and monitoring in place

### Environment Variables Setup

Create a `.env` file in the project root with the following structure:

```bash
# Required: Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/database_name
PGSSLMODE=require

# Required: OpenAI API Configuration
OPENAI_API_KEY=sk-proj-your-openai-api-key-here

# Optional: Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Optional: Application Configuration
APP_PORT=8000
ENVIRONMENT=development
DEBUG=true
```

### Security Best Practices

#### 1. API Key Management
- **Never commit API keys to version control**
- **Rotate keys every 90 days**
- **Use environment-specific keys**
- **Monitor key usage for suspicious activity**

#### 2. Environment Variables
- **Use .env files for local development**
- **Set production variables via deployment platform**
- **Validate environment on application startup**
- **Use strong, unique passwords**

#### 3. Access Control
- **Implement proper authentication**
- **Use HTTPS in production**
- **Limit API access to necessary endpoints**
- **Monitor access patterns**

## Security Monitoring

### Security Status Endpoint
Access security status at: `/api/security/status`

This endpoint provides:
- Environment validation status
- Secrets configuration status
- Rotation recommendations
- Suspicious activity detection

### Environment Validation
Access validation at: `/api/security/validate-environment`

This endpoint validates:
- Required environment variables are present
- API key format is valid
- Secrets meet minimum length requirements

### Key Rotation Status
Access rotation status at: `/api/security/check-rotation`

This endpoint shows:
- Which secrets need rotation
- Last rotation dates
- Rotation recommendations

## Preventing Future Leaks

### 1. Pre-commit Hooks
Consider implementing pre-commit hooks to scan for:
- API keys in code
- Hardcoded credentials
- Sensitive data patterns

### 2. Automated Scanning
Implement automated scanning for:
- Secrets in git history
- Exposed credentials in logs
- API key usage patterns

### 3. Monitoring and Alerting
Set up monitoring for:
- Unusual API usage patterns
- Failed authentication attempts
- Environment variable changes

### 4. Development Workflow
- Use separate API keys for development/staging/production
- Implement key rotation schedules
- Regular security audits
- Team security training

## Incident Response

### If an API Key is Leaked

1. **Immediate Actions**
   - Revoke the exposed key immediately
   - Generate a new key
   - Update all environment variables
   - Check git history for exposure

2. **Investigation**
   - Identify how the key was exposed
   - Check for unauthorized usage
   - Review access logs
   - Update security procedures

3. **Prevention**
   - Implement additional security measures
   - Update team procedures
   - Conduct security review
   - Document lessons learned

## Security Endpoints

### Available Security APIs

- `GET /api/security/status` - Comprehensive security status
- `GET /api/security/validate-environment` - Environment validation
- `GET /api/security/check-rotation` - Key rotation status
- `POST /api/security/rotate-secret` - Request secret rotation

### Example Usage

```bash
# Check security status
curl http://localhost:8000/api/security/status

# Validate environment
curl http://localhost:8000/api/security/validate-environment

# Check rotation status
curl http://localhost:8000/api/security/check-rotation
```

## Deployment Security

### Cloud Run Deployment
Use either Secret Manager or the Cloud Run UI/CLI to set runtime variables:

```bash
gcloud run services update taps-analytics-ui \
  --region=us-central1 \
  --set-env-vars OPENAI_API_KEY=your-new-key,REDIS_URL=redis://...
```

Verify configuration with `gcloud run services describe taps-analytics-ui`.

### Local Development
```bash
# Copy example environment file
cp .env.example .env

# Edit with your values
nano .env

# Verify .env is in .gitignore
git status
```

## Security Checklist

- [ ] All API keys stored in environment variables
- [ ] .env files excluded from version control
- [ ] Production keys different from development
- [ ] Keys rotated every 90 days
- [ ] Security monitoring enabled
- [ ] HTTPS used in production
- [ ] Access controls implemented
- [ ] Team security training completed
- [ ] Incident response plan documented
- [ ] Regular security audits scheduled
