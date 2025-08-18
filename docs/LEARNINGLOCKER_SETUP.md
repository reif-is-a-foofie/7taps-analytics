# Learning Locker Integration Guide

## Overview

Learning Locker is a full-featured xAPI Learning Record Store (LRS) that provides advanced data exploration and visualization capabilities. This integration adds Learning Locker alongside our custom LRS for enhanced data checking and analysis.

## Architecture

```
7taps → Custom LRS → Redis Streams → ETL Pipeline → Postgres
                    ↓
              Learning Locker Sync
                    ↓
              Learning Locker LRS
```

## Benefits

### For Data Checking:
- ✅ **Statement Browser**: Visual exploration of xAPI statements
- ✅ **Advanced Queries**: Complex xAPI-specific filtering
- ✅ **Data Export**: Export statements in various formats
- ✅ **Visual Analytics**: Built-in charts and graphs
- ✅ **xAPI Compliance**: Full LRS implementation

### For Team Access:
- ✅ **Web Interface**: User-friendly admin panel
- ✅ **Role-based Access**: Different user permissions
- ✅ **Real-time Updates**: Live statement viewing
- ✅ **Search & Filter**: Advanced data exploration

## Setup Instructions

### 1. Local Development

```bash
# Start all services including Learning Locker
docker-compose up -d

# Check Learning Locker status
curl http://localhost:8080

# Access Learning Locker admin
# URL: http://localhost:8080/admin
# Username: admin@7taps.com
# Password: admin123
```

### 2. Production Deployment

```bash
# Set Learning Locker environment variables
heroku config:set LEARNINGLOCKER_URL=https://your-learninglocker-domain.com --app seventaps-analytics
heroku config:set LEARNINGLOCKER_USERNAME=admin@7taps.com --app seventaps-analytics
heroku config:set LEARNINGLOCKER_PASSWORD=your-secure-password --app seventaps-analytics
```

### 3. Sync Data

```bash
# Manual sync from Redis to Learning Locker
curl -X POST https://seventaps-analytics-5135b3a0701a.herokuapp.com/api/sync-learninglocker

# Check sync status
curl https://seventaps-analytics-5135b3a0701a.herokuapp.com/api/sync-status
```

## Usage

### 1. Access Learning Locker

**Local Development:**
- URL: http://localhost:8080
- Admin: http://localhost:8080/admin
- Credentials: admin@7taps.com / admin123

**Production:**
- URL: Your Learning Locker domain
- Admin: Your Learning Locker domain/admin
- Credentials: As configured

### 2. View Statements

1. **Login to Learning Locker admin**
2. **Navigate to "Statements" section**
3. **Browse statements by:**
   - Actor (user)
   - Verb (action)
   - Object (activity)
   - Timestamp
   - Custom filters

### 3. Export Data

1. **Select statements using filters**
2. **Choose export format:**
   - JSON
   - CSV
   - XML
3. **Download exported data**

### 4. Advanced Queries

Learning Locker supports complex xAPI queries:

```javascript
// Example: Find all completion statements for a specific user
{
  "actor": {
    "account": {
      "name": "user123"
    }
  },
  "verb": {
    "id": "http://adlnet.gov/expapi/verbs/completed"
  }
}
```

## API Endpoints

### Sync Endpoints

- `POST /api/sync-learninglocker` - Sync statements to Learning Locker
- `GET /api/sync-status` - Get sync status
- `GET /api/learninglocker-info` - Get Learning Locker info

### xAPI Endpoints

- `POST /statements` - Post xAPI statements (our custom LRS)
- `GET /statements` - Get xAPI statements
- `GET /about` - Get LRS information

## Monitoring

### Check Sync Status

```bash
curl https://seventaps-analytics-5135b3a0701a.herokuapp.com/api/sync-status
```

Response:
```json
{
  "status": "active",
  "learninglocker_sync": {
    "last_sync_time": "2025-01-05T20:30:00Z",
    "total_synced": 150,
    "learninglocker_url": "http://localhost:8080",
    "redis_url": "localhost:6379"
  },
  "message": "Learning Locker sync status retrieved"
}
```

### Health Checks

```bash
# Custom LRS health
curl https://seventaps-analytics-5135b3a0701a.herokuapp.com/health

# Learning Locker health
curl http://localhost:8080/health
```

## Troubleshooting

### Common Issues

1. **Learning Locker not starting**
   - Check database connection
   - Verify environment variables
   - Check logs: `docker-compose logs learninglocker`

2. **Sync not working**
   - Verify Learning Locker credentials
   - Check Redis connection
   - Review sync logs

3. **Data not appearing**
   - Run manual sync: `POST /api/sync-learninglocker`
   - Check statement format
   - Verify xAPI compliance

### Logs

```bash
# View Learning Locker logs
docker-compose logs learninglocker

# View sync service logs
docker-compose logs app
```

## Security

### Authentication

- **Learning Locker Admin**: Username/password
- **xAPI LRS**: Basic Authentication
- **API Endpoints**: Environment-based credentials

### Data Protection

- **Encrypted connections**: HTTPS in production
- **Secure credentials**: Environment variables
- **Access control**: Role-based permissions

## Performance

### Resource Usage

- **Learning Locker**: ~512MB RAM, 1 CPU
- **Sync Service**: Minimal overhead
- **Database**: Shared with existing system

### Optimization

- **Batch syncing**: Process multiple statements
- **Incremental sync**: Only new statements
- **Error handling**: Retry failed syncs

## Migration

### From Custom LRS Only

1. **Deploy Learning Locker**
2. **Configure sync service**
3. **Run initial sync**
4. **Verify data integrity**
5. **Switch team to Learning Locker UI**

### Benefits

- **No data loss**: All statements preserved
- **Gradual transition**: Use both systems
- **Rollback option**: Keep custom LRS

## Support

### Documentation

- **Learning Locker Docs**: https://docs.learninglocker.net/
- **xAPI Specification**: https://xapi.com/
- **ADL xAPI Test Suite**: https://github.com/adlnet/xapi-test-suite

### Community

- **Learning Locker Community**: https://community.learninglocker.net/
- **xAPI Community**: https://xapi.com/community/ 