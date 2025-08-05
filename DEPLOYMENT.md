# 🚀 7taps Analytics - Production Deployment Guide

## Overview
This guide covers deploying the 7taps Analytics ETL application to production for stable webhook endpoints.

## 🎯 Quick Deployment Options

### Option 1: Railway (Recommended - Fastest)
1. **Connect GitHub Repository**
   - Go to [railway.app](https://railway.app)
   - Sign up with GitHub
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your `7taps-analytics` repository

2. **Configure Environment Variables**
   ```bash
   DATABASE_URL=your_postgres_url
   REDIS_URL=your_redis_url
   SEVENTAPS_WEBHOOK_SECRET=your_secret_here
   OPENAI_API_KEY=your_openai_key
   ```

3. **Deploy**
   - Railway will automatically detect the Python app
   - Build and deploy automatically
   - Get your production URL (e.g., `https://7taps-analytics.railway.app`)

### Option 2: Render
1. **Create New Web Service**
   - Go to [render.com](https://render.com)
   - Connect GitHub repository
   - Create new "Web Service"
   - Select your repository

2. **Configure Build Settings**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

3. **Add Environment Variables**
   - Same as Railway above

### Option 3: Heroku
1. **Install Heroku CLI**
   ```bash
   brew install heroku/brew/heroku
   ```

2. **Deploy**
   ```bash
   heroku create 7taps-analytics
   git push heroku main
   ```

3. **Add Add-ons**
   ```bash
   heroku addons:create heroku-postgresql
   heroku addons:create heroku-redis
   ```

## 🔧 Environment Setup

### Required Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/db

# Redis
REDIS_URL=redis://user:pass@host:port

# 7taps Configuration
SEVENTAPS_WEBHOOK_SECRET=your_webhook_secret
SEVENTAPS_AUTH_ENABLED=true
SEVENTAPS_VERIFY_SIGNATURE=true

# OpenAI (for NLP features)
OPENAI_API_KEY=your_openai_key

# Application
LOG_LEVEL=info
ENVIRONMENT=production
```

### PEM Keys Setup
1. **Generate keys locally** (already done)
2. **Upload to production:**
   - Copy `keys/7taps_private_key.pem` to production
   - Copy `keys/7taps_public_key.pem` to production
   - Set file permissions: `chmod 600 keys/7taps_private_key.pem`

## 🌐 Domain Configuration

### Custom Domain (Recommended)
1. **Purchase domain** (e.g., `7taps-analytics.com`)
2. **Configure DNS:**
   ```
   Type: CNAME
   Name: @
   Value: your-app.railway.app
   ```

### SSL Certificate
- Railway/Render/Heroku provide automatic SSL
- Custom domains get free SSL certificates

## 🔗 7taps Integration

### Webhook Configuration
Once deployed, configure 7taps with:

**Webhook URL:** `https://your-domain.com/api/7taps/webhook`

**Public Key:**
```
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAt2eaCrickieAdVeZjupD
vtxdRryikZ42GiTjB3zmHmFcxN5RRDfI0f3PxCmX38FhpgnJM9G/QdZeXn9MrgsW
Xu3h9i9oDDQ07H1I9WAqxtCte5QbA+dx+ZsEz6dvL7FSb4tjjZxQ9K2DzAZJigFT
/mcisjvFoC10HTJ+x3qhE+jptd+ULrpo0gzhyttYpaeV4cmjeNPNVefjKITWQDVl
G39A+q4z+U3JUukKyqXa4CE62cTHGqPof+zLq4EdUp5pGE7RWKXqvr3AX2jTx4TZ
n7rQY1FWdNgVTVoI/C06lz9lYPGaXTEFJDwlZl1AiwTa0zLE4QLiIyqPG+m6X9Dl
CwIDAQAB
-----END PUBLIC KEY-----
```

## 📊 Monitoring & Health Checks

### Health Check Endpoint
- **URL:** `https://your-domain.com/health`
- **Expected Response:** `{"status": "healthy", "service": "7taps-analytics-etl"}`

### Dashboard Access
- **URL:** `https://your-domain.com/ui/dashboard`
- **Features:** Real-time metrics, charts, analytics

## 🔍 Testing Production Deployment

### 1. Health Check
```bash
curl https://your-domain.com/health
```

### 2. Test Webhook
```bash
curl -X POST https://your-domain.com/api/7taps/webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "webhook"}'
```

### 3. Test xAPI Ingestion
```bash
curl -X POST https://your-domain.com/api/xapi/ingest \
  -H "Content-Type: application/json" \
  -d '{"actor": {"name": "test"}, "verb": {"id": "http://adlnet.gov/expapi/verbs/completed"}, "object": {"id": "http://example.com/activity"}}'
```

## 🚨 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check `DATABASE_URL` environment variable
   - Ensure database is accessible from production

2. **Redis Connection Failed**
   - Check `REDIS_URL` environment variable
   - Ensure Redis is accessible from production

3. **PEM Key Not Found**
   - Upload keys to production server
   - Check file permissions (600 for private key)

4. **Webhook Signature Invalid**
   - Verify public key is correctly configured in 7taps
   - Check `SEVENTAPS_WEBHOOK_SECRET` is set

## 📈 Scaling Considerations

### For High Traffic
1. **Database Scaling**
   - Upgrade to larger database instance
   - Consider read replicas for analytics queries

2. **Application Scaling**
   - Railway/Render: Upgrade to paid plan for more resources
   - Heroku: Use dyno scaling

3. **Caching**
   - Redis is already configured for caching
   - Consider CDN for static assets

## 🔐 Security Best Practices

1. **Environment Variables**
   - Never commit secrets to Git
   - Use platform-specific secret management

2. **PEM Keys**
   - Keep private key secure
   - Rotate keys periodically

3. **HTTPS**
   - Always use HTTPS in production
   - Configure HSTS headers

## 📞 Support

For deployment issues:
1. Check platform-specific logs
2. Verify environment variables
3. Test endpoints individually
4. Monitor application health

---

**🎉 Once deployed, you'll have a stable, production-ready endpoint for 7taps integration!** 