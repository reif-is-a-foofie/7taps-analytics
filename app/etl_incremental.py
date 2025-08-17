"""
Incremental ETL for 7taps xAPI analytics using direct database connections.

This module handles incremental processing of xAPI statements
and ensure data consistency. Uses direct PostgreSQL connections for storage.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx
import psycopg2
import redis
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IncrementalETLProcessor:
    """Incremental ETL processor using direct database connections."""

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://analytics_user:analytics_pass@localhost:5432/7taps_analytics",
        )
        self.stream_name = "xapi_statements"
        self.group_name = "incremental_etl"
        self.consumer_name = "incremental_worker"

        # Initialize Redis client
        self.redis_client = redis.from_url(
            self.redis_url, ssl_cert_reqs=None, decode_responses=True
        )

        # Initialize database connection pool
        self.db_pool = SimpleConnectionPool(
            minconn=1, maxconn=10, dsn=self.database_url
        )

        # Processing stats
        self.processed_count = 0
        self.error_count = 0
        self.last_processed_time = None

    def get_db_connection(self):
        """Get database connection from pool."""
        return self.db_pool.getconn()

    def return_db_connection(self, conn):
        """Return database connection to pool."""
        self.db_pool.putconn(conn)

    async def process_missed_statements(
        self, statements: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Process missed statements."""
        return await self.process_incremental_batch(statements)

    async def process_batch_direct(
        self, statements: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process batch using direct database connections."""
        try:
            processed_statements = []

            for statement in statements:
                # Process statement (flatten for database storage)
                processed = {
                    "statement_id": statement.get("id"),
                    "actor_id": (
                        statement.get("actor", {}).get("name")
                        if isinstance(statement.get("actor"), dict)
                        else None
                    ),
                    "verb_id": (
                        statement.get("verb", {}).get("id")
                        if isinstance(statement.get("verb"), dict)
                        else None
                    ),
                    "object_id": (
                        statement.get("object", {}).get("id")
                        if isinstance(statement.get("object"), dict)
                        else None
                    ),
                    "object_type": (
                        statement.get("object", {}).get("objectType")
                        if isinstance(statement.get("object"), dict)
                        else None
                    ),
                    "timestamp": statement.get("timestamp"),
                    "raw_statement": json.dumps(statement),
                    "processed_at": datetime.utcnow().isoformat(),
                }
                processed_statements.append(processed)

            return {
                "processed_count": len(processed_statements),
                "statements": processed_statements,
                "success": True,
            }

        except Exception as e:
            logger.error(f"Error processing batch directly: {e}")
            return {"processed_count": 0, "error": str(e), "success": False}

    async def write_batch_to_database(self, processed_statements: List[Dict[str, Any]]):
        """Write processed incremental statements to Postgres directly."""
        try:
            conn = self.get_db_connection()
            try:
                with conn.cursor() as cursor:
                    # Insert statements into statements_flat table
                    sql = """
                    INSERT INTO statements_flat (
                        statement_id, actor_id, verb_id, object_id, object_type, 
                        timestamp, raw_statement, processed_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s
                    ) ON CONFLICT (statement_id) DO NOTHING
                    """

                    for statement in processed_statements:
                        cursor.execute(
                            sql,
                            (
                                statement.get("statement_id"),
                                statement.get("actor_id"),
                                statement.get("verb_id"),
                                statement.get("object_id"),
                                statement.get("object_type"),
                                statement.get("timestamp"),
                                statement.get("raw_statement"),
                                statement.get("processed_at"),
                            ),
                        )

                    conn.commit()
                    logger.info(
                        f"Successfully wrote {len(processed_statements)} incremental statements to database"
                    )

            finally:
                self.return_db_connection(conn)

        except Exception as e:
            logger.error(f"Error writing incremental batch to database: {e}")
            raise

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
                self.stream_name, self.group_name, id="0", mkstream=True
            )
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                logger.error(f"Error creating stream group: {e}")
                raise

    async def get_pending_messages(
        self, max_messages: int = 100
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Get pending messages from Redis stream that haven't been processed."""
        try:
            # Read pending messages for this consumer group
            pending = self.redis_client.xpending_range(
                self.stream_name, self.group_name, min="-", max="+", count=max_messages
            )

            if not pending:
                return []

            # Get the actual messages
            message_ids = [msg["message_id"] for msg in pending]
            messages = self.redis_client.xreadgroup(
                self.group_name,
                self.consumer_name,
                {self.stream_name: "0"},
                count=max_messages,
            )

            return messages

        except Exception as e:
            logger.error(f"Error getting pending messages: {e}")
            return []

    async def get_missed_statements(
        self, start_time: datetime, end_time: datetime
    ) -> List[Dict[str, Any]]:
        """Get statements that may have been missed in the last N hours."""
        try:
            # Calculate timestamp for lookback
            lookback_time = start_time
            lookback_timestamp = int(lookback_time.timestamp() * 1000)

            # Read messages from the lookback time
            messages = self.redis_client.xread(
                {self.stream_name: lookback_timestamp}, count=1000
            )

            missed_statements = []
            for stream, message_list in messages:
                for message_id, fields in message_list:
                    try:
                        if b"data" in fields:
                            statement_data = json.loads(fields[b"data"].decode("utf-8"))
                            missed_statements.append(
                                {
                                    "message_id": message_id,
                                    "statement": statement_data,
                                    "timestamp": fields.get(
                                        b"timestamp", lookback_timestamp
                                    ),
                                }
                            )
                    except Exception as e:
                        logger.error(f"Error parsing message {message_id}: {e}")
                        continue

            return missed_statements

        except Exception as e:
            logger.error(f"Error getting missed statements: {e}")
            return []

    async def process_incremental_batch(
        self, statements: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
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
                f"{self.mcp_python_url}/execute", json={"script": python_script}
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
                    stmt.get("statement_id"),
                    stmt.get("actor_id"),
                    stmt.get("verb_id"),
                    stmt.get("object_id"),
                    stmt.get("object_type"),
                    stmt.get("timestamp"),
                    stmt.get("raw_statement"),
                    stmt.get("processed_at"),
                    stmt.get("processing_type", "incremental"),
                )

                response = await self._http_client.post(
                    f"{self.mcp_postgres_url}/execute",
                    json={"sql": sql, "params": params},
                )
                await response.raise_for_status()

            logger.info(
                f"Successfully wrote {len(processed_statements)} incremental statements to Postgres"
            )

        except Exception as e:
            logger.error(f"Error writing incremental batch to Postgres via MCP DB: {e}")
            raise

    async def run_incremental_etl(self, hours_back: int = 24) -> Dict[str, Any]:
        """Run incremental ETL for the specified time period."""
        try:
            # Calculate time range
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours_back)

            logger.info(f"Running incremental ETL from {start_time} to {end_time}")

            # Get missed statements from Redis
            missed_statements = await self.get_missed_statements(start_time, end_time)

            if not missed_statements:
                logger.info("No missed statements found for incremental processing")
                return {
                    "processed_count": 0,
                    "missed_statements": 0,
                    "success": True,
                    "message": "No missed statements found",
                }

            logger.info(
                f"Found {len(missed_statements)} missed statements for processing"
            )

            # Process batch using direct database connections
            result = await self.process_batch_direct(missed_statements)

            if result["success"]:
                # Write to database directly
                await self.write_batch_to_database(result["statements"])

                self.processed_count += result["processed_count"]
                self.last_processed_time = datetime.utcnow().isoformat()

                return {
                    "processed_count": result["processed_count"],
                    "missed_statements": len(missed_statements),
                    "success": True,
                    "message": f"Successfully processed {result['processed_count']} incremental statements",
                }
            else:
                self.error_count += 1
                return {
                    "processed_count": 0,
                    "error": result.get("error", "Unknown error"),
                    "success": False,
                }

        except Exception as e:
            logger.error(f"Error in incremental ETL: {e}")
            self.error_count += 1
            return {"processed_count": 0, "error": str(e), "success": False}

    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get incremental ETL processing statistics."""
        return {
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "last_processed_time": self.last_processed_time,
            "success_rate": (
                (self.processed_count / (self.processed_count + self.error_count)) * 100
                if (self.processed_count + self.error_count) > 0
                else 0
            ),
            "database_url": (
                self.database_url.split("@")[-1]
                if self.database_url
                else "not_configured"
            ),
            "redis_stream": self.stream_name,
        }

    async def schedule_incremental_etl(self, interval_hours: int = 6):
        """Schedule periodic incremental ETL runs."""
        while True:
            try:
                logger.info(
                    f"Running scheduled incremental ETL (every {interval_hours} hours)"
                )
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
