"""
Streaming ETL for 7taps xAPI analytics using MCP servers.

This module processes xAPI statements from Redis Streams and writes them to Postgres
via MCP DB server. It uses MCP Python for script execution.
"""

import os
import json
import logging
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime
import redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ETLStreamingProcessor:
    """ETL processor for streaming xAPI statements using MCP servers."""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.database_url = os.getenv("DATABASE_URL", "postgresql://analytics_user:analytics_pass@localhost:5432/7taps_analytics")
        self.stream_name = "xapi_statements"
        self.group_name = "etl_processor"
        self.consumer_name = "etl_worker"
        
        # Initialize Redis client with SSL configuration
        self.redis_client = redis.from_url(
            self.redis_url,
            ssl_cert_reqs=None,  # Disable SSL certificate verification for Heroku Redis
            decode_responses=True
        )
        
        # Initialize database connection
        import psycopg2
        self.db_connection = psycopg2.connect(self.database_url)
        
        # Track last processed statement
        self.last_processed_statement = None
        
    def redis_client(self):
        """Get Redis client instance."""
        return self.redis_client
        
    def redis_client(self):
        """Get Redis client instance."""
        return self.redis_client
        
    def db_client(self):
        """Get database client instance."""
        return self.db_connection
        
    async def process_statement(self, statement: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single xAPI statement."""
        return await self.process_xapi_statement(statement)
        
    async def write_to_mcp_db(self, data: Dict[str, Any]):
        """Write data to MCP DB."""
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
        """Process a single xAPI statement directly."""
        
        try:
            # Flatten xAPI statement for database storage
            flattened = {
                'statement_id': statement.get('id'),
                'actor_id': statement.get('actor', {}).get('account', {}).get('name'),
                'verb_id': statement.get('verb', {}).get('id'),
                'object_id': statement.get('object', {}).get('id'),
                'object_type': statement.get('object', {}).get('objectType'),
                'timestamp': statement.get('timestamp'),
                'raw_statement': json.dumps(statement),
                'processed_at': datetime.utcnow().isoformat()
            }
            
            return flattened
                
        except Exception as e:
            logger.error(f"Error processing statement: {e}")
            raise
            
    async def write_to_postgres(self, flattened_data: Dict[str, Any]):
        """Write flattened data to Postgres directly."""
        
        # SQL to insert flattened statement
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
            # Execute directly via psycopg2
            cursor = self.db_connection.cursor()
            cursor.execute(sql, params)
            self.db_connection.commit()
            cursor.close()
            
            logger.info(f"Successfully wrote statement {flattened_data.get('statement_id')} to Postgres")
            
        except Exception as e:
            logger.error(f"Error writing to Postgres: {e}")
            raise
            
    async def create_statements_table(self):
        """Create statements_flat table if it doesn't exist."""
        
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
        """
        
        try:
            cursor = self.db_connection.cursor()
            cursor.execute(create_table_sql)
            self.db_connection.commit()
            cursor.close()
            logger.info("Statements table created/verified")
            
        except Exception as e:
            logger.error(f"Error creating statements table: {e}")
            raise
            
    async def process_stream(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """Process messages from Redis stream using MCP servers."""
        
        await self.ensure_stream_group()
        await self.create_statements_table()
        
        processed_statements = []
        
        try:
            # Read messages from stream
            messages = self.redis_client.xreadgroup(
                self.group_name,
                self.consumer_name,
                {self.stream_name: ">"},
                count=max_messages,
                block=1000
            )
            
            for stream, message_list in messages:
                for message_id, fields in message_list:
                    try:
                        # Parse xAPI statement
                        if b'data' in fields:
                            statement_data = json.loads(fields[b'data'].decode('utf-8'))
                        else:
                            # Handle case where data might be in different format
                            statement_data = json.loads(fields.get('data', '{}'))
                        
                        # Process via MCP Python
                        flattened_data = await self.process_xapi_statement(statement_data)
                        
                        # Write to Postgres via MCP DB
                        await self.write_to_postgres(flattened_data)
                        
                        # Acknowledge message
                        self.redis_client.xack(self.stream_name, self.group_name, message_id)
                        
                        # Track last processed
                        self.last_processed_statement = {
                            "statement_id": flattened_data.get('statement_id'),
                            "processed_at": flattened_data.get('processed_at'),
                            "raw_statement": statement_data
                        }
                        
                        processed_statements.append(self.last_processed_statement)
                        logger.info(f"Processed statement {flattened_data.get('statement_id')}")
                        
                    except Exception as e:
                        logger.error(f"Error processing message {message_id}: {e}")
                        # Don't acknowledge failed messages
                        continue
                        
        except Exception as e:
            logger.error(f"Error reading from Redis stream: {e}")
            raise
            
        return processed_statements
        
    async def get_last_processed_statement(self) -> Optional[Dict[str, Any]]:
        """Get the last processed statement for the test endpoint."""
        return self.last_processed_statement
        
    async def close(self):
        """Close database connection."""
        if self.db_connection:
            self.db_connection.close()

# Global processor instance
etl_processor = ETLStreamingProcessor() 