"""
Streaming ETL for 7taps xAPI analytics using direct connections.

This module processes xAPI statements from Redis Streams and writes them to Postgres
using direct psycopg2 and redis-py connections for better performance and simplicity.
"""

import os
import json
import logging
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime
import redis
from contextlib import asynccontextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

from app.data_normalization import DataNormalizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ETLStreamingProcessor:
    """ETL processor for streaming xAPI statements using direct connections with performance optimizations."""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.database_url = os.getenv("DATABASE_URL", "postgresql://analytics_user:analytics_pass@localhost:5432/7taps_analytics")
        self.stream_name = "xapi_statements"
        self.group_name = "etl_processor"
        self.consumer_name = "etl_worker"
        
        # Performance optimization: Connection pooling
        self.db_pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=self.database_url
        )
        
        # Initialize Redis client with SSL configuration and connection pooling
        self.redis_client = redis.from_url(
            self.redis_url,
            ssl_cert_reqs=None,  # Disable SSL certificate verification for Heroku Redis
            decode_responses=True,
            max_connections=20,  # Connection pooling for Redis
            retry_on_timeout=True,
            socket_keepalive=True
        )
        
        # Performance tracking
        self.processed_count = 0
        self.error_count = 0
        self.last_processed_statement = None
        self.batch_size = 50  # Optimized batch size for better performance
        
        # Initialize data normalizer for automatic normalization
        self.normalizer = DataNormalizer()
        
    @asynccontextmanager
    async def get_db_connection(self):
        """Get database connection from pool with automatic cleanup."""
        conn = self.db_pool.getconn()
        try:
            yield conn
        finally:
            self.db_pool.putconn(conn)
        
    async def process_statement(self, statement: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single xAPI statement."""
        return await self.process_xapi_statement(statement)
        
    async def write_to_db(self, data: Dict[str, Any]):
        """Write data to PostgreSQL database."""
        return await self.write_to_postgres(data)
        
    async def ensure_stream_group(self):
        """Ensure Redis stream and consumer group exist."""
        try:
            # Create stream group if it doesn't exist
            self.redis_client.xgroup_create(
                self.stream_name, 
                self.group_name, 
                id="0", 
                mkstream=True
            )
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                logger.error(f"Error creating stream group: {e}")
                raise
                
    async def process_xapi_statement(self, statement: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single xAPI statement directly with optimized processing."""
        
        try:
            # Optimized flattening with minimal object creation
            actor = statement.get('actor', {})
            verb = statement.get('verb', {})
            object_data = statement.get('object', {})
            
            flattened = {
                'statement_id': statement.get('id'),
                'actor_id': actor.get('account', {}).get('name') if isinstance(actor, dict) else None,
                'verb_id': verb.get('id') if isinstance(verb, dict) else None,
                'object_id': object_data.get('id') if isinstance(object_data, dict) else None,
                'object_type': object_data.get('objectType') if isinstance(object_data, dict) else None,
                'timestamp': statement.get('timestamp'),
                'raw_statement': json.dumps(statement, separators=(',', ':')),  # Compact JSON
                'processed_at': datetime.utcnow().isoformat()
            }
            
            return flattened
                
        except Exception as e:
            logger.error(f"Error processing statement: {e}")
            self.error_count += 1
            raise
            
    async def write_to_postgres(self, flattened_data: Dict[str, Any]):
        """Write flattened data to Postgres with optimized batch processing."""
        
        # Optimized SQL with prepared statement
        sql = """
        INSERT INTO statements_flat (
            statement_id, actor_id, verb_id, object_id, object_type, 
            timestamp, raw_statement, processed_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s
        ) ON CONFLICT (statement_id) DO NOTHING
        """
        
        params = (
            flattened_data.get('statement_id'),
            flattened_data.get('actor_id'),
            flattened_data.get('verb_id'),
            flattened_data.get('object_id'),
            flattened_data.get('object_type'),
            flattened_data.get('timestamp'),
            flattened_data.get('raw_statement'),
            flattened_data.get('processed_at')
        )
        
        try:
            async with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    conn.commit()
                    
            self.processed_count += 1
            logger.info(f"Successfully wrote statement {flattened_data.get('statement_id')} to Postgres")
            
        except Exception as e:
            logger.error(f"Error writing to Postgres: {e}")
            self.error_count += 1
            raise
            
    async def write_batch_to_postgres(self, batch_data: List[Dict[str, Any]]):
        """Write batch of statements to Postgres for better performance and automatic normalization."""
        
        if not batch_data:
            return
            
        # Optimized batch insert SQL for flat table
        sql = """
        INSERT INTO statements_flat (
            statement_id, actor_id, verb_id, object_id, object_type, 
            timestamp, raw_statement, processed_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s
        ) ON CONFLICT (statement_id) DO NOTHING
        """
        
        # Prepare batch parameters
        batch_params = []
        for data in batch_data:
            params = (
                data.get('statement_id'),
                data.get('actor_id'),
                data.get('verb_id'),
                data.get('object_id'),
                data.get('object_type'),
                data.get('timestamp'),
                data.get('raw_statement'),
                data.get('processed_at')
            )
            batch_params.append(params)
        
        try:
            # Write to flat table first
            async with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Use executemany for batch insert
                    cursor.executemany(sql, batch_params)
                    conn.commit()
                    
            self.processed_count += len(batch_data)
            logger.info(f"Successfully wrote batch of {len(batch_data)} statements to Postgres")
            
            # Now normalize each statement automatically
            normalized_count = 0
            for data in batch_data:
                try:
                    # Parse the raw statement for normalization
                    raw_statement = json.loads(data.get('raw_statement', '{}'))
                    
                    # Normalize the statement
                    await self.normalizer.process_statement_normalization(raw_statement)
                    normalized_count += 1
                    
                except Exception as e:
                    logger.error(f"Error normalizing statement {data.get('statement_id')}: {e}")
                    continue
            
            logger.info(f"Successfully normalized {normalized_count}/{len(batch_data)} statements")
            
        except Exception as e:
            logger.error(f"Error writing batch to Postgres: {e}")
            self.error_count += len(batch_data)
            raise
            
    async def create_statements_table(self):
        """Create statements_flat table if it doesn't exist with optimized indexes."""
        
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS statements_flat (
            id SERIAL PRIMARY KEY,
            statement_id VARCHAR(255) UNIQUE NOT NULL,
            actor_id VARCHAR(255),
            verb_id VARCHAR(255),
            object_id VARCHAR(255),
            object_type VARCHAR(100),
            timestamp TIMESTAMP,
            raw_statement JSONB,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Performance optimization: Create indexes for common queries
        CREATE INDEX IF NOT EXISTS idx_statements_actor_id ON statements_flat(actor_id);
        CREATE INDEX IF NOT EXISTS idx_statements_verb_id ON statements_flat(verb_id);
        CREATE INDEX IF NOT EXISTS idx_statements_object_id ON statements_flat(object_id);
        CREATE INDEX IF NOT EXISTS idx_statements_timestamp ON statements_flat(timestamp);
        CREATE INDEX IF NOT EXISTS idx_statements_processed_at ON statements_flat(processed_at);
        """
        
        try:
            async with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(create_table_sql)
                    conn.commit()
                    
            logger.info("Statements table created/verified with optimized indexes")
            
        except Exception as e:
            logger.error(f"Error creating statements table: {e}")
            raise
            
    async def process_stream(self, max_messages: int = None) -> List[Dict[str, Any]]:
        """Process Redis stream with optimized batch processing."""
        
        if max_messages is None:
            max_messages = self.batch_size
            
        try:
            # Ensure stream group exists
            await self.ensure_stream_group()
            
            # Read messages from stream with optimized batch size
            messages = self.redis_client.xreadgroup(
                self.group_name,
                self.consumer_name,
                {self.stream_name: ">"},
                count=max_messages,
                block=1000
            )
            
            processed_statements = []
            batch_data = []
            
            for stream, message_list in messages:
                for message_id, fields in message_list:
                    try:
                        # Parse statement data
                        if b'data' in fields:
                            statement_data = json.loads(fields[b'data'].decode('utf-8'))
                        else:
                            statement_data = json.loads(fields.get('data', '{}'))
                        
                        # Process statement
                        processed = await self.process_xapi_statement(statement_data)
                        processed_statements.append(processed)
                        batch_data.append(processed)
                        
                        # Acknowledge message
                        self.redis_client.xack(stream, self.group_name, message_id)
                        
                        # Update last processed
                        self.last_processed_statement = processed
                        
                    except Exception as e:
                        logger.error(f"Error processing message {message_id}: {e}")
                        self.error_count += 1
                        continue
            
            # Write batch to database for better performance
            if batch_data:
                await self.write_batch_to_postgres(batch_data)
            
            return processed_statements
            
        except Exception as e:
            logger.error(f"Error in stream processing: {e}")
            raise
            
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "success_rate": (self.processed_count / (self.processed_count + self.error_count)) * 100 if (self.processed_count + self.error_count) > 0 else 0,
            "batch_size": self.batch_size,
            "last_processed_statement": self.last_processed_statement
        }
        
    async def get_last_processed_statement(self) -> Optional[Dict[str, Any]]:
        """Get last processed statement."""
        return self.last_processed_statement
        
    async def close(self):
        """Close database connection pool."""
        if self.db_pool:
            self.db_pool.closeall()

# Global processor instance (lazy initialization)
etl_processor = None

def get_etl_processor():
    """Get or create the global ETL processor instance."""
    global etl_processor
    if etl_processor is None:
        etl_processor = ETLStreamingProcessor()
    return etl_processor 