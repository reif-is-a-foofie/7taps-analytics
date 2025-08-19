# Scripts Directory

This directory contains utility scripts for development, deployment, and maintenance.

## Available Scripts

### Database Management
- `heroku_deep_cleanup.py` - Deep cleanup of unused database tables
- `heroku_cleanup_tables.py` - Basic database table cleanup
- `cleanup_old_tables.py` - Legacy table cleanup (deprecated)

### Data Processing
- `verify_data_pipeline.py` - Verify data pipeline integrity
- `run_normalized_migration.py` - Run normalized schema migration
- `import_focus_group.py` - Import focus group data

### Testing & Development
- `test_csv_to_xapi.py` - Test CSV to xAPI conversion
- `xapi_test_client.py` - xAPI test client utilities
- `health_check.py` - System health check utilities

### Deployment
- `setup_heroku.sh` - Heroku deployment setup
- `generate_pem_keys.py` - Generate PEM keys for authentication

## Usage

Run scripts with Python from the project root:

```bash
python scripts/script_name.py [options]
```

## Development

When adding new scripts:
1. Use descriptive names with snake_case
2. Include proper error handling
3. Add logging for debugging
4. Document usage in this README
