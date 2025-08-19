#!/usr/bin/env python3
"""
Cleanup Executor

This script executes the focused cleanup plan by moving files, deleting redundant files,
and creating missing documentation.
"""

import os
import sys
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CleanupExecutor:
    """Executes cleanup actions based on the focused cleanup plan."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        
    def execute_cleanup(self, dry_run: bool = True):
        """Execute the focused cleanup plan."""
        logger.info("🧹 Executing focused cleanup plan...")
        
        if dry_run:
            logger.info("🔍 DRY RUN MODE - No files will be modified")
        
        # File moves
        self._move_test_files(dry_run)
        
        # File deletions
        self._delete_redundant_files(dry_run)
        
        # Documentation updates
        self._create_missing_docs(dry_run)
        
        logger.info("✅ Cleanup execution completed!")
    
    def _move_test_files(self, dry_run: bool):
        """Move test files to the tests directory."""
        logger.info("📁 Moving test files...")
        
        test_files_to_move = [
            'scripts/test_csv_to_xapi.py'
        ]
        
        for file_path in test_files_to_move:
            source = self.project_root / file_path
            destination = self.project_root / 'tests' / Path(file_path).name
            
            if source.exists():
                if dry_run:
                    logger.info(f"  🔍 Would move: {file_path} → tests/{Path(file_path).name}")
                else:
                    try:
                        # Ensure tests directory exists
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Move the file
                        shutil.move(str(source), str(destination))
                        logger.info(f"  ✅ Moved: {file_path} → tests/{Path(file_path).name}")
                    except Exception as e:
                        logger.error(f"  ❌ Error moving {file_path}: {e}")
            else:
                logger.warning(f"  ⚠️  File not found: {file_path}")
    
    def _delete_redundant_files(self, dry_run: bool):
        """Delete redundant files from quarantine and other locations."""
        logger.info("🗑️  Deleting redundant files...")
        
        files_to_delete = [
            # Old cleanup script
            'scripts/cleanup_old_tables.py',
            
            # Redundant reports
            'quarantine/redundant_reports/xapi_to_normalized_mapping_test.json',
            'quarantine/redundant_reports/corrected_field_mapping.json',
            'quarantine/redundant_reports/real_xapi_field_mapping.json',
            'quarantine/redundant_reports/xapi_csv_field_mapping.json',
            'quarantine/redundant_reports/data_gaps_analysis.json',
            'quarantine/redundant_reports/concrete_field_mapping_examples.json',
            'quarantine/redundant_reports/backend_agent_workflow_map.json',
            
            # Redundant requirements
            'quarantine/redundant_requirements/b07_xapi_ingestion.json',
            'quarantine/redundant_requirements/b02_streaming_etl.json',
            'quarantine/redundant_requirements/b03_incremental_etl.json',
            'quarantine/redundant_requirements/b09_performance_optimization.json',
            'quarantine/redundant_requirements/b06_ui_integration.json',
            'quarantine/redundant_requirements/b08_deployment_testing.json',
            'quarantine/redundant_requirements/b05_nlp_query.json',
            'quarantine/redundant_requirements/b10_7taps_api_integration.json',
        ]
        
        for file_path in files_to_delete:
            full_path = self.project_root / file_path
            
            if full_path.exists():
                if dry_run:
                    logger.info(f"  🔍 Would delete: {file_path}")
                else:
                    try:
                        full_path.unlink()
                        logger.info(f"  ✅ Deleted: {file_path}")
                    except Exception as e:
                        logger.error(f"  ❌ Error deleting {file_path}: {e}")
            else:
                logger.warning(f"  ⚠️  File not found: {file_path}")
    
    def _create_missing_docs(self, dry_run: bool):
        """Create missing README files in key directories."""
        logger.info("📚 Creating missing documentation...")
        
        docs_to_create = [
            ('app/README.md', self._get_app_readme_content()),
            ('scripts/README.md', self._get_scripts_readme_content()),
            ('tests/README.md', self._get_tests_readme_content()),
            ('docs/README.md', self._get_docs_readme_content()),
        ]
        
        for file_path, content in docs_to_create:
            full_path = self.project_root / file_path
            
            if dry_run:
                logger.info(f"  🔍 Would create: {file_path}")
            else:
                try:
                    # Ensure directory exists
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Create the file
                    with open(full_path, 'w') as f:
                        f.write(content)
                    logger.info(f"  ✅ Created: {file_path}")
                except Exception as e:
                    logger.error(f"  ❌ Error creating {file_path}: {e}")
    
    def _get_app_readme_content(self) -> str:
        """Get content for app/README.md."""
        return """# App Directory

This directory contains the main application code for the 7taps Analytics platform.

## Structure

- `api/` - FastAPI endpoints and API routes
- `ui/` - User interface components and templates
- `etl/` - ETL (Extract, Transform, Load) processing modules
- `config.py` - Application configuration
- `data_normalization.py` - Data normalization utilities

## Key Components

- **API Layer**: RESTful endpoints for data access and analytics
- **ETL Pipeline**: Data processing and transformation workflows
- **UI Components**: Web interface for data visualization and management

## Usage

The app is designed to process xAPI learning data and provide analytics insights for 7taps learning platform.
"""
    
    def _get_scripts_readme_content(self) -> str:
        """Get content for scripts/README.md."""
        return """# Scripts Directory

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
"""
    
    def _get_tests_readme_content(self) -> str:
        """Get content for tests/README.md."""
        return """# Tests Directory

This directory contains test files for the 7taps Analytics platform.

## Test Structure

- `test_*.py` - Individual test modules
- `test_csv_to_xapi.py` - CSV to xAPI conversion tests

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_file.py

# Run with coverage
pytest --cov=app tests/

# Run with verbose output
pytest -v
```

## Test Conventions

- Test files should be named `test_*.py`
- Test functions should be named `test_*`
- Use descriptive test names that explain what is being tested
- Include both unit tests and integration tests
- Mock external dependencies when appropriate

## Coverage

Maintain good test coverage for critical components:
- API endpoints
- ETL processes
- Data validation
- Database operations
"""
    
    def _get_docs_readme_content(self) -> str:
        """Get content for docs/README.md."""
        return """# Documentation Directory

This directory contains project documentation and guides.

## Available Documentation

- `AGENTS.md` - Agent system documentation
- `DEPLOYMENT.md` - Deployment instructions
- `LEARNINGLOCKER_AGENT_GUIDE.md` - LearningLocker integration guide

## Documentation Standards

- Use Markdown format
- Include code examples where appropriate
- Keep documentation up to date with code changes
- Use clear, concise language
- Include diagrams when helpful

## Contributing

When updating documentation:
1. Update this README if adding new docs
2. Ensure links are working
3. Test code examples
4. Review for clarity and completeness
"""

def main():
    """Main function to execute cleanup."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Execute focused project cleanup')
    parser.add_argument('--dry-run', action='store_true', default=True, help='Show what would be done without making changes')
    parser.add_argument('--execute', action='store_true', help='Actually execute the cleanup (overrides --dry-run)')
    
    args = parser.parse_args()
    
    # Determine if this is a dry run
    dry_run = not args.execute
    
    try:
        executor = CleanupExecutor()
        executor.execute_cleanup(dry_run=dry_run)
        
        if dry_run:
            logger.info("\n🔍 This was a dry run. Use --execute to actually perform the cleanup.")
        else:
            logger.info("\n✅ Cleanup executed successfully!")
            
    except Exception as e:
        logger.error(f"❌ Error during cleanup execution: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

