"""
BigQuery Analytics API Router - BigQuery-powered analytics queries
This router provides standardized analytics endpoints for BigQuery data visualization.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from app.config.gcp_config import gcp_config
from app.config.bigquery_schema import bigquery_schema
from google.cloud import bigquery
from google.api_core import exceptions as google_exceptions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Response Models
class BigQueryAnalyticsResponse(BaseModel):
    success: bool = Field(..., description="Whether the query was successful")
    chart_type: str = Field(..., description="Type of chart for frontend rendering")
    data: Dict[str, Any] = Field(..., description="Chart data")
    title: str = Field(..., description="Chart title")
    error: Optional[str] = Field(None, description="Error message if query failed")
    execution_time: Optional[float] = Field(None, description="Query execution time in seconds")
    row_count: Optional[int] = Field(None, description="Number of rows returned")

class QueryRequest(BaseModel):
    query: str = Field(..., description="BigQuery SQL query to execute")
    chart_type: str = Field("table", description="Desired chart type for visualization")

def execute_bigquery_query(sql_query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute a BigQuery query and return structured results."""
    start_time = datetime.now()

    try:
        # Validate query is read-only
        sql_upper = sql_query.upper().strip()
        if any(keyword in sql_upper for keyword in ['DELETE', 'DROP', 'UPDATE', 'INSERT', 'CREATE', 'ALTER', 'TRUNCATE']):
            raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")

        # Execute query
        client = gcp_config.bigquery_client
        job_config = bigquery.QueryJobConfig()

        if params:
            job_config.query_parameters = [
                bigquery.ScalarQueryParameter(key, "STRING", value)
                for key, value in params.items()
            ]

        query_job = client.query(sql_query, job_config=job_config)
        results = query_job.result()

        # Convert results to list of dicts
        rows = []
        for row in results:
            row_dict = {}
            for field_name in row.keys():
                value = row[field_name]
                # Convert datetime objects to strings
                if hasattr(value, 'isoformat'):
                    row_dict[field_name] = value.isoformat()
                else:
                    row_dict[field_name] = value
            rows.append(row_dict)

        execution_time = (datetime.now() - start_time).total_seconds()

        return {
            "success": True,
            "results": rows,
            "row_count": len(rows),
            "execution_time": execution_time,
            "query": sql_query
        }

    except google_exceptions.GoogleAPIError as e:
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"BigQuery error: {e}")
        return {
            "success": False,
            "results": [],
            "row_count": 0,
            "execution_time": execution_time,
            "error": f"BigQuery error: {str(e)}",
            "query": sql_query
        }
    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"Query execution failed: {e}")
        return {
            "success": False,
            "results": [],
            "row_count": 0,
            "execution_time": execution_time,
            "error": f"Query execution failed: {str(e)}",
            "query": sql_query
        }

@router.get("/bigquery/query",
    response_model=BigQueryAnalyticsResponse,
    summary="Execute custom BigQuery analytics query",
    description="Execute a custom BigQuery query and return results for visualization"
)
async def execute_custom_query(
    query: str = Query(..., description="BigQuery SQL query to execute"),
    chart_type: str = Query("table", description="Chart type for visualization")
):
    """Execute a custom BigQuery query."""
    logger.info(f"Executing BigQuery query: {query[:100]}...")

    result = execute_bigquery_query(query)

    if not result["success"]:
        return BigQueryAnalyticsResponse(
            success=False,
            chart_type=chart_type,
            data={},
            title="Custom Query",
            error=result["error"],
            execution_time=result["execution_time"],
            row_count=result["row_count"]
        )

    return BigQueryAnalyticsResponse(
        success=True,
        chart_type=chart_type,
        data={
            "columns": list(result["results"][0].keys()) if result["results"] else [],
            "rows": result["results"],
            "query": query
        },
        title=f"Custom Query Results ({result['row_count']} rows)",
        execution_time=result["execution_time"],
        row_count=result["row_count"]
    )

