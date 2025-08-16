#!/usr/bin/env python3
"""
Startup script for 7taps Analytics ETL

This script provides detailed logging and error handling during application startup
to help debug deployment issues.
"""

import os
import sys
import traceback
import logging
from pathlib import Path

# Configure basic logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger("startup")

def check_environment():
    """Check environment variables and configuration."""
    logger.info("Checking environment configuration...")
    
    # Check required environment variables
    required_vars = []
    optional_vars = ["DATABASE_URL", "REDIS_URL", "ENVIRONMENT", "DEBUG"]
    
    for var in required_vars:
        if not os.getenv(var):
            logger.error(f"Required environment variable {var} is not set")
            return False
    
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            logger.info(f"Environment variable {var} is set: {value[:20]}..." if len(str(value)) > 20 else value)
        else:
            logger.warning(f"Optional environment variable {var} is not set")
    
    return True

def check_dependencies():
    """Check if all required Python packages are available."""
    logger.info("Checking Python dependencies...")
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "psycopg2",
        "redis",
        "pydantic",
        "structlog"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"✓ {package} is available")
        except ImportError:
            logger.error(f"✗ {package} is missing")
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"Missing packages: {', '.join(missing_packages)}")
        return False
    
    return True

def check_files():
    """Check if required files exist."""
    logger.info("Checking required files...")
    
    required_files = [
        "app/main.py",
        "app/config.py",
        "requirements.txt"
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if Path(file_path).exists():
            logger.info(f"✓ {file_path} exists")
        else:
            logger.error(f"✗ {file_path} is missing")
            missing_files.append(file_path)
    
    if missing_files:
        logger.error(f"Missing files: {', '.join(missing_files)}")
        return False
    
    return True

def test_imports():
    """Test importing key modules."""
    logger.info("Testing module imports...")
    
    modules_to_test = [
        "app.main",
        "app.config",
        "app.logging_config"
    ]
    
    failed_imports = []
    
    for module in modules_to_test:
        try:
            __import__(module)
            logger.info(f"✓ Successfully imported {module}")
        except Exception as e:
            logger.error(f"✗ Failed to import {module}: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        logger.error(f"Failed imports: {', '.join(failed_imports)}")
        return False
    
    return True

def main():
    """Main startup function."""
    logger.info("=" * 60)
    logger.info("7taps Analytics ETL - Startup Diagnostics")
    logger.info("=" * 60)
    
    # Check current working directory
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Python executable: {sys.executable}")
    
    # Run checks
    checks = [
        ("Environment", check_environment),
        ("Dependencies", check_dependencies),
        ("Files", check_files),
        ("Imports", test_imports)
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        logger.info(f"\n--- {check_name} Check ---")
        try:
            if not check_func():
                all_passed = False
        except Exception as e:
            logger.error(f"Error during {check_name} check: {e}")
            logger.error(traceback.format_exc())
            all_passed = False
    
    logger.info("\n" + "=" * 60)
    if all_passed:
        logger.info("✓ All startup checks passed!")
        logger.info("Starting FastAPI application...")
        
        # Import and start the app
        try:
            from app.main import app
            import uvicorn
            
            port = int(os.getenv("PORT", 8000))
            logger.info(f"Starting server on port {port}")
            
            uvicorn.run(
                app,
                host="0.0.0.0",
                port=port,
                log_level="info"
            )
            
        except Exception as e:
            logger.error(f"Failed to start application: {e}")
            logger.error(traceback.format_exc())
            sys.exit(1)
    else:
        logger.error("✗ Some startup checks failed!")
        logger.error("Please fix the issues above before starting the application.")
        sys.exit(1)

if __name__ == "__main__":
    main()
