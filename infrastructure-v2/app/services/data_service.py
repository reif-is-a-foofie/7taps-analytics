"""
Data service for database operations and data management.
"""
from typing import Dict, Any, List, Optional
import structlog
from datetime import datetime, timedelta

from app.core.exceptions import ExternalServiceError, ValidationError
from app.database import execute_query, get_db_pool
from app.redis_client import get_redis_client

logger = structlog.get_logger()


class DataService:
    """Service for handling data operations and management."""
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self.db_pool = get_db_pool()
    
    async def get_data_overview(self) -> Dict[str, Any]:
        """Get comprehensive data overview."""
        try:
            overview = {}
            
            # Get table counts
            tables = ["xapi_statements", "xapi_statements_normalized", "users", "lessons"]
            for table in tables:
                try:
                    result = execute_query(f"SELECT COUNT(*) as count FROM {table}")
                    overview[f"{table}_count"] = result[0]["count"] if result else 0
                except Exception as e:
                    logger.warning(f"Failed to get count for {table}", error=str(e))
                    overview[f"{table}_count"] = 0
            
            # Get recent activity
            try:
                recent_query = """
                SELECT COUNT(*) as count, DATE(timestamp) as date
                FROM xapi_statements
                WHERE timestamp >= NOW() - INTERVAL '7 days'
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
                LIMIT 7
                """
                recent_activity = execute_query(recent_query)
                overview["recent_activity"] = recent_activity
            except Exception as e:
                logger.warning("Failed to get recent activity", error=str(e))
                overview["recent_activity"] = []
            
            # Get top users
            try:
                top_users_query = """
                SELECT 
                    JSON_EXTRACT_SCALAR(actor, '$.mbox') as user_email,
                    COUNT(*) as statement_count
                FROM xapi_statements
                WHERE timestamp >= NOW() - INTERVAL '30 days'
                GROUP BY JSON_EXTRACT_SCALAR(actor, '$.mbox')
                ORDER BY statement_count DESC
                LIMIT 10
                """
                top_users = execute_query(top_users_query)
                overview["top_users"] = top_users
            except Exception as e:
                logger.warning("Failed to get top users", error=str(e))
                overview["top_users"] = []
            
            return {
                "success": True,
                "overview": overview,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get data overview", error=str(e))
            raise ExternalServiceError(f"Data overview failed: {str(e)}")
    
    async def execute_custom_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a custom SQL query safely."""
        try:
            # Basic query validation
            if not query.strip():
                raise ValidationError("Query cannot be empty")
            
            # Check for dangerous operations
            dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE"]
            query_upper = query.upper()
            for keyword in dangerous_keywords:
                if keyword in query_upper:
                    raise ValidationError(f"Query contains dangerous operation: {keyword}")
            
            # Execute query
            results = execute_query(query, tuple(params.values()) if params else None)
            
            return {
                "success": True,
                "results": results,
                "row_count": len(results),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error("Custom query execution failed", error=str(e))
            raise ExternalServiceError(f"Query execution failed: {str(e)}")
    
    async def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get schema information for a specific table."""
        try:
            # Validate table name
            if not table_name or not table_name.replace("_", "").isalnum():
                raise ValidationError("Invalid table name")
            
            # Get column information
            schema_query = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length
            FROM information_schema.columns
            WHERE table_name = %s AND table_schema = 'public'
            ORDER BY ordinal_position
            """
            
            results = execute_query(schema_query, (table_name,))
            
            if not results:
                raise ValidationError(f"Table '{table_name}' not found")
            
            return {
                "success": True,
                "table_name": table_name,
                "columns": results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error("Failed to get table schema", error=str(e))
            raise ExternalServiceError(f"Schema retrieval failed: {str(e)}")
    
    async def get_table_data(self, table_name: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Get data from a specific table with pagination."""
        try:
            # Validate inputs
            if not table_name or not table_name.replace("_", "").isalnum():
                raise ValidationError("Invalid table name")
            
            if limit > 1000:
                raise ValidationError("Limit cannot exceed 1000")
            
            # Get data
            data_query = f"SELECT * FROM {table_name} LIMIT %s OFFSET %s"
            results = execute_query(data_query, (limit, offset))
            
            # Get total count
            count_query = f"SELECT COUNT(*) as total FROM {table_name}"
            count_result = execute_query(count_query)
            total_count = count_result[0]["total"] if count_result else 0
            
            return {
                "success": True,
                "table_name": table_name,
                "data": results,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total": total_count,
                    "has_more": offset + limit < total_count
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error("Failed to get table data", error=str(e))
            raise ExternalServiceError(f"Data retrieval failed: {str(e)}")
    
    async def get_analytics_metrics(self, time_period: str = "7d") -> Dict[str, Any]:
        """Get analytics metrics for a specific time period."""
        try:
            # Parse time period
            if time_period.endswith("d"):
                days = int(time_period[:-1])
            elif time_period.endswith("h"):
                days = int(time_period[:-1]) / 24
            else:
                days = 7
            
            # Get engagement metrics
            engagement_query = """
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as total_statements,
                COUNT(DISTINCT JSON_EXTRACT_SCALAR(actor, '$.mbox')) as unique_users,
                COUNT(DISTINCT JSON_EXTRACT_SCALAR(object, '$.id')) as unique_activities
            FROM xapi_statements
            WHERE timestamp >= NOW() - INTERVAL '%s days'
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
            """
            
            engagement_data = execute_query(engagement_query % days)
            
            # Get completion rates
            completion_query = """
            SELECT 
                JSON_EXTRACT_SCALAR(object, '$.id') as activity_id,
                COUNT(*) as total_attempts,
                COUNT(CASE WHEN JSON_EXTRACT_SCALAR(verb, '$.id') LIKE '%completed%' THEN 1 END) as completions,
                ROUND(
                    COUNT(CASE WHEN JSON_EXTRACT_SCALAR(verb, '$.id') LIKE '%completed%' THEN 1 END) * 100.0 / COUNT(*), 2
                ) as completion_rate
            FROM xapi_statements
            WHERE timestamp >= NOW() - INTERVAL '%s days'
            GROUP BY JSON_EXTRACT_SCALAR(object, '$.id')
            HAVING COUNT(*) >= 5
            ORDER BY completion_rate DESC
            LIMIT 10
            """
            
            completion_data = execute_query(completion_query % days)
            
            return {
                "success": True,
                "time_period": time_period,
                "engagement_metrics": engagement_data,
                "completion_metrics": completion_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get analytics metrics", error=str(e))
            raise ExternalServiceError(f"Analytics metrics failed: {str(e)}")

