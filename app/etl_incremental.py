"""
Incremental ETL for 7taps xAPI analytics using MCP servers.

This module provides periodic catch-up ETL processing to handle missed statements
and ensure data consistency. Uses MCP Python for processing and MCP DB for storage.
"""

import os
import json
import logging
import asyncio
import httpx
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IncrementalETLProcessor:
    """Incremental ETL processor for catching up missed xAPI statements."""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.mcp_python_url = os.getenv("MCP_PYTHON_URL", "http://localhost:8002")
        self.mcp_postgres_url = os.getenv("MCP_POSTGRES_URL", "http://localhost:8001")
        self.stream_name = "xapi_statements"
        self.group_name = "incremental_processor"
        self.consumer_name = "incremental_worker"
        
        # Initialize Redis client
        self.redis_client = redis.from_url(self.redis_url)
        
        # Initialize HTTP client for MCP servers
        self._http_client = httpx.AsyncClient(timeout=30.0)
        
        # Track processing status
        self.last_processed_timestamp = None
        self.processing_stats = {
            "total_processed": 0,
            "last_run": None,
            "errors": 0,
            "successful_runs": 0
        }
        
    def mcp_python_client(self):
        """Get MCP Python client instance."""
        return self.http_client
        
    def mcp_db_client(self):
        """Get MCP DB client instance."""
        return self.http_client
        
    async def process_missed_statements(self, statements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process missed statements."""
        return await self.process_incremental_batch(statements)
        
    async def process_batch_mcp_python(self, statements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process batch using MCP Python."""
        return await self.process_incremental_batch(statements)
        
    async def write_batch_to_mcp_db(self, processed_statements: List[Dict[str, Any]]):
        """Write batch to MCP DB."""
        return await self.write_incremental_batch(processed_statements)
        
    def scheduler(self):
        """Get scheduler instance."""
        return self
        
    def retry_mechanism(self):
        """Get retry mechanism."""
        return self
        
    async def retry_failed_batch(self, batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Retry failed batch processing."""
        try:
            return await self.process_incremental_batch(batch)
        except Exception as e:
            logger.error(f"Retry failed: {e}")
            return {"status": "error", "error": str(e)}
        
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
                
    async def get_pending_messages(self, max_messages: int = 100) -> List[Tuple[str, Dict[str, Any]]]:
        """Get pending messages from Redis stream that haven't been processed."""
        try:
            # Read pending messages for this consumer group
            pending = self.redis_client.xpending_range(
                self.stream_name,
                self.group_name,
                min="-",
                max="+",
                count=max_messages
            )
            
            if not pending:
                return []
                
            # Get the actual messages
            message_ids = [msg["message_id"] for msg in pending]
            messages = self.redis_client.xreadgroup(
                self.group_name,
                self.consumer_name,
                {self.stream_name: "0"},
                count=max_messages
            )
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting pending messages: {e}")
            return []
            
    async def get_missed_statements(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Get statements that may have been missed in the last N hours."""
        try:
            # Calculate timestamp for lookback
            lookback_time = datetime.utcnow() - timedelta(hours=hours_back)
            lookback_timestamp = int(lookback_time.timestamp() * 1000)
            
            # Read messages from the lookback time
            messages = self.redis_client.xread(
                {self.stream_name: lookback_timestamp},
                count=1000
            )
            
            missed_statements = []
            for stream, message_list in messages:
                for message_id, fields in message_list:
                    try:
                        if b'data' in fields:
                            statement_data = json.loads(fields[b'data'].decode('utf-8'))
                            missed_statements.append({
                                'message_id': message_id,
                                'statement': statement_data,
                                'timestamp': fields.get(b'timestamp', lookback_timestamp)
                            })
                    except Exception as e:
                        logger.error(f"Error parsing message {message_id}: {e}")
                        continue
                        
            return missed_statements
            
        except Exception as e:
            logger.error(f"Error getting missed statements: {e}")
            return []
            
    async def process_incremental_batch(self, statements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process a batch of statements using MCP Python."""
        
        if not statements:
            return {"processed": 0, "errors": 0, "success": True}
            
        # MCP Python script for batch processing
        python_script = f"""
import json
import datetime
from typing import List, Dict, Any

def process_incremental_batch(statements):
    \"\"\"Process a batch of xAPI statements for incremental ETL.\"\"\"
    processed = []
    errors = 0
    
    for stmt_data in statements:
        try:
            statement = stmt_data['statement']
            message_id = stmt_data['message_id']
            
            # Flatten statement
            flattened = {{
                'statement_id': statement.get('id'),
                'actor_id': statement.get('actor', {{}}).get('account', {{}}).get('name'),
                'verb_id': statement.get('verb', {{}}).get('id'),
                'object_id': statement.get('object', {{}}).get('id'),
                'object_type': statement.get('object', {{}}).get('objectType'),
                'timestamp': statement.get('timestamp'),
                'raw_statement': json.dumps(statement),
                'processed_at': datetime.datetime.utcnow().isoformat(),
                'message_id': message_id,
                'processing_type': 'incremental'
            }}
            
            processed.append(flattened)
            
        except Exception as e:
            errors += 1
            print(f"Error processing statement: {{e}}")
    
    return {{
        'processed': processed,
        'errors': errors,
        'total_input': len(statements)
    }}

# Process the batch
statements = {json.dumps(statements)}
result = process_incremental_batch(statements)
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
            logger.error(f"Error processing incremental batch via MCP Python: {e}")
            raise
            
    async def write_incremental_batch(self, processed_statements: List[Dict[str, Any]]):
        """Write processed incremental statements to Postgres via MCP DB."""
        
        if not processed_statements:
            return
            
        # SQL to insert incremental statements
        sql = """
        INSERT INTO statements_flat (
            statement_id, actor_id, verb_id, object_id, object_type, 
            timestamp, raw_statement, processed_at, processing_type
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        ) ON CONFLICT (statement_id) DO UPDATE SET
            processed_at = EXCLUDED.processed_at,
            processing_type = EXCLUDED.processing_type
        """
        
        try:
            # Execute via MCP DB server
            for stmt in processed_statements:
                params = (
                    stmt.get('statement_id'),
                    stmt.get('actor_id'),
                    stmt.get('verb_id'),
                    stmt.get('object_id'),
                    stmt.get('object_type'),
                    stmt.get('timestamp'),
                    stmt.get('raw_statement'),
                    stmt.get('processed_at'),
                    stmt.get('processing_type', 'incremental')
                )
                
                response = await self._http_client.post(
                    f"{self.mcp_postgres_url}/execute",
                    json={
                        "sql": sql,
                        "params": params
                    }
                )
                await response.raise_for_status()
                
            logger.info(f"Successfully wrote {len(processed_statements)} incremental statements to Postgres")
            
        except Exception as e:
            logger.error(f"Error writing incremental batch to Postgres via MCP DB: {e}")
            raise
            
    async def run_incremental_etl(self, hours_back: int = 24, max_batch_size: int = 50) -> Dict[str, Any]:
        """Run incremental ETL to catch up missed statements."""
        
        start_time = datetime.utcnow()
        logger.info(f"Starting incremental ETL for last {hours_back} hours")
        
        try:
            await self.ensure_stream_group()
            
            # Get missed statements
            missed_statements = await self.get_missed_statements(hours_back)
            
            if not missed_statements:
                logger.info("No missed statements found")
                return {
                    "status": "success",
                    "processed": 0,
                    "errors": 0,
                    "duration_seconds": (datetime.utcnow() - start_time).total_seconds()
                }
            
            # Process in batches
            total_processed = 0
            total_errors = 0
            
            for i in range(0, len(missed_statements), max_batch_size):
                batch = missed_statements[i:i + max_batch_size]
                
                # Process batch via MCP Python
                batch_result = await self.process_incremental_batch(batch)
                
                if batch_result.get('success', True):
                    # Write to Postgres via MCP DB
                    await self.write_incremental_batch(batch_result.get('processed', []))
                    
                    total_processed += len(batch_result.get('processed', []))
                    total_errors += batch_result.get('errors', 0)
                    
                    # Acknowledge messages
                    for stmt in batch:
                        try:
                            self.redis_client.xack(
                                self.stream_name, 
                                self.group_name, 
                                stmt['message_id']
                            )
                        except Exception as e:
                            logger.error(f"Error acknowledging message {stmt['message_id']}: {e}")
                else:
                    total_errors += len(batch)
                    logger.error(f"Batch processing failed")
            
            # Update processing stats
            self.processing_stats["total_processed"] += total_processed
            self.processing_stats["last_run"] = datetime.utcnow().isoformat()
            self.processing_stats["errors"] += total_errors
            self.processing_stats["successful_runs"] += 1
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"Incremental ETL completed: {total_processed} processed, {total_errors} errors in {duration:.2f}s")
            
            return {
                "status": "success",
                "processed": total_processed,
                "errors": total_errors,
                "duration_seconds": duration,
                "batch_size": max_batch_size,
                "hours_back": hours_back
            }
            
        except Exception as e:
            logger.error(f"Incremental ETL failed: {e}")
            self.processing_stats["errors"] += 1
            
            return {
                "status": "error",
                "error": str(e),
                "duration_seconds": (datetime.utcnow() - start_time).total_seconds()
            }
            
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics."""
        return {
            **self.processing_stats,
            "last_processed_timestamp": self.last_processed_timestamp,
            "stream_name": self.stream_name,
            "group_name": self.group_name
        }
        
    async def schedule_incremental_etl(self, interval_hours: int = 6):
        """Schedule periodic incremental ETL runs."""
        while True:
            try:
                logger.info(f"Running scheduled incremental ETL (every {interval_hours} hours)")
                await self.run_incremental_etl(hours_back=interval_hours * 2)
                
                # Wait for next run
                await asyncio.sleep(interval_hours * 3600)
                
            except Exception as e:
                logger.error(f"Scheduled incremental ETL failed: {e}")
                # Wait 1 hour before retrying
                await asyncio.sleep(3600)
                
    async def close(self):
        """Close HTTP client."""
        await self._http_client.aclose()

# Global incremental processor instance
incremental_processor = IncrementalETLProcessor() 