"""
Database utilities for infrastructure-v2.
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from typing import Optional, Dict, Any, List
import structlog

logger = structlog.get_logger()

# Global connection pool
_db_pool: Optional[SimpleConnectionPool] = None

def get_database_url() -> str:
    """Get database URL from environment."""
    return os.getenv("DATABASE_URL", "postgresql://analytics_user:analytics_pass@localhost:5432/7taps_analytics")

def get_db_pool() -> SimpleConnectionPool:
    """Get or create database connection pool."""
    global _db_pool
    if _db_pool is None:
        database_url = get_database_url()
        if database_url:
            # Ensure Heroku-style URL compatibility
            dsn = database_url.replace('postgres://', 'postgresql://', 1) if database_url.startswith('postgres://') else database_url
            sslmode = os.getenv('PGSSLMODE', 'require')
            _db_pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=dsn,
                sslmode=sslmode
            )
        else:
            logger.warning("No DATABASE_URL provided, database operations disabled")
    return _db_pool

def get_db_connection():
    """Get database connection from pool."""
    pool = get_db_pool()
    if pool is None:
        raise Exception("Database connection pool not available")
    return pool.getconn()

def put_db_connection(conn):
    """Return database connection to pool."""
    pool = get_db_pool()
    if pool:
        pool.putconn(conn)

def execute_query(sql: str, params: tuple = None) -> List[Dict[str, Any]]:
    """Execute a SQL query and return results."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql, params)
            if cursor.description:
                return [dict(row) for row in cursor.fetchall()]
            return []
    except Exception as e:
        logger.error("Database query failed", error=str(e), sql=sql)
        raise
    finally:
        if conn:
            put_db_connection(conn)

