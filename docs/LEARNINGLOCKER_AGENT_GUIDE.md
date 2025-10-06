# Learning Locker Agent Guide

## Contract Overview

### Backend Agent (b13_learninglocker_integration)
**Status**: In Progress (3/5 subtasks completed)

**Completed Tasks:**
- ✅ Learning Locker Docker Setup
- ✅ Sync Service Implementation  
- ✅ Sync API Endpoints

**Remaining Tasks:**
- 🔄 Production Deployment
- 🔄 Data Migration & Testing

### UI Agent (b14_learninglocker_ui)
**Status**: Not Started (waiting for backend completion)

**Tasks:**
- 🔄 Learning Locker Admin Dashboard
- 🔄 Statement Browser Integration
- 🔄 Data Export Interface
- 🔄 Analytics Dashboard Enhancement
- 🔄 User Access Management

## Quick Reference

### Backend Agent Tasks

#### b13.04 - Production Deployment
```bash
# Deploy Learning Locker to production
# Files: render.yaml, docker-compose.yml
# Acceptance: Learning Locker deployed, env vars configured, health checks passing
```

#### b13.05 - Data Migration & Testing
```bash
# Test sync functionality
# Files: tests/test_learninglocker_sync.py
# Acceptance: Existing statements sync, new statements sync, data integrity verified
```

### UI Agent Tasks

#### b14.01 - Learning Locker Admin Dashboard
```python
# Files: app/ui/learninglocker_admin.py, templates/learninglocker_admin.html
# Features: Sync status, manual sync button, real-time updates, error reporting
```

#### b14.02 - Statement Browser Integration
```python
# Files: app/ui/statement_browser.py, templates/statement_browser.html
# Features: Statement list, filtering, search, detail view
```

#### b14.03 - Data Export Interface
```python
# Files: app/ui/data_export.py, templates/data_export.html
# Features: Export formats (JSON, CSV, XML), date filtering, download
```

#### b14.04 - Analytics Dashboard Enhancement
```python
# Files: app/ui/dashboard.py, templates/dashboard.html
# Features: Learning Locker charts, sync indicators, activity graphs
```

#### b14.05 - User Access Management
```python
# Files: app/ui/user_management.py, templates/user_management.html
# Features: Role management, access control, login/logout, permissions
```

## API Endpoints Available

### Sync Endpoints
- `POST /api/sync-learninglocker` - Manual sync trigger
- `GET /api/sync-status` - Sync status and statistics
- `GET /api/learninglocker-info` - Connection information

### xAPI Endpoints
- `POST /statements` - Post xAPI statements
- `GET /statements` - Get xAPI statements
- `GET /about` - LRS information

## Learning Locker Access

### Local Development
- **URL**: http://localhost:8080
- **Admin**: http://localhost:8080/admin
- **Credentials**: admin@7taps.com / admin123

### Production
- **URL**: Configured via environment variables
- **Admin**: Your Learning Locker domain/admin
- **Credentials**: As configured

## Testing Checklist

### Backend Agent Testing
- [ ] Learning Locker starts successfully
- [ ] Database connection established
- [ ] Sync service connects to Redis
- [ ] Authentication with Learning Locker works
- [ ] API endpoints return correct responses
- [ ] Production deployment successful
- [ ] Data migration completed
- [ ] Performance acceptable

### UI Agent Testing
- [ ] Admin dashboard loads correctly
- [ ] Sync status displays accurately
- [ ] Manual sync button functional
- [ ] Statement browser works
- [ ] Filtering and search functional
- [ ] Data export works
- [ ] Analytics charts display
- [ ] User management interface works

## Dependencies

### Backend Agent Dependencies
- b02_streaming_etl (completed)
- b07_xapi_ingestion (completed)

### UI Agent Dependencies
- b13_learninglocker_integration (in progress)

## Handoff Process

### Backend → UI Agent
- Complete b13.04 and b13.05
- Update contract status to "completed"
- Notify UI agent that infrastructure is ready

### UI → Testing Agent
- Complete all b14 subtasks
- Update contract status to "completed"
- Submit for testing agent verification

## Common Issues & Solutions

### Learning Locker Not Starting
```bash
# Check logs
docker-compose logs learninglocker

# Verify environment variables
docker-compose config

# Restart service
docker-compose restart learninglocker
```

### Sync Not Working
```bash
# Check Redis connection
docker-compose exec app redis-cli ping

# Test sync manually
curl -X POST http://localhost:8000/api/sync-learninglocker

# Check sync status
curl http://localhost:8000/api/sync-status
```

### UI Not Loading
```bash
# Check service health
curl http://localhost:8080/health

# Verify port mapping
docker-compose ps

# Check browser console for errors
```

## Success Criteria

### Backend Agent Success
- Learning Locker running in production
- Sync service operational
- API endpoints functional
- Data migration completed
- Performance acceptable

### UI Agent Success
- Admin dashboard functional
- Statement browser working
- Data export operational
- Analytics enhanced
- User management complete

## Next Steps

1. **Backend Agent**: Complete production deployment and testing
2. **UI Agent**: Wait for backend completion, then implement UI components
3. **Testing Agent**: Verify both contracts meet requirements
4. **Orchestrator**: Mark contracts as completed after testing approval 