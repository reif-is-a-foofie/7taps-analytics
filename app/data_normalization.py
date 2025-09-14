"""
Data Normalization Module for 7taps xAPI Analytics.

This module provides comprehensive data flattening and normalization for xAPI statements,
creating structured tables for analytics and reporting.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataNormalizer:
    """Comprehensive data normalizer for xAPI statements."""
    
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        self.db_pool = None
        if self.database_url:
            dsn = self.database_url.replace('postgres://', 'postgresql://', 1) if self.database_url.startswith('postgres://') else self.database_url
            sslmode = os.getenv('PGSSLMODE', 'require')
            # Connection pooling for performance
            self.db_pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=dsn,
                sslmode=sslmode
            )
        
        # Performance tracking
        self.normalized_count = 0
        self.error_count = 0
        
    @asynccontextmanager
    async def get_db_connection(self):
        """Get database connection from pool with automatic cleanup."""
        if not self.db_pool:
            raise RuntimeError("Database pool is not configured; set DATABASE_URL")
        conn = self.db_pool.getconn()
        try:
            yield conn
        finally:
            self.db_pool.putconn(conn)
    
    async def create_normalized_tables(self):
        """Create normalized tables for analytics."""
        
        tables = {
            'actors': """
                CREATE TABLE IF NOT EXISTS actors (
                    actor_id VARCHAR(255) PRIMARY KEY,
                    actor_type VARCHAR(50) NOT NULL,
                    name VARCHAR(500),
                    email VARCHAR(255),
                    account_name VARCHAR(255),
                    account_homepage VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            
            'activities': """
                CREATE TABLE IF NOT EXISTS activities (
                    activity_id VARCHAR(500) PRIMARY KEY,
                    activity_type VARCHAR(100),
                    name VARCHAR(500),
                    description TEXT,
                    interaction_type VARCHAR(100),
                    correct_responses_pattern TEXT,
                    choices JSONB,
                    scale JSONB,
                    source JSONB,
                    target JSONB,
                    steps JSONB,
                    extensions JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            
            'verbs': """
                CREATE TABLE IF NOT EXISTS verbs (
                    verb_id VARCHAR(255) PRIMARY KEY,
                    display_name VARCHAR(500),
                    language VARCHAR(10) DEFAULT 'en-US',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            
            'statements_normalized': """
                CREATE TABLE IF NOT EXISTS statements_normalized (
                    statement_id VARCHAR(255) PRIMARY KEY,
                    actor_id VARCHAR(255) REFERENCES actors(actor_id),
                    verb_id VARCHAR(255) REFERENCES verbs(verb_id),
                    activity_id VARCHAR(500) REFERENCES activities(activity_id),
                    timestamp TIMESTAMP,
                    stored TIMESTAMP,
                    authority_actor_id VARCHAR(255) REFERENCES actors(actor_id),
                    version VARCHAR(20),
                    result_success BOOLEAN,
                    result_completion BOOLEAN,
                    result_duration VARCHAR(100),
                    result_score_scaled DECIMAL(5,4),
                    result_score_raw DECIMAL(10,2),
                    result_score_min DECIMAL(10,2),
                    result_score_max DECIMAL(10,2),
                    context_registration VARCHAR(255),
                    context_platform VARCHAR(255),
                    context_language VARCHAR(10),
                    context_statement_id VARCHAR(255),
                    context_extensions JSONB,
                    attachments JSONB,
                    raw_statement JSONB,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    -- Cohort and learner analytics fields
                    cohort_id VARCHAR(100),
                    cohort_name VARCHAR(255),
                    cohort_type VARCHAR(100),
                    learner_email VARCHAR(255),
                    learner_phone VARCHAR(20),
                    learner_group VARCHAR(100),
                    course_progress TEXT,
                    -- Additional fields for flexible data storage
                    additional_field_1 TEXT,
                    additional_field_2 TEXT,
                    additional_field_3 TEXT,
                    additional_field_4 TEXT,
                    additional_field_5 TEXT,
                    additional_field_6 TEXT,
                    additional_field_7 TEXT,
                    additional_field_8 TEXT,
                    additional_field_9 TEXT,
                    additional_field_10 TEXT
                )
            """,
            
            'statements_normalized_indexes': """
                CREATE INDEX IF NOT EXISTS idx_statements_timestamp ON statements_normalized (timestamp);
                CREATE INDEX IF NOT EXISTS idx_statements_actor_verb ON statements_normalized (actor_id, verb_id);
                CREATE INDEX IF NOT EXISTS idx_statements_activity ON statements_normalized (activity_id);
                -- Cohort analytics indexes
                CREATE INDEX IF NOT EXISTS idx_statements_cohort_id ON statements_normalized (cohort_id);
                CREATE INDEX IF NOT EXISTS idx_statements_cohort_name ON statements_normalized (cohort_name);
                CREATE INDEX IF NOT EXISTS idx_statements_cohort_type ON statements_normalized (cohort_type);
                CREATE INDEX IF NOT EXISTS idx_statements_learner_group ON statements_normalized (learner_group);
                CREATE INDEX IF NOT EXISTS idx_statements_learner_email ON statements_normalized (learner_email);
                -- Composite indexes for common cohort queries
                CREATE INDEX IF NOT EXISTS idx_statements_cohort_activity ON statements_normalized (cohort_id, activity_id);
                CREATE INDEX IF NOT EXISTS idx_statements_cohort_timestamp ON statements_normalized (cohort_id, timestamp);
                CREATE INDEX IF NOT EXISTS idx_statements_group_activity ON statements_normalized (learner_group, activity_id);
            """,
            
            'sessions': """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id VARCHAR(255) PRIMARY KEY,
                    actor_id VARCHAR(255) REFERENCES actors(actor_id),
                    registration VARCHAR(255),
                    platform VARCHAR(255),
                    language VARCHAR(10),
                    started_at TIMESTAMP,
                    ended_at TIMESTAMP,
                    duration_seconds INTEGER,
                    statement_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            
            'cohorts': """
                CREATE TABLE IF NOT EXISTS cohorts (
                    cohort_id VARCHAR(100) PRIMARY KEY,
                    cohort_name VARCHAR(255) NOT NULL,
                    cohort_type VARCHAR(100) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB
                )
            """,
            
            'cohort_members': """
                CREATE TABLE IF NOT EXISTS cohort_members (
                    cohort_id VARCHAR(100) REFERENCES cohorts(cohort_id),
                    actor_id VARCHAR(255) REFERENCES actors(actor_id),
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    role VARCHAR(50) DEFAULT 'member',
                    metadata JSONB,
                    PRIMARY KEY (cohort_id, actor_id)
                )
            """,
            
            'learning_paths': """
                CREATE TABLE IF NOT EXISTS learning_paths (
                    path_id SERIAL PRIMARY KEY,
                    actor_id VARCHAR(255) REFERENCES actors(actor_id),
                    session_id VARCHAR(255) REFERENCES sessions(session_id),
                    activity_sequence JSONB,
                    total_activities INTEGER,
                    completed_activities INTEGER,
                    total_duration_seconds INTEGER,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
        }
        
        try:
            async with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    for table_name, create_sql in tables.items():
                        cursor.execute(create_sql)
                        logger.info(f"Created/verified table: {table_name}")
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"Error creating normalized tables: {e}")
            raise
    
    def extract_actor_data(self, actor: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize actor data."""
        actor_data = {
            'actor_id': None,
            'actor_type': actor.get('objectType', 'Agent'),
            'name': actor.get('name'),
            'email': None,
            'account_name': None,
            'account_homepage': None
        }
        
        # Extract email from mbox - normalize to lowercase
        if actor.get('mbox') and actor['mbox'].startswith('mailto:'):
            actor_data['email'] = actor['mbox'].replace('mailto:', '').lower()
        
        # Extract account information
        if actor.get('account'):
            account = actor['account']
            actor_data['account_name'] = account.get('name')
            actor_data['account_homepage'] = account.get('homePage')
            # Normalize actor_id to lowercase for consistency
            actor_data['actor_id'] = account.get('name', '').lower() if account.get('name') else None
        
        # Fallback actor_id - normalize to lowercase
        if not actor_data['actor_id']:
            fallback_id = actor.get('mbox') or actor.get('openid') or actor.get('name')
            actor_data['actor_id'] = fallback_id.lower() if fallback_id else None
        
        return actor_data
    
    def extract_activity_data(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize activity data."""
        activity_data = {
            'activity_id': activity.get('id'),
            'activity_type': activity.get('objectType', 'Activity'),
            'name': None,
            'description': None,
            'interaction_type': None,
            'correct_responses_pattern': None,
            'choices': None,
            'scale': None,
            'source': None,
            'target': None,
            'steps': None,
            'extensions': None
        }
        
        # Extract definition data
        definition = activity.get('definition', {})
        if definition:
            activity_data['name'] = definition.get('name', {}).get('en-US') or definition.get('name', {}).get('en')
            activity_data['description'] = definition.get('description', {}).get('en-US') or definition.get('description', {}).get('en')
            activity_data['interaction_type'] = definition.get('interactionType')
            activity_data['correct_responses_pattern'] = definition.get('correctResponsesPattern')
            
            # Extract interaction components
            if definition.get('choices'):
                activity_data['choices'] = json.dumps(definition['choices'])
            if definition.get('scale'):
                activity_data['scale'] = json.dumps(definition['scale'])
            if definition.get('source'):
                activity_data['source'] = json.dumps(definition['source'])
            if definition.get('target'):
                activity_data['target'] = json.dumps(definition['target'])
            if definition.get('steps'):
                activity_data['steps'] = json.dumps(definition['steps'])
            if definition.get('extensions'):
                activity_data['extensions'] = json.dumps(definition['extensions'])
        
        return activity_data
    
    def extract_verb_data(self, verb: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize verb data."""
        verb_data = {
            'verb_id': verb.get('id'),
            'display_name': None,
            'language': 'en-US'
        }
        
        # Extract display name
        if verb.get('display'):
            display = verb['display']
            verb_data['display_name'] = display.get('en-US') or display.get('en')
            # Get first available language
            for lang in display.keys():
                if lang != 'en-US' and lang != 'en':
                    verb_data['language'] = lang
                    verb_data['display_name'] = display[lang]
                    break
        
        return verb_data
    
    def extract_result_data(self, result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract and normalize result data."""
        if not result:
            return {}
        
        return {
            'result_success': result.get('success'),
            'result_completion': result.get('completion'),
            'result_duration': result.get('duration'),
            'result_score_scaled': result.get('score', {}).get('scaled'),
            'result_score_raw': result.get('score', {}).get('raw'),
            'result_score_min': result.get('score', {}).get('min'),
            'result_score_max': result.get('score', {}).get('max')
        }
    
    def extract_context_data(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract and normalize context data."""
        if not context:
            return {}
        
        return {
            'context_registration': context.get('registration'),
            'context_platform': context.get('platform'),
            'context_language': context.get('language'),
            'context_statement_id': context.get('statement', {}).get('id'),
            'context_extensions': json.dumps(context.get('extensions')) if context.get('extensions') else None
        }
    
    async def normalize_statement(self, statement: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a single xAPI statement into structured data."""
        
        try:
            # Extract actor data
            actor_data = self.extract_actor_data(statement.get('actor', {}))
            
            # Extract activity data
            activity_data = self.extract_activity_data(statement.get('object', {}))
            
            # Extract verb data
            verb_data = self.extract_verb_data(statement.get('verb', {}))
            
            # Extract result data
            result_data = self.extract_result_data(statement.get('result'))
            
            # Extract context data
            context_data = self.extract_context_data(statement.get('context'))
            
            # Extract authority data
            authority_data = {}
            if statement.get('authority'):
                authority_data = self.extract_actor_data(statement['authority'])
            
            # Build normalized statement
            normalized = {
                'statement_id': statement.get('id'),
                'actor_id': actor_data['actor_id'],
                'verb_id': verb_data['verb_id'],
                'activity_id': activity_data['activity_id'],
                'timestamp': statement.get('timestamp'),
                'stored': statement.get('stored'),
                'authority_actor_id': authority_data.get('actor_id'),
                'version': statement.get('version'),
                'attachments': json.dumps(statement.get('attachments')) if statement.get('attachments') else None,
                'raw_statement': json.dumps(statement),
                'processed_at': datetime.utcnow().isoformat()
            }
            
            # Add result data
            normalized.update(result_data)
            
            # Add context data
            normalized.update(context_data)
            
            return {
                'actor': actor_data,
                'activity': activity_data,
                'verb': verb_data,
                'authority': authority_data,
                'statement': normalized
            }
            
        except Exception as e:
            logger.error(f"Error normalizing statement: {e}")
            self.error_count += 1
            raise
    
    async def upsert_actor(self, actor_data: Dict[str, Any]):
        """Upsert actor data to database."""
        sql = """
        INSERT INTO actors (actor_id, actor_type, name, email, account_name, account_homepage, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (actor_id) DO UPDATE SET
            actor_type = EXCLUDED.actor_type,
            name = EXCLUDED.name,
            email = EXCLUDED.email,
            account_name = EXCLUDED.account_name,
            account_homepage = EXCLUDED.account_homepage,
            updated_at = CURRENT_TIMESTAMP
        """
        
        params = (
            actor_data['actor_id'],
            actor_data['actor_type'],
            actor_data['name'],
            actor_data['email'],
            actor_data['account_name'],
            actor_data['account_homepage']
        )
        
        try:
            async with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    conn.commit()
        except Exception as e:
            logger.error(f"Error upserting actor: {e}")
            raise
    
    async def upsert_activity(self, activity_data: Dict[str, Any]):
        """Upsert activity data to database."""
        sql = """
        INSERT INTO activities (activity_id, activity_type, name, description, interaction_type, 
                               correct_responses_pattern, choices, scale, source, target, steps, extensions, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (activity_id) DO UPDATE SET
            activity_type = EXCLUDED.activity_type,
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            interaction_type = EXCLUDED.interaction_type,
            correct_responses_pattern = EXCLUDED.correct_responses_pattern,
            choices = EXCLUDED.choices,
            scale = EXCLUDED.scale,
            source = EXCLUDED.source,
            target = EXCLUDED.target,
            steps = EXCLUDED.steps,
            extensions = EXCLUDED.extensions,
            updated_at = CURRENT_TIMESTAMP
        """
        
        params = (
            activity_data['activity_id'],
            activity_data['activity_type'],
            activity_data['name'],
            activity_data['description'],
            activity_data['interaction_type'],
            activity_data['correct_responses_pattern'],
            activity_data['choices'],
            activity_data['scale'],
            activity_data['source'],
            activity_data['target'],
            activity_data['steps'],
            activity_data['extensions']
        )
        
        try:
            async with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    conn.commit()
        except Exception as e:
            logger.error(f"Error upserting activity: {e}")
            raise
    
    async def upsert_verb(self, verb_data: Dict[str, Any]):
        """Upsert verb data to database."""
        sql = """
        INSERT INTO verbs (verb_id, display_name, language)
        VALUES (%s, %s, %s)
        ON CONFLICT (verb_id) DO UPDATE SET
            display_name = EXCLUDED.display_name,
            language = EXCLUDED.language
        """
        
        params = (
            verb_data['verb_id'],
            verb_data['display_name'],
            verb_data['language']
        )
        
        try:
            async with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    conn.commit()
        except Exception as e:
            logger.error(f"Error upserting verb: {e}")
            raise
    
    async def insert_normalized_statement(self, statement_data: Dict[str, Any]):
        """Insert normalized statement data to database."""
        sql = """
        INSERT INTO statements_normalized (
            statement_id, actor_id, verb_id, activity_id, timestamp, stored, authority_actor_id,
            version, result_success, result_completion, result_duration, result_score_scaled,
            result_score_raw, result_score_min, result_score_max, context_registration,
            context_platform, context_language, context_statement_id, context_extensions,
            attachments, raw_statement, processed_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        ) ON CONFLICT (statement_id) DO NOTHING
        """
        
        params = (
            statement_data['statement_id'],
            statement_data['actor_id'],
            statement_data['verb_id'],
            statement_data['activity_id'],
            statement_data['timestamp'],
            statement_data['stored'],
            statement_data['authority_actor_id'],
            statement_data['version'],
            statement_data['result_success'],
            statement_data['result_completion'],
            statement_data['result_duration'],
            statement_data['result_score_scaled'],
            statement_data['result_score_raw'],
            statement_data['result_score_min'],
            statement_data['result_score_max'],
            statement_data['context_registration'],
            statement_data['context_platform'],
            statement_data['context_language'],
            statement_data['context_statement_id'],
            statement_data['context_extensions'],
            statement_data['attachments'],
            statement_data['raw_statement'],
            statement_data['processed_at']
        )
        
        try:
            async with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    conn.commit()
                    self.normalized_count += 1
        except Exception as e:
            logger.error(f"Error inserting normalized statement: {e}")
            self.error_count += 1
            raise
    
    async def process_statement_normalization(self, statement: Dict[str, Any]):
        """Process a single statement through the complete normalization pipeline."""
        try:
            # Normalize the statement
            normalized_data = await self.normalize_statement(statement)
            
            # Upsert related entities
            await self.upsert_actor(normalized_data['actor'])
            await self.upsert_activity(normalized_data['activity'])
            await self.upsert_verb(normalized_data['verb'])
            
            if normalized_data['authority']:
                await self.upsert_actor(normalized_data['authority'])
            
            # Insert normalized statement
            await self.insert_normalized_statement(normalized_data['statement'])
            
            logger.info(f"Successfully normalized statement: {statement.get('id')}")
            
        except Exception as e:
            logger.error(f"Error in statement normalization pipeline: {e}")
            raise
    
    async def get_normalization_stats(self) -> Dict[str, Any]:
        """Get normalization statistics."""
        try:
            async with self.get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Get counts from each table
                    cursor.execute("SELECT COUNT(*) as count FROM actors")
                    actor_count = cursor.fetchone()['count']
                    
                    cursor.execute("SELECT COUNT(*) as count FROM activities")
                    activity_count = cursor.fetchone()['count']
                    
                    cursor.execute("SELECT COUNT(*) as count FROM verbs")
                    verb_count = cursor.fetchone()['count']
                    
                    cursor.execute("SELECT COUNT(*) as count FROM statements_normalized")
                    statement_count = cursor.fetchone()['count']
                    
                    return {
                        'actors': actor_count,
                        'activities': activity_count,
                        'verbs': verb_count,
                        'statements': statement_count,
                        'processed_count': self.normalized_count,
                        'error_count': self.error_count
                    }
        except Exception as e:
            logger.error(f"Error getting normalization stats: {e}")
            return {}

    async def exists_equivalent_statement(self, actor_id: str, activity_id: str, response_text: str) -> bool:
        """Check if an equivalent statement already exists.

        Two statements are considered equivalent for idempotency purposes if:
        - actor_id matches
        - activity_id matches
        - result.response (stored in raw_statement JSONB) matches
        """
        sql = (
            "SELECT 1 FROM statements_normalized "
            "WHERE actor_id = %s AND activity_id = %s "
            "AND COALESCE(raw_statement #>> '{result,response}', '') = %s "
            "LIMIT 1"
        )
        try:
            async with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (actor_id, activity_id, response_text or ""))
                    return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking existing equivalent statement: {e}")
            # If check fails, default to not found so we don't block ingestion
            return False
