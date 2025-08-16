"""
Migration API for 7taps Analytics.

This module provides API endpoints for triggering data migrations
and monitoring migration progress.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import asyncio

from app.migrate_flat_to_normalized import FlatToNormalizedMigrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class MigrationRequest(BaseModel):
    """Request model for migration operations."""
    force: bool = False
    batch_size: Optional[int] = None

class MigrationStatus(BaseModel):
    """Status model for migration operations."""
    status: str
    migrated_count: int
    error_count: int
    total_statements: int
    progress_percentage: float
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    message: str

class MigrationStats(BaseModel):
    """Statistics for migration operations."""
    total_flat_statements: int
    total_normalized_statements: int
    migration_needed: int
    last_migration_time: Optional[datetime] = None
    migration_status: str

# Global migration state
migration_state = {
    'is_running': False,
    'start_time': None,
    'end_time': None,
    'migrated_count': 0,
    'error_count': 0,
    'total_statements': 0
}

async def run_migration_background():
    """Background task to run migration."""
    global migration_state
    
    try:
        migration_state['is_running'] = True
        migration_state['start_time'] = datetime.utcnow()
        migration_state['migrated_count'] = 0
        migration_state['error_count'] = 0
        
        logger.info("Starting background migration...")
        
        # Run migration
        migrator = FlatToNormalizedMigrator()
        result = await migrator.run_migration()
        
        migration_state['migrated_count'] = result['migrated_count']
        migration_state['error_count'] = result['error_count']
        migration_state['end_time'] = datetime.utcnow()
        
        logger.info(f"Background migration completed: {result}")
        
    except Exception as e:
        logger.error(f"Error in background migration: {e}")
        migration_state['error_count'] += 1
    finally:
        migration_state['is_running'] = False

@router.post("/migration/trigger", response_model=MigrationStatus)
async def trigger_migration(request: MigrationRequest, background_tasks: BackgroundTasks):
    """Trigger data migration from flat to normalized tables."""
    try:
        if migration_state['is_running']:
            raise HTTPException(status_code=409, detail="Migration already in progress")
        # Pre-check schema validation
        migrator = FlatToNormalizedMigrator()
        if not await migrator.validate_schema():
            raise HTTPException(status_code=500, detail="Schema validation failed. Required tables missing.")
        # Get current stats
        flat_statements = await migrator.get_flat_statements()
        total_statements = len(flat_statements)
        migration_state['total_statements'] = total_statements
        if total_statements == 0:
            return MigrationStatus(
                status="completed",
                migrated_count=0,
                error_count=0,
                total_statements=0,
                progress_percentage=100.0,
                message="No statements to migrate"
            )
        # Start background migration
        background_tasks.add_task(run_migration_background)
        return MigrationStatus(
            status="started",
            migrated_count=0,
            error_count=0,
            total_statements=total_statements,
            progress_percentage=0.0,
            start_time=datetime.utcnow(),
            message=f"Migration started for {total_statements} statements"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering migration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/migration/status", response_model=MigrationStatus)
async def get_migration_status():
    """Get current migration status."""
    try:
        if not migration_state['is_running'] and migration_state['start_time'] is None:
            return MigrationStatus(
                status="idle",
                migrated_count=0,
                error_count=0,
                total_statements=0,
                progress_percentage=0.0,
                message="No migration in progress"
            )
        
        # Calculate progress
        progress = 0.0
        if migration_state['total_statements'] > 0:
            progress = (migration_state['migrated_count'] / migration_state['total_statements']) * 100.0
        
        # Determine status
        status = "running"
        message = f"Migration in progress: {migration_state['migrated_count']}/{migration_state['total_statements']} statements"
        
        if not migration_state['is_running'] and migration_state['end_time']:
            status = "completed"
            message = f"Migration completed: {migration_state['migrated_count']} statements migrated, {migration_state['error_count']} errors"
        
        return MigrationStatus(
            status=status,
            migrated_count=migration_state['migrated_count'],
            error_count=migration_state['error_count'],
            total_statements=migration_state['total_statements'],
            progress_percentage=progress,
            start_time=migration_state['start_time'],
            end_time=migration_state['end_time'],
            message=message
        )
        
    except Exception as e:
        logger.error(f"Error getting migration status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/migration/stats", response_model=MigrationStats)
async def get_migration_stats():
    """Get migration statistics."""
    try:
        migrator = FlatToNormalizedMigrator()
        
        # Get flat statements count
        flat_statements = await migrator.get_flat_statements()
        total_flat = len(flat_statements)
        
        # Get normalized statements count
        async with migrator.get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM statements_normalized")
                total_normalized = cursor.fetchone()[0]
        
        # Determine migration status
        migration_needed = total_flat
        migration_status = "up_to_date"
        
        if total_flat > 0:
            migration_status = "migration_needed"
        
        if migration_state['is_running']:
            migration_status = "migration_in_progress"
        
        return MigrationStats(
            total_flat_statements=total_flat,
            total_normalized_statements=total_normalized,
            migration_needed=migration_needed,
            last_migration_time=migration_state.get('end_time'),
            migration_status=migration_status
        )
        
    except Exception as e:
        logger.error(f"Error getting migration stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/migration/reset")
async def reset_migration_state():
    """Reset migration state (for testing/debugging)."""
    try:
        global migration_state
        migration_state = {
            'is_running': False,
            'start_time': None,
            'end_time': None,
            'migrated_count': 0,
            'error_count': 0,
            'total_statements': 0
        }
        
        return {"message": "Migration state reset successfully"}
        
    except Exception as e:
        logger.error(f"Error resetting migration state: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/migration/health")
async def migration_health_check():
    """Health check for migration system."""
    try:
        migrator = FlatToNormalizedMigrator()
        
        # Test database connection
        async with migrator.get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        
        # Check if tables exist
        async with migrator.get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('statements_flat', 'statements_normalized', 'actors', 'activities', 'verbs')
                """)
                tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ['statements_flat', 'statements_normalized', 'actors', 'activities', 'verbs']
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            return {
                "status": "unhealthy",
                "message": f"Missing required tables: {missing_tables}",
                "tables_found": tables
            }
        
        return {
            "status": "healthy",
            "message": "Migration system is ready",
            "tables_found": tables,
            "migration_state": migration_state
        }
        
    except Exception as e:
        logger.error(f"Error in migration health check: {e}")
        return {
            "status": "unhealthy",
            "message": f"Migration system error: {str(e)}"
        }