@router.get("/bigquery/learner-activity-summary",
    response_model=BigQueryAnalyticsResponse,
    summary="Learner activity summary from BigQuery",
    description="Get comprehensive learner activity statistics from BigQuery"
)
async def get_learner_activity_summary():
    """Get learner activity summary from BigQuery."""
    query = f"""
        SELECT
            actor_id,
            COUNT(*) as total_statements,
            COUNT(DISTINCT verb_id) as unique_verbs,
            COUNT(DISTINCT object_id) as unique_activities,
            MIN(timestamp) as first_activity,
            MAX(timestamp) as last_activity,
            AVG(CASE WHEN result_score_scaled IS NOT NULL THEN result_score_scaled END) as avg_score_scaled,
            COUNT(CASE WHEN result_success = true THEN 1 END) as successful_attempts,
            COUNT(CASE WHEN result_completion = true THEN 1 END) as completed_activities
        FROM `{gcp_config.project_id}.{gcp_config.bigquery_dataset}.statements`
        GROUP BY actor_id
        ORDER BY total_statements DESC
        LIMIT 50
    """

    result = execute_bigquery_query(query)

    if not result["success"]:
        return BigQueryAnalyticsResponse(
            success=False,
            chart_type="table",
            data={},
            title="Learner Activity Summary",
            error=result["error"],
            execution_time=result["execution_time"],
            row_count=result["row_count"]
        )

    # Prepare table data for frontend
    columns = [
        {"field": "actor_id", "headerName": "Learner ID", "width": 200},
        {"field": "total_statements", "headerName": "Total Activities", "width": 150},
        {"field": "unique_verbs", "headerName": "Unique Verbs", "width": 120},
        {"field": "unique_activities", "headerName": "Unique Activities", "width": 150},
        {"field": "first_activity", "headerName": "First Activity", "width": 180},
        {"field": "last_activity", "headerName": "Last Activity", "width": 180},
        {"field": "avg_score_scaled", "headerName": "Avg Score", "width": 120},
        {"field": "successful_attempts", "headerName": "Success Count", "width": 130},
        {"field": "completed_activities", "headerName": "Completed", "width": 120}
    ]

    return BigQueryAnalyticsResponse(
        success=True,
        chart_type="table",
        data={
            "columns": columns,
            "rows": result["results"],
            "total_count": len(result["results"])
        },
        title="Learner Activity Summary",
        execution_time=result["execution_time"],
        row_count=result["row_count"]
    )

@router.get("/bigquery/verb-distribution",
    response_model=BigQueryAnalyticsResponse,
    summary="Verb distribution analysis",
    description="Analyze the distribution of different learning activity verbs"
)
async def get_verb_distribution():
    """Get verb distribution from BigQuery."""
    query = f"""
        SELECT
            verb_display,
            verb_id,
            COUNT(*) as frequency,
            COUNT(DISTINCT actor_id) as unique_learners,
            AVG(CASE WHEN result_score_scaled IS NOT NULL THEN result_score_scaled END) as avg_score,
            COUNT(CASE WHEN result_success = true THEN 1 END) as success_count
        FROM `{gcp_config.project_id}.{gcp_config.bigquery_dataset}.statements`
        WHERE verb_display IS NOT NULL
        GROUP BY verb_display, verb_id
        ORDER BY frequency DESC
        LIMIT 20
    """

    result = execute_bigquery_query(query)

    if not result["success"]:
        return BigQueryAnalyticsResponse(
            success=False,
            chart_type="bar",
            data={},
            title="Verb Distribution",
            error=result["error"],
            execution_time=result["execution_time"],
            row_count=result["row_count"]
        )

    # Prepare chart data
    labels = [r.get('verb_display', r.get('verb_id', 'Unknown')) for r in result["results"]]
    frequencies = [r['frequency'] for r in result["results"]]
    success_rates = []
    for r in result["results"]:
        total = r['frequency']
        success = r['success_count']
        rate = (success / total * 100) if total > 0 else 0
        success_rates.append(round(rate, 1))

    return BigQueryAnalyticsResponse(
        success=True,
        chart_type="bar",
        data={
            "labels": labels,
            "datasets": [
                {
                    "label": "Activity Count",
                    "data": frequencies,
                    "backgroundColor": "#6366f1",
                    "borderColor": "#6366f1",
                    "borderWidth": 1
                },
                {
                    "label": "Success Rate (%)",
                    "data": success_rates,
                    "backgroundColor": "#10b981",
                    "borderColor": "#10b981",
                    "borderWidth": 1,
                    "type": "line",
                    "yAxisID": "y1"
                }
            ],
            "raw_data": result["results"]
        },
        title="Learning Activity Verb Distribution",
        execution_time=result["execution_time"],
        row_count=result["row_count"]
    )

