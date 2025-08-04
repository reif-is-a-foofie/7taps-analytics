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
        self.mcp_python_url = os.getenv("MCP_PYTHON_URL", "http://localhost:8002")
        self.mcp_postgres_url = os.getenv("MCP_POSTGRES_URL", "http://localhost:8001")
        self.stream_name = "xapi_statements"
        self.group_name = "etl_processor"
        self.consumer_name = "etl_worker"
        
        # Initialize Redis client
        self.redis_client = redis.from_url(self.redis_url)
        
        # Initialize HTTP client for MCP servers
        self._http_client = httpx.AsyncClient(timeout=30.0)
        
        # Track last processed statement
        self.last_processed_statement = None
        
    def redis_client(self):
        """Get Redis client instance."""
        return self.redis_client
        
    def mcp_db_client(self):
        """Get MCP DB client instance."""
        return self._http_client
        
    def mcp_python_client(self):
        """Get MCP Python client instance."""
        return self._http_client
        
    @property
    def http_client(self):
        """Get HTTP client for MCP operations."""
        return self._http_client
        
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
        """Process a single xAPI statement using MCP Python."""
        
        # MCP Python script to flatten xAPI statement
        python_script = f"""
import json
import datetime

def flatten_xapi_statement(statement):
    \"\"\"Flatten xAPI statement for database storage.\"\"\"
    flattened = {{
        'statement_id': statement.get('id'),
        'actor_id': statement.get('actor', {{}}).get('account', {{}}).get('name'),
        'verb_id': statement.get('verb', {{}}).get('id'),
        'object_id': statement.get('object', {{}}).get('id'),
        'object_type': statement.get('object', {{}}).get('objectType'),
        'timestamp': statement.get('timestamp'),
        'raw_statement': json.dumps(statement),
        'processed_at': datetime.datetime.utcnow().isoformat()
    }}
    return flattened

# Process the statement
statement = {json.dumps(statement)}
result = flatten_xapi_statement(statement)
print(json.dumps(result))
"""
        
        try:
            # Execute script via MCP Python
            response = await self._http_client.post(
                f"{self.mcp_python_url}/execute",
                json={"script": python_script}
            )
            await response.raise_for_status()
            
            # Parse result
            result = await response.json()
            if "output" in result:
                return json.loads(result["output"])
            else:
                raise Exception(f"MCP Python execution failed: {result}")
                
        except Exception as e:
            logger.error(f"Error processing statement via MCP Python: {e}")
            raise
            
    async def write_to_postgres(self, flattened_data: Dict[str, Any]):
        """Write flattened data to Postgres via MCP DB server."""
        
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
            # Execute via MCP DB server
            response = await self._http_client.post(
                f"{self.mcp_postgres_url}/execute",
                json={
                    "sql": sql,
                    "params": params
                }
            )
            await response.raise_for_status()
            
            logger.info(f"Successfully wrote statement {flattened_data.get('statement_id')} to Postgres")
            
        except Exception as e:
            logger.error(f"Error writing to Postgres via MCP DB: {e}")
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
            response = await self._http_client.post(
                f"{self.mcp_postgres_url}/execute",
                json={"sql": create_table_sql}
            )
            await response.raise_for_status()
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
        """Close HTTP client."""
        await self._http_client.aclose()

# Global processor instance
etl_processor = ETLStreamingProcessor() 