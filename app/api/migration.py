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

from app.migrate_flat_to_normalized import migrate_flat_to_normalized, FlatToNormalizedMigrator
from app.config import settings
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import asynccontextmanager

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
        result = await migrate_flat_to_normalized()
        
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
        
        # Get current stats
        migrator = FlatToNormalizedMigrator()
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

@router.post("/migration/normalized-schema")
async def run_normalized_schema_migration():
    """Run the normalized schema migration and ETL processes."""
    try:
        logger.info("🚀 Starting normalized schema migration...")
        
        # Get database connection
        conn = psycopg2.connect(settings.DATABASE_URL)
        
        # Step 1: Create normalized schema
        logger.info("Creating normalized schema...")
        schema_sql = """
        -- Create normalized schema for 7taps analytics
        -- This replaces the current flat structure with proper relational tables

        -- Enable UUID extension
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

        -- Drop existing tables if they exist (for clean migration)
        DROP TABLE IF EXISTS context_extensions CASCADE;
        DROP TABLE IF EXISTS results CASCADE;
        DROP TABLE IF EXISTS statements CASCADE;

        -- 1. Actors table - normalized user data (create if not exists)
        CREATE TABLE IF NOT EXISTS actors (
            actor_id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255),
            email VARCHAR(255),
            account_name VARCHAR(255),
            account_homepage VARCHAR(500),
            source VARCHAR(50) NOT NULL, -- 'csv' or 'xapi'
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- 2. Activities table - learning activities/cards (create if not exists)
        CREATE TABLE IF NOT EXISTS activities (
            activity_id VARCHAR(500) PRIMARY KEY,
            name TEXT,
            type VARCHAR(100), -- 'card', 'lesson', 'quiz', etc.
            description TEXT,
            lesson_number INTEGER,
            global_q_number INTEGER,
            pdf_page INTEGER,
            source VARCHAR(50) NOT NULL, -- 'csv' or 'xapi'
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- 3. Statements table - core xAPI statements
        CREATE TABLE statements (
            statement_id VARCHAR(255) PRIMARY KEY,
            actor_id VARCHAR(255) REFERENCES actors(actor_id),
            activity_id VARCHAR(500) REFERENCES activities(activity_id),
            verb_id VARCHAR(255) NOT NULL,
            timestamp TIMESTAMPTZ NOT NULL,
            version VARCHAR(50),
            authority_actor_id VARCHAR(255),
            stored TIMESTAMPTZ,
            source VARCHAR(50) NOT NULL, -- 'csv' or 'xapi'
            raw_json JSONB, -- for audit/debug
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- 4. Results table - statement results and responses
        CREATE TABLE results (
            statement_id VARCHAR(255) PRIMARY KEY REFERENCES statements(statement_id),
            success BOOLEAN,
            completion BOOLEAN,
            score_raw DECIMAL(10,2),
            score_scaled DECIMAL(5,4),
            score_min DECIMAL(10,2),
            score_max DECIMAL(10,2),
            duration VARCHAR(100),
            response TEXT, -- free-text responses from focus group
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- 5. Context extensions table - flexible metadata
        CREATE TABLE context_extensions (
            id SERIAL PRIMARY KEY,
            statement_id VARCHAR(255) REFERENCES statements(statement_id),
            extension_key VARCHAR(255) NOT NULL,
            extension_value TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- Create indexes for performance (create if not exists)
        CREATE INDEX IF NOT EXISTS idx_actors_email ON actors(email);
        CREATE INDEX IF NOT EXISTS idx_actors_source ON actors(source);
        CREATE INDEX IF NOT EXISTS idx_statements_actor_id ON statements(actor_id);
        CREATE INDEX IF NOT EXISTS idx_statements_activity_id ON statements(activity_id);
        CREATE INDEX IF NOT EXISTS idx_statements_verb_id ON statements(verb_id);
        CREATE INDEX IF NOT EXISTS idx_statements_timestamp ON statements(timestamp);
        CREATE INDEX IF NOT EXISTS idx_statements_source ON statements(source);
        CREATE INDEX IF NOT EXISTS idx_context_extensions_statement_id ON context_extensions(statement_id);
        CREATE INDEX IF NOT EXISTS idx_context_extensions_key ON context_extensions(extension_key);

        -- Create updated_at trigger for actors table
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';

        CREATE TRIGGER update_actors_updated_at BEFORE UPDATE ON actors
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

        -- Create function to normalize actor_id
        CREATE OR REPLACE FUNCTION normalize_actor_id(
            p_email VARCHAR(255),
            p_account_name VARCHAR(255),
            p_name VARCHAR(255)
        ) RETURNS VARCHAR(255) AS $$
        BEGIN
            -- Clean and normalize email
            IF p_email IS NOT NULL AND p_email != '' THEN
                -- Remove 'mailto:' prefix and convert to lowercase
                RETURN LOWER(REPLACE(p_email, 'mailto:', ''));
            END IF;
            
            -- Use account name if available
            IF p_account_name IS NOT NULL AND p_account_name != '' THEN
                RETURN LOWER(p_account_name);
            END IF;
            
            -- Fallback to name
            IF p_name IS NOT NULL AND p_name != '' THEN
                RETURN LOWER(p_name);
            END IF;
            
            -- Final fallback
            RETURN 'unknown_actor';
        END;
        $$ LANGUAGE plpgsql;
        """
        
        cursor = conn.cursor()
        cursor.execute(schema_sql)
        
        # Add missing columns to existing tables if they don't exist
        try:
            cursor.execute("ALTER TABLE actors ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'xapi'")
            cursor.execute("ALTER TABLE activities ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'xapi'")
            cursor.execute("ALTER TABLE activities ADD COLUMN IF NOT EXISTS lesson_number INTEGER")
            cursor.execute("ALTER TABLE activities ADD COLUMN IF NOT EXISTS global_q_number INTEGER")
            cursor.execute("ALTER TABLE activities ADD COLUMN IF NOT EXISTS pdf_page INTEGER")
            conn.commit()
        except Exception as e:
            logger.warning(f"Some columns may already exist: {e}")
        
        logger.info("✅ Created normalized schema")
        
        # Step 2: Migrate xAPI data
        logger.info("Migrating xAPI data...")
        xapi_sql = """
        -- Migrate actors from existing data
        INSERT INTO actors (actor_id, name, email, account_name, account_homepage, source)
        SELECT DISTINCT
            normalize_actor_id(
                CASE 
                    WHEN raw_statement->'actor'->>'mbox' IS NOT NULL 
                    THEN raw_statement->'actor'->>'mbox'
                    ELSE NULL
                END,
                CASE 
                    WHEN raw_statement->'actor'->'account'->>'name' IS NOT NULL 
                    THEN raw_statement->'actor'->'account'->>'name'
                    ELSE NULL
                END,
                CASE 
                    WHEN raw_statement->'actor'->>'name' IS NOT NULL 
                    THEN raw_statement->'actor'->>'name'
                    ELSE NULL
                END
            ) as actor_id,
            raw_statement->'actor'->>'name' as name,
            CASE 
                WHEN raw_statement->'actor'->>'mbox' IS NOT NULL 
                THEN LOWER(REPLACE(raw_statement->'actor'->>'mbox', 'mailto:', ''))
                ELSE NULL
            END as email,
            raw_statement->'actor'->'account'->>'name' as account_name,
            raw_statement->'actor'->'account'->>'homePage' as account_homepage,
            'xapi' as source
        FROM statements_flat
        WHERE raw_statement IS NOT NULL
        ON CONFLICT (actor_id) DO NOTHING;

        -- Migrate activities from existing data
        INSERT INTO activities (activity_id, name, type, description, source)
        SELECT DISTINCT
            raw_statement->'object'->>'id' as activity_id,
            CASE 
                WHEN raw_statement->'object'->'definition'->'name'->>'en-US' IS NOT NULL 
                THEN raw_statement->'object'->'definition'->'name'->>'en-US'
                ELSE raw_statement->'object'->>'id'
            END as name,
            raw_statement->'object'->>'objectType' as type,
            CASE 
                WHEN raw_statement->'object'->'definition'->'description'->>'en-US' IS NOT NULL 
                THEN raw_statement->'object'->'definition'->'description'->>'en-US'
                ELSE NULL
            END as description,
            'xapi' as source
        FROM statements_flat
        WHERE raw_statement IS NOT NULL
        ON CONFLICT (activity_id) DO NOTHING;

        -- Migrate statements from existing data
        INSERT INTO statements (
            statement_id, 
            actor_id, 
            activity_id, 
            verb_id, 
            timestamp, 
            version, 
            authority_actor_id, 
            stored, 
            source, 
            raw_json
        )
        SELECT 
            raw_statement->>'id' as statement_id,
            normalize_actor_id(
                CASE 
                    WHEN raw_statement->'actor'->>'mbox' IS NOT NULL 
                    THEN raw_statement->'actor'->>'mbox'
                    ELSE NULL
                END,
                CASE 
                    WHEN raw_statement->'actor'->'account'->>'name' IS NOT NULL 
                    THEN raw_statement->'actor'->'account'->>'name'
                    ELSE NULL
                END,
                CASE 
                    WHEN raw_statement->'actor'->>'name' IS NOT NULL 
                    THEN raw_statement->'actor'->>'name'
                    ELSE NULL
                END
            ) as actor_id,
            raw_statement->'object'->>'id' as activity_id,
            raw_statement->'verb'->>'id' as verb_id,
            (raw_statement->>'timestamp')::timestamptz as timestamp,
            raw_statement->>'version' as version,
            CASE 
                WHEN raw_statement->'authority'->'account'->>'name' IS NOT NULL 
                THEN raw_statement->'authority'->'account'->>'name'
                ELSE NULL
            END as authority_actor_id,
            (raw_statement->>'stored')::timestamptz as stored,
            'xapi' as source,
            raw_statement as raw_json
        FROM statements_flat
        WHERE raw_statement IS NOT NULL
        ON CONFLICT (statement_id) DO NOTHING;

        -- Migrate results from existing data
        INSERT INTO results (
            statement_id,
            success,
            completion,
            score_raw,
            score_scaled,
            score_min,
            score_max,
            duration
        )
        SELECT 
            raw_statement->>'id' as statement_id,
            (raw_statement->'result'->>'success')::boolean as success,
            (raw_statement->'result'->>'completion')::boolean as completion,
            (raw_statement->'result'->'score'->>'raw')::decimal as score_raw,
            (raw_statement->'result'->'score'->>'scaled')::decimal as score_scaled,
            (raw_statement->'result'->'score'->>'min')::decimal as score_min,
            (raw_statement->'result'->'score'->>'max')::decimal as score_max,
            raw_statement->'result'->>'duration' as duration
        FROM statements_flat
        WHERE raw_statement->'result' IS NOT NULL
        ON CONFLICT (statement_id) DO NOTHING;
        """
        
        cursor.execute(xapi_sql)
        conn.commit()
        logger.info("✅ Migrated xAPI data")
        
        # Step 3: Create views
        logger.info("Creating views...")
        views_sql = """
        -- Create views for easy querying
        CREATE OR REPLACE VIEW vw_focus_group_responses AS
        SELECT 
            s.statement_id,
            a.name as learner_name,
            a.email as learner_email,
            act.name as activity_name,
            act.type as activity_type,
            act.lesson_number,
            act.global_q_number,
            s.verb_id,
            s.timestamp,
            r.response,
            r.success,
            r.completion
        FROM statements s
        JOIN actors a ON s.actor_id = a.actor_id
        JOIN activities act ON s.activity_id = act.activity_id
        LEFT JOIN results r ON s.statement_id = r.statement_id
        WHERE s.source = 'csv'
        ORDER BY s.timestamp DESC;

        CREATE OR REPLACE VIEW vw_user_progress AS
        SELECT 
            a.actor_id,
            a.name as learner_name,
            a.email as learner_email,
            COUNT(s.statement_id) as total_statements,
            COUNT(DISTINCT s.activity_id) as unique_activities,
            COUNT(CASE WHEN r.completion = true THEN 1 END) as completed_activities,
            MIN(s.timestamp) as first_activity,
            MAX(s.timestamp) as last_activity,
            a.source
        FROM actors a
        LEFT JOIN statements s ON a.actor_id = s.actor_id
        LEFT JOIN results r ON s.statement_id = r.statement_id
        GROUP BY a.actor_id, a.name, a.email, a.source
        ORDER BY total_statements DESC;
        """
        
        cursor.execute(views_sql)
        conn.commit()
        logger.info("✅ Created views")
        
        # Step 4: Verify migration
        logger.info("Verifying migration...")
        
        # Get counts
        cursor.execute("SELECT COUNT(*) as count FROM statements")
        result = cursor.fetchone()
        statement_count = result[0]
        
        cursor.execute("SELECT COUNT(*) as count FROM actors")
        result = cursor.fetchone()
        actor_count = result[0]
        
        cursor.execute("SELECT COUNT(*) as count FROM activities")
        result = cursor.fetchone()
        activity_count = result[0]
        
        cursor.execute("SELECT source, COUNT(*) as count FROM statements GROUP BY source")
        sources = cursor.fetchall()
        
        logger.info(f"📊 Migration results:")
        logger.info(f"   Statements: {statement_count}")
        logger.info(f"   Actors: {actor_count}")
        logger.info(f"   Activities: {activity_count}")
        for source in sources:
            logger.info(f"   {source[0]}: {source[1]} statements")
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "message": "Normalized schema migration completed successfully",
            "results": {
                "statements": statement_count,
                "actors": actor_count,
                "activities": activity_count,
                "sources": [{"source": s[0], "count": s[1]} for s in sources]
            }
        }
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")

@router.post("/migration/normalized-schema-simple")
async def run_normalized_schema_migration_simple():
    """Run a simple normalized schema migration - just create new tables."""
    try:
        logger.info("🚀 Starting simple normalized schema migration...")
        
        # Get database connection
        conn = psycopg2.connect(settings.DATABASE_URL)
        cursor = conn.cursor()
        
        # Step 1: Create new normalized tables only
        logger.info("Creating new normalized tables...")
        schema_sql = """
        -- Enable UUID extension
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

        -- Create new normalized tables (don't touch existing ones)
        CREATE TABLE IF NOT EXISTS statements_new (
            statement_id VARCHAR(255) PRIMARY KEY,
            actor_id VARCHAR(255),
            activity_id VARCHAR(500),
            verb_id VARCHAR(255) NOT NULL,
            timestamp TIMESTAMPTZ NOT NULL,
            version VARCHAR(50),
            authority_actor_id VARCHAR(255),
            stored TIMESTAMPTZ,
            source VARCHAR(50) NOT NULL, -- 'csv' or 'xapi'
            raw_json JSONB, -- for audit/debug
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS results_new (
            statement_id VARCHAR(255) PRIMARY KEY,
            success BOOLEAN,
            completion BOOLEAN,
            score_raw DECIMAL(10,2),
            score_scaled DECIMAL(5,4),
            score_min DECIMAL(10,2),
            score_max DECIMAL(10,2),
            duration VARCHAR(100),
            response TEXT, -- free-text responses from focus group
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS context_extensions_new (
            id SERIAL PRIMARY KEY,
            statement_id VARCHAR(255),
            extension_key VARCHAR(255) NOT NULL,
            extension_value TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_statements_new_actor_id ON statements_new(actor_id);
        CREATE INDEX IF NOT EXISTS idx_statements_new_activity_id ON statements_new(activity_id);
        CREATE INDEX IF NOT EXISTS idx_statements_new_verb_id ON statements_new(verb_id);
        CREATE INDEX IF NOT EXISTS idx_statements_new_timestamp ON statements_new(timestamp);
        CREATE INDEX IF NOT EXISTS idx_statements_new_source ON statements_new(source);
        CREATE INDEX IF NOT EXISTS idx_context_extensions_new_statement_id ON context_extensions_new(statement_id);
        CREATE INDEX IF NOT EXISTS idx_context_extensions_new_key ON context_extensions_new(extension_key);

        -- Create function to normalize actor_id
        CREATE OR REPLACE FUNCTION normalize_actor_id(
            p_email VARCHAR(255),
            p_account_name VARCHAR(255),
            p_name VARCHAR(255)
        ) RETURNS VARCHAR(255) AS $$
        BEGIN
            -- Clean and normalize email
            IF p_email IS NOT NULL AND p_email != '' THEN
                -- Remove 'mailto:' prefix and convert to lowercase
                RETURN LOWER(REPLACE(p_email, 'mailto:', ''));
            END IF;
            
            -- Use account name if available
            IF p_account_name IS NOT NULL AND p_account_name != '' THEN
                RETURN LOWER(p_account_name);
            END IF;
            
            -- Fallback to name
            IF p_name IS NOT NULL AND p_name != '' THEN
                RETURN LOWER(p_name);
            END IF;
            
            -- Final fallback
            RETURN 'unknown_actor';
        END;
        $$ LANGUAGE plpgsql;
        """
        
        cursor.execute(schema_sql)
        conn.commit()
        logger.info("✅ Created new normalized tables")
        
        # Step 2: Create views
        logger.info("Creating views...")
        views_sql = """
        -- Create views for easy querying
        CREATE OR REPLACE VIEW vw_focus_group_responses AS
        SELECT 
            s.statement_id,
            a.name as learner_name,
            a.email as learner_email,
            act.name as activity_name,
            act.activity_type as activity_type,
            s.verb_id,
            s.timestamp,
            r.response,
            r.success,
            r.completion
        FROM statements_new s
        LEFT JOIN actors a ON s.actor_id = a.actor_id
        LEFT JOIN activities act ON s.activity_id = act.activity_id
        LEFT JOIN results_new r ON s.statement_id = r.statement_id
        WHERE s.source = 'csv'
        ORDER BY s.timestamp DESC;

        CREATE OR REPLACE VIEW vw_user_progress AS
        SELECT 
            a.actor_id,
            a.name as learner_name,
            a.email as learner_email,
            COUNT(s.statement_id) as total_statements,
            COUNT(DISTINCT s.activity_id) as unique_activities,
            COUNT(CASE WHEN r.completion = true THEN 1 END) as completed_activities,
            MIN(s.timestamp) as first_activity,
            MAX(s.timestamp) as last_activity,
            'mixed' as source
        FROM actors a
        LEFT JOIN statements_new s ON a.actor_id = s.actor_id
        LEFT JOIN results_new r ON s.statement_id = r.statement_id
        GROUP BY a.actor_id, a.name, a.email
        ORDER BY total_statements DESC;
        """
        
        cursor.execute(views_sql)
        conn.commit()
        logger.info("✅ Created views")
        
        # Step 3: Verify migration
        logger.info("Verifying migration...")
        
        # Get counts
        cursor.execute("SELECT COUNT(*) as count FROM statements_new")
        result = cursor.fetchone()
        statement_count = result[0]
        
        cursor.execute("SELECT COUNT(*) as count FROM results_new")
        result = cursor.fetchone()
        result_count = result[0]
        
        cursor.execute("SELECT COUNT(*) as count FROM context_extensions_new")
        result = cursor.fetchone()
        extension_count = result[0]
        
        logger.info(f"📊 Migration results:")
        logger.info(f"   New statements table: {statement_count} records")
        logger.info(f"   New results table: {result_count} records")
        logger.info(f"   New context_extensions table: {extension_count} records")
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "message": "Simple normalized schema migration completed successfully",
            "results": {
                "statements_new": statement_count,
                "results_new": result_count,
                "context_extensions_new": extension_count
            }
        }
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")

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