@router.get("/bigquery/activity-timeline",
    response_model=BigQueryAnalyticsResponse,
    summary="Activity timeline analysis",
    description="Show learning activity patterns over time"
)
async def get_activity_timeline(days: int = Query(30, description="Number of days to analyze")):
    """Get activity timeline from BigQuery."""
    query = f"""
        SELECT
            DATE(timestamp) as activity_date,
            COUNT(*) as total_activities,
            COUNT(DISTINCT actor_id) as unique_learners,
            COUNT(DISTINCT verb_id) as unique_verbs,
            COUNT(CASE WHEN result_success = true THEN 1 END) as successful_activities,
            AVG(CASE WHEN result_score_scaled IS NOT NULL THEN result_score_scaled END) as avg_score
        FROM `{gcp_config.project_id}.{gcp_config.bigquery_dataset}.statements`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
        GROUP BY DATE(timestamp)
        ORDER BY activity_date
    """

    result = execute_bigquery_query(query)

    if not result["success"]:
        return BigQueryAnalyticsResponse(
            success=False,
            chart_type="line",
            data={},
            title="Activity Timeline",
            error=result["error"],
            execution_time=result["execution_time"],
            row_count=result["row_count"]
        )

    # Prepare chart data
    dates = [r['activity_date'] for r in result["results"]]
    total_activities = [r['total_activities'] for r in result["results"]]
    unique_learners = [r['unique_learners'] for r in result["results"]]
    successful_activities = [r['successful_activities'] for r in result["results"]]

    return BigQueryAnalyticsResponse(
        success=True,
        chart_type="line",
        data={
            "labels": dates,
            "datasets": [
                {
                    "label": "Total Activities",
                    "data": total_activities,
                    "borderColor": "#6366f1",
                    "backgroundColor": "rgba(99, 102, 241, 0.1)",
                    "tension": 0.4
                },
                {
                    "label": "Unique Learners",
                    "data": unique_learners,
                    "borderColor": "#10b981",
                    "backgroundColor": "rgba(16, 185, 129, 0.1)",
                    "tension": 0.4
                },
                {
                    "label": "Successful Activities",
                    "data": successful_activities,
                    "borderColor": "#f59e0b",
                    "backgroundColor": "rgba(245, 158, 11, 0.1)",
                    "tension": 0.4
                }
            ],
            "raw_data": result["results"]
        },
        title=f"Learning Activity Timeline (Last {days} Days)",
        execution_time=result["execution_time"],
        row_count=result["row_count"]
    )

@router.get("/bigquery/connection-status",
    summary="BigQuery connection status",
    description="Check BigQuery connection and dataset status"
)
async def get_bigquery_connection_status():
    """Check BigQuery connection status."""
    try:
        # Test BigQuery client connection
        client = gcp_config.bigquery_client

        # Get dataset info
        dataset_ref = client.dataset(gcp_config.bigquery_dataset)
        dataset = client.get_dataset(dataset_ref)

        # Get table info
        tables = list(client.list_tables(dataset_ref))
        table_info = {}
        total_rows = 0

        for table in tables:
            table_ref = dataset_ref.table(table.table_id)
            table_obj = client.get_table(table_ref)
            table_info[table.table_id] = {
                "row_count": table_obj.num_rows,
                "size_bytes": table_obj.num_bytes,
                "created": table_obj.created.isoformat() if table_obj.created else None,
                "last_modified": table_obj.modified.isoformat() if table_obj.modified else None
            }
            total_rows += table_obj.num_rows

        return {
            "status": "connected",
            "project_id": gcp_config.project_id,
            "dataset_id": gcp_config.bigquery_dataset,
            "dataset_exists": True,
            "tables_count": len(tables),
            "total_rows": total_rows,
            "tables": table_info,
            "last_checked": datetime.now().isoformat()
        }

    except google_exceptions.NotFound:
        return {
            "status": "dataset_not_found",
            "project_id": gcp_config.project_id,
            "dataset_id": gcp_config.bigquery_dataset,
            "dataset_exists": False,
            "error": f"Dataset '{gcp_config.bigquery_dataset}' not found",
            "last_checked": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"BigQuery connection error: {e}")
        return {
            "status": "error",
            "project_id": gcp_config.project_id,
            "dataset_id": gcp_config.bigquery_dataset,
            "dataset_exists": False,
            "error": str(e),
            "last_checked": datetime.now().isoformat()
        }

@router.get("/bigquery/health", summary="BigQuery analytics API health check")
async def bigquery_analytics_health():
    """Health check for BigQuery analytics API."""
    return {
        "status": "healthy",
        "service": "bigquery-analytics-api",
        "endpoints": [
            "/api/analytics/bigquery/query",
            "/api/analytics/bigquery/learner-activity-summary",
            "/api/analytics/bigquery/verb-distribution",
            "/api/analytics/bigquery/activity-timeline",
            "/api/debug/bigquery-connection-status"
        ],
        "bigquery_config": {
            "project_id": gcp_config.project_id,
            "dataset_id": gcp_config.bigquery_dataset,
            "location": gcp_config.location
        }
    }
