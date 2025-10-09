# GCP UI Configuration Guide

## Environment Variables for Google Cloud Deployment

The UI components have been updated to work with Google Cloud by using environment variables instead of hardcoded URLs.

### Required Environment Variables

```bash
# API Base URL (leave empty for relative URLs)
API_BASE_URL=""

# Database Terminal URL (for SQLPad/Superset access)
DATABASE_TERMINAL_URL="https://your-sqlpad-instance.run.app"

# Learning Locker URL (if using Learning Locker)
LEARNINGLOCKER_URL="https://your-learninglocker-instance.run.app"

# Database Configuration
DATABASE_URL="postgresql://user:pass@host:port/db"
PGSSLMODE="require"

# Redis Configuration
REDIS_URL="redis://your-redis-instance:6379"

# Optional: Specific tool URLs
SQLPAD_URL="https://your-sqlpad-instance.run.app"
SUPERSET_URL="https://your-superset-instance.run.app"
USE_SQLPAD="true"
```

### Changes Made for GCP Compatibility

1. **Template URLs**: All hardcoded `localhost` and `herokuapp.com` URLs replaced with environment variables
2. **API Endpoints**: Changed from absolute URLs to relative URLs for better cloud deployment
3. **Database Terminal**: Configurable via `DATABASE_TERMINAL_URL` environment variable
4. **UI Modules**: All UI modules now use `API_BASE_URL` environment variable

### Template Context Helper

Added `get_template_context()` function in `main.py` that provides:
- `database_terminal_url`: From `DATABASE_TERMINAL_URL` env var
- `api_base_url`: From `API_BASE_URL` env var (empty for relative URLs)

### Files Updated

- `templates/base.html`: Database terminal links
- `templates/chat_interface.html`: API endpoint URLs
- `templates/api_docs_clean.html`: SQLPad links
- `app/main.py`: Template context helper
- `app/ui/bigquery_dashboard.py`: API base URL
- `app/ui/user_management.py`: API base URL
- `app/ui/statement_browser.py`: API base URL
- `app/ui/learninglocker_admin.py`: API base URL
- `app/ui/data_export.py`: API base URL
- `app/ui/admin.py`: Database terminal URLs

### Testing

To test the UI in GCP:

1. Set the environment variables in your Cloud Run service
2. Deploy the application
3. Verify all links work correctly
4. Test the chat interface and dashboard functionality

The UI will now work seamlessly in Google Cloud without hardcoded localhost or Heroku URLs.
