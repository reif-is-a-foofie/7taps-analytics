"""
Migration script to move data from statements_flat to normalized tables.

This script processes all existing data in statements_flat and moves it to the
normalized tables (actors, activities, verbs, statements_normalized) for better
analytics and querying capabilities.
"""

import os
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FlatToNormalizedMigrator:
    """Migrate data from statements_flat to normalized tables."""
    
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "postgresql://analytics_user:analytics_pass@localhost:5432/7taps_analytics")
        
        # Connection pooling for performance
        self.db_pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=self.database_url
        )
        
        # Migration tracking
        self.migrated_count = 0
        self.error_count = 0
        
    @asynccontextmanager
    async def get_db_connection(self):
        """Get database connection from pool with automatic cleanup."""
        conn = self.db_pool.getconn()
        try:
            yield conn
        finally:
            self.db_pool.putconn(conn)
    
    async def get_flat_statements(self) -> List[Dict[str, Any]]:
        """Get all statements from statements_flat table."""
        try:
            async with self.get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT * FROM statements_flat 
                        ORDER BY processed_at ASC
                    """)
                    return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error fetching flat statements: {e}")
            raise
    
    async def extract_actor_data(self, raw_statement: Dict[str, Any]) -> Dict[str, Any]:
        """Extract actor data from raw statement."""
        actor = raw_statement.get('actor', {})
        
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
            actor_data['actor_id'] = actor_data['email']
        
        # Extract account information - normalize to lowercase
        if actor.get('account'):
            account = actor['account']
            actor_data['account_name'] = account.get('name')
            actor_data['account_homepage'] = account.get('homePage')
            if account.get('name'):
                actor_data['actor_id'] = account['name'].lower()
        
        # Use name as fallback - normalize to lowercase
        if not actor_data['actor_id'] and actor.get('name'):
            actor_data['actor_id'] = actor['name'].lower()
        
        return actor_data
    
    async def extract_activity_data(self, raw_statement: Dict[str, Any]) -> Dict[str, Any]:
        """Extract activity data from raw statement."""
        object_data = raw_statement.get('object', {})
        
        activity_data = {
            'activity_id': object_data.get('id'),
            'activity_type': object_data.get('objectType', 'Activity'),
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
        if object_data.get('definition'):
            definition = object_data['definition']
            
            # Extract name
            if definition.get('name'):
                name_obj = definition['name']
                if isinstance(name_obj, dict):
                    activity_data['name'] = name_obj.get('en-US') or next(iter(name_obj.values()), None)
                else:
                    activity_data['name'] = str(name_obj)
            
            # Extract description
            if definition.get('description'):
                desc_obj = definition['description']
                if isinstance(desc_obj, dict):
                    activity_data['description'] = desc_obj.get('en-US') or next(iter(desc_obj.values()), None)
                else:
                    activity_data['description'] = str(desc_obj)
            
            # Extract interaction data
            activity_data['interaction_type'] = definition.get('interactionType')
            activity_data['correct_responses_pattern'] = definition.get('correctResponsesPattern')
            
            # Extract complex data as JSONB
            for field in ['choices', 'scale', 'source', 'target', 'steps', 'extensions']:
                if definition.get(field):
                    activity_data[field] = json.dumps(definition[field])
        
        return activity_data
    
    async def extract_verb_data(self, raw_statement: Dict[str, Any]) -> Dict[str, Any]:
        """Extract verb data from raw statement."""
        verb = raw_statement.get('verb', {})
        
        verb_data = {
            'verb_id': verb.get('id'),
            'display_name': None,
            'language': 'en-US'
        }
        
        # Extract display name
        if verb.get('display'):
            display_obj = verb['display']
            if isinstance(display_obj, dict):
                verb_data['display_name'] = display_obj.get('en-US') or next(iter(display_obj.values()), None)
            else:
                verb_data['display_name'] = str(display_obj)
        
        return verb_data
    
    async def extract_result_data(self, raw_statement: Dict[str, Any]) -> Dict[str, Any]:
        """Extract result data from raw statement."""
        result = raw_statement.get('result', {})
        
        result_data = {
            'success': result.get('success'),
            'completion': result.get('completion'),
            'duration': result.get('duration'),
            'score_scaled': None,
            'score_raw': None,
            'score_min': None,
            'score_max': None
        }
        
        # Extract score data
        if result.get('score'):
            score = result['score']
            result_data['score_scaled'] = score.get('scaled')
            result_data['score_raw'] = score.get('raw')
            result_data['score_min'] = score.get('min')
            result_data['score_max'] = score.get('max')
        
        return result_data
    
    async def extract_context_data(self, raw_statement: Dict[str, Any]) -> Dict[str, Any]:
        """Extract context data from raw statement."""
        context = raw_statement.get('context', {})
        
        context_data = {
            'registration': context.get('registration'),
            'platform': context.get('platform'),
            'language': context.get('language'),
            'statement_id': context.get('statement', {}).get('id') if context.get('statement') else None,
            'extensions': json.dumps(context.get('extensions')) if context.get('extensions') else None
        }
        
        return context_data
    
    async def upsert_actor(self, actor_data: Dict[str, Any]):
        """Upsert actor data to database."""
        sql = """
        INSERT INTO actors (actor_id, actor_type, name, email, account_name, account_homepage, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
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
        INSERT INTO activities (
            activity_id, activity_type, name, description, interaction_type, 
            correct_responses_pattern, choices, scale, source, target, steps, extensions,
            created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
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
        INSERT INTO verbs (verb_id, display_name, language, created_at)
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
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
                    self.migrated_count += 1
        except Exception as e:
            logger.error(f"Error inserting normalized statement: {e}")
            self.error_count += 1
            raise
    
    async def migrate_statement(self, flat_statement: Dict[str, Any]):
        """Migrate a single statement from flat to normalized format."""
        try:
            # Parse raw statement JSON
            raw_statement = json.loads(flat_statement['raw_statement'])
            
            # Extract data from raw statement
            actor_data = await self.extract_actor_data(raw_statement)
            activity_data = await self.extract_activity_data(raw_statement)
            verb_data = await self.extract_verb_data(raw_statement)
            result_data = await self.extract_result_data(raw_statement)
            context_data = await self.extract_context_data(raw_statement)
            
            # Upsert related entities
            if actor_data['actor_id']:
                await self.upsert_actor(actor_data)
            
            if activity_data['activity_id']:
                await self.upsert_activity(activity_data)
            
            if verb_data['verb_id']:
                await self.upsert_verb(verb_data)
            
            # Prepare normalized statement data
            normalized_statement = {
                'statement_id': flat_statement['statement_id'],
                'actor_id': actor_data['actor_id'],
                'verb_id': verb_data['verb_id'],
                'activity_id': activity_data['activity_id'],
                'timestamp': flat_statement['timestamp'],
                'stored': flat_statement['processed_at'],
                'authority_actor_id': None,  # Not extracted from flat data
                'version': raw_statement.get('version'),
                'result_success': result_data['success'],
                'result_completion': result_data['completion'],
                'result_duration': result_data['duration'],
                'result_score_scaled': result_data['score_scaled'],
                'result_score_raw': result_data['score_raw'],
                'result_score_min': result_data['score_min'],
                'result_score_max': result_data['score_max'],
                'context_registration': context_data['registration'],
                'context_platform': context_data['platform'],
                'context_language': context_data['language'],
                'context_statement_id': context_data['statement_id'],
                'context_extensions': context_data['extensions'],
                'attachments': json.dumps(raw_statement.get('attachments')) if raw_statement.get('attachments') else None,
                'raw_statement': flat_statement['raw_statement'],
                'processed_at': flat_statement['processed_at']
            }
            
            # Insert normalized statement
            await self.insert_normalized_statement(normalized_statement)
            
            logger.info(f"Successfully migrated statement: {flat_statement['statement_id']}")
            
        except Exception as e:
            logger.error(f"Error migrating statement {flat_statement['statement_id']}: {e}")
            self.error_count += 1
    
    async def run_migration(self):
        """Run the complete migration from flat to normalized tables."""
        logger.info("Starting migration from statements_flat to normalized tables...")
        
        try:
            # Get all flat statements
            flat_statements = await self.get_flat_statements()
            logger.info(f"Found {len(flat_statements)} statements to migrate")
            
            # Migrate each statement
            for flat_statement in flat_statements:
                await self.migrate_statement(flat_statement)
            
            logger.info(f"Migration completed. Migrated: {self.migrated_count}, Errors: {self.error_count}")
            
        except Exception as e:
            logger.error(f"Error during migration: {e}")
            raise

# Migration function for external use
async def migrate_flat_to_normalized():
    """Main migration function."""
    migrator = FlatToNormalizedMigrator()
    await migrator.run_migration()
    return {
        'migrated_count': migrator.migrated_count,
        'error_count': migrator.error_count
    }
