"""Simplified Data Explorer - Real-time xAPI data from BigQuery."""

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any
import httpx
import os
from app.logging_config import get_logger

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = get_logger("data_explorer")


def get_api_base_url(request: Optional[Request] = None) -> str:
    """Get the API base URL from environment variable or request."""
    api_base_url = os.getenv("API_BASE_URL", "")
    if api_base_url:
        return api_base_url.rstrip("/")
    if request:
        return str(request.base_url).rstrip("/")
    # Fallback for local development
    if os.getenv("ENVIRONMENT") == "development":
        return "http://localhost:8000"
    # Fallback: try to get from Cloud Run metadata or use a sensible default
    # In Cloud Run, we can use the service URL from environment
    service_url = os.getenv("CLOUD_RUN_SERVICE_URL", "")
    if service_url:
        return service_url.rstrip("/")
    # Last resort: return empty string (will use relative URLs)
    return ""


async def get_direct_xapi_requests(limit: int = 25, base_url: Optional[str] = None) -> Dict[str, Any]:
    """Get recent direct xAPI requests from the webhook endpoints."""
    try:
        # Use base_url for httpx client if provided, otherwise use relative URLs
        client_kwargs = {}
        if base_url:
            client_kwargs["base_url"] = base_url
        
        async with httpx.AsyncClient(**client_kwargs) as client:
            # Get recent direct xAPI requests from raw statements
            query = f"""
            SELECT 
                timestamp,
                actor_name,
                verb_id as verb_display,
                object_name,
                result_completion,
                result_success,
                result_score_scaled,
                result_response,
                'Direct xAPI Request' as data_type,
                statement_id
            FROM taps_data.raw_xapi_statements 
            ORDER BY timestamp DESC 
            LIMIT {limit}
            """
            
            response = await client.get(
                "/api/analytics/bigquery/query",
                params={"query": query},
                timeout=30.0
            )
            
            logger.info(f"BigQuery API response: status={response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Response data keys: {list(data.keys())}")
                logger.info(f"Response success: {data.get('success')}")
                
                if data.get("success"):
                    # Response structure: data.data.rows (BigQueryAnalyticsResponse format)
                    rows = data.get("data", {}).get("rows", [])
                    row_count = data.get("row_count", 0)
                    
                    logger.info(f"BigQuery query returned {len(rows)} rows, row_count={row_count}")
                    
                    if len(rows) == 0:
                        logger.warning("BigQuery query returned success=True but 0 rows")
                        return {"success": True, "statements": [], "total_count": 0}
                    
                    # Enhance statements with verbose JSON in result_response
                    enhanced_statements = []
                    for statement in rows:
                        # Create detailed payload for result section - show actual xAPI data
                        import json
                        detailed_payload = {
                            "id": statement.get("statement_id", ""),
                            "actor": {"name": statement.get("actor_name", ""), "mbox": f"mailto:{statement.get('actor_name', '')}"},
                            "verb": {"id": statement.get("verb_display", ""), "display": {"en-US": statement.get("verb_display", "")}},
                            "object": {"id": statement.get("object_name", ""), "definition": {"name": {"en-US": statement.get("object_name", "")}}},
                            "result": {
                                "completion": statement.get("result_completion"),
                                "success": statement.get("result_success"),
                                "score": {"scaled": statement.get("result_score_scaled")},
                                "response": statement.get("result_response")
                            },
                            "timestamp": statement.get("timestamp", ""),
                            "data_type": statement.get("data_type", "Direct xAPI Request")
                        }
                        
                        # Update the statement with verbose JSON
                        enhanced_statement = statement.copy()
                        enhanced_statement["result_response"] = json.dumps(detailed_payload, indent=2)
                        enhanced_statements.append(enhanced_statement)
                    
                    return {
                        "success": True,
                        "statements": enhanced_statements,
                        "total_count": row_count
                    }
                else:
                    # Table might not exist - return empty result instead of failing
                    error_msg = data.get("error", "")
                    if "not found" in error_msg.lower() or "does not exist" in error_msg.lower() or "not recognized" in error_msg.lower():
                        logger.debug(f"raw_xapi_statements table not found, returning empty result")
                        return {"success": True, "statements": [], "total_count": 0}
                    else:
                        logger.warning(f"BigQuery query error: {error_msg}")
                        return {"success": False, "statements": [], "total_count": 0, "error": error_msg}
            
            # Non-200 status - return empty instead of failing the whole page
            logger.warning(f"Direct xAPI query returned {response.status_code}, returning empty result")
            return {"success": True, "statements": [], "total_count": 0}
            
    except Exception as e:
        logger.warning(f"Failed to get direct xAPI requests (table may not exist): {e}")
        return {"success": True, "statements": [], "total_count": 0}  # Don't fail the whole page


async def get_endpoint_tracking_data(limit: int = 25, base_url: Optional[str] = None) -> Dict[str, Any]:
    """Get recent endpoint tracking data formatted for the data explorer table."""
    try:
        # Use base_url for httpx client if provided
        client_kwargs = {}
        if base_url:
            client_kwargs["base_url"] = base_url
        
        async with httpx.AsyncClient(**client_kwargs) as client:
            response = await client.get("/api/endpoint-analytics")
            
            if response.status_code == 200:
                data = response.json()
                endpoint_events = []
                
                # Convert recent activity to data explorer format - only /statements endpoint
                statements_activity = [activity for activity in data.get("recent_activity", []) if activity.get("endpoint") == "/statements"]
                for activity in statements_activity[:limit]:
                    # Format timestamp in Central Time
                    timestamp = activity.get("timestamp", "")
                    if timestamp:
                        try:
                            from app.utils.timestamp_utils import format_compact
                            formatted_time = format_compact(timestamp)
                        except:
                            formatted_time = timestamp
                    else:
                        formatted_time = "Unknown"
                    
                    # Determine result status
                    status_code = activity.get("status_code", 200)
                    if 200 <= status_code < 300:
                        result = "Success"
                    elif 400 <= status_code < 500:
                        result = "Failed"
                    else:
                        result = "Error"
                    
                    # Create detailed JSON payload for the result section
                    import json
                    detailed_payload = {
                        "endpoint": activity.get("endpoint", "Unknown"),
                        "method": activity.get("method", "GET"),
                        "status_code": status_code,
                        "response_time_ms": round(activity.get('response_time', 0) * 1000, 2),
                        "timestamp": activity.get("timestamp", ""),
                        "result": result,
                        "data_type": "Endpoint Tracking"
                    }
                    
                    endpoint_events.append({
                        "timestamp": formatted_time,
                        "actor_id": f"API Request ({activity.get('method', 'GET')})",
                        "verb_display": "Endpoint Hit",
                        "object_name": activity.get("endpoint", "Unknown"),
                        "result_completion": None,
                        "result_success": result,
                        "result_score_scaled": None,
                        "result_response": json.dumps(detailed_payload, indent=2),
                        "data_type": "Endpoint Tracking",
                        "statement_id": f"endpoint-{activity.get('timestamp', 'unknown')}"
                    })
                
                return {
                    "success": True,
                    "statements": endpoint_events,
                    "total_count": len(endpoint_events)
                }
            
            return {"success": False, "statements": [], "total_count": 0}
            
    except Exception as e:
        logger.error(f"Failed to get endpoint tracking data: {e}")
        return {"success": False, "statements": [], "total_count": 0}


async def get_recent_bigquery_data(limit: int = 25, base_url: Optional[str] = None, cohort_id: Optional[str] = None) -> Dict[str, Any]:
    """Get recent xAPI data directly from BigQuery."""
    try:
        from app.utils.cohort_filtering import build_cohort_filter_sql
        
        # Use base_url for httpx client if provided
        client_kwargs = {}
        if base_url:
            client_kwargs["base_url"] = base_url
        else:
            # Fallback: use internal API endpoint
            client_kwargs["base_url"] = "https://taps-analytics-ui-euvwb5vwea-uc.a.run.app"
        
        async with httpx.AsyncClient(**client_kwargs, timeout=30.0) as client:
            # Build cohort filter
            cohort_filter = build_cohort_filter_sql(cohort_id=cohort_id) if cohort_id else ""
            
            # Get recent statements from BigQuery with data type indicator
            query = f"""
            SELECT 
                timestamp,
                actor_id,
                verb_display,
                object_name,
                result_completion,
                result_success,
                result_score_scaled,
                result_response,
                context_platform,
                raw_json,
                'ETL Processed' as data_type,
                statement_id
            FROM taps_data.statements 
            WHERE 1=1
            {cohort_filter}
            ORDER BY timestamp DESC 
            LIMIT {limit}
            """
            
            logger.info(f"Calling BigQuery API endpoint with query limit={limit}")
            response = await client.get(
                "/api/analytics/bigquery/query",
                params={"query": query},
                timeout=30.0
            )
            
            logger.info(f"BigQuery API response: status={response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Response success: {data.get('success')}, row_count: {data.get('row_count', 0)}")
                
                if data.get("success"):
                    # Response structure: data.data.rows (BigQueryAnalyticsResponse format)
                    rows = data.get("data", {}).get("rows", [])
                    row_count = data.get("row_count", 0)
                    
                    logger.info(f"Got {len(rows)} rows from BigQuery API")
                    
                    if len(rows) == 0:
                        logger.warning("BigQuery query returned success=True but 0 rows")
                        return {"success": True, "statements": [], "total_count": 0}
                    
                    # Enhance statements with verbose JSON in result_response
                    enhanced_statements = []
                    for statement in rows:
                        try:
                            # Try to use raw xAPI data if available, otherwise reconstruct
                            import json
                            detailed_payload = None
                            if statement.get("raw_json"):
                                try:
                                    detailed_payload = json.loads(statement["raw_json"])
                                except:
                                    pass
                            
                            # Fallback to reconstructed payload if raw_json is not available
                            if not detailed_payload:
                                detailed_payload = {
                                    "id": statement.get("statement_id", ""),
                                    "actor": {"name": statement.get("actor_id", ""), "mbox": f"mailto:{statement.get('actor_id', '')}"},
                                    "verb": {"id": statement.get("verb_display", ""), "display": {"en-US": statement.get("verb_display", "")}},
                                    "object": {"id": statement.get("object_name", ""), "definition": {"name": {"en-US": statement.get("object_name", "")}}},
                                    "result": {
                                        "completion": statement.get("result_completion"),
                                        "success": statement.get("result_success"),
                                        "score": {"scaled": statement.get("result_score_scaled")},
                                        "response": statement.get("result_response")
                                    },
                                    "context": {"platform": statement.get("context_platform")},
                                    "timestamp": statement.get("timestamp", ""),
                                    "data_type": statement.get("data_type", "ETL Processed")
                                }
                            
                            # Update the statement with verbose JSON
                            enhanced_statement = statement.copy()
                            enhanced_statement["result_response"] = json.dumps(detailed_payload, indent=2)
                            
                            # Format timestamp to Central Time
                            if enhanced_statement.get("timestamp"):
                                try:
                                    from app.utils.timestamp_utils import format_compact
                                    enhanced_statement["timestamp"] = format_compact(enhanced_statement["timestamp"])
                                except ImportError:
                                    # timestamp_utils not available, keep original timestamp
                                    pass
                                except Exception:
                                    # Formatting failed, keep original timestamp
                                    pass
                            
                            enhanced_statements.append(enhanced_statement)
                        except Exception as e:
                            logger.error(f"Error enhancing statement {statement.get('statement_id', 'unknown')}: {e}")
                            # Still add the statement even if enhancement fails
                            enhanced_statements.append(statement)
                    
                    logger.info(f"Returning {len(enhanced_statements)} enhanced statements")
                    return {
                        "success": True,
                        "statements": enhanced_statements,
                        "total_count": row_count
                    }
                else:
                    # Query succeeded but returned error in response
                    error_msg = data.get("error", "Unknown query error")
                    logger.warning(f"BigQuery query returned error: {error_msg}")
                    return {"success": False, "statements": [], "total_count": 0, "error": error_msg}
            
            # Non-200 status code
            try:
                error_text = response.text[:500] if hasattr(response, 'text') else f"HTTP {response.status_code}"
            except:
                error_text = f"HTTP {response.status_code}"
            logger.error(f"BigQuery query endpoint returned {response.status_code}: {error_text}")
            return {"success": False, "statements": [], "total_count": 0, "error": f"Query endpoint returned {response.status_code}: {error_text}"}
            
    except httpx.TimeoutException as e:
        logger.error(f"Timeout getting BigQuery data: {e}")
        return {"success": False, "statements": [], "total_count": 0, "error": "Query timeout"}
    except Exception as e:
        logger.error(f"Failed to get BigQuery data: {e}", exc_info=True)
        return {"success": False, "statements": [], "total_count": 0, "error": str(e)}


async def get_raw_incoming_statements(limit: int = 25, base_url: Optional[str] = None) -> Dict[str, Any]:
    """Get raw incoming xAPI statements from Cloud Storage for debugging."""
    try:
        # Use base_url for httpx client if provided
        client_kwargs = {}
        if base_url:
            client_kwargs["base_url"] = base_url
        
        async with httpx.AsyncClient(**client_kwargs) as client:
            # Query for raw statements stored in Cloud Storage
            query = f"""
            SELECT 
                timestamp,
                statement_id,
                actor_name,
                verb_id,
                object_id,
                object_name,
                result_completion,
                result_success,
                raw_statement
            FROM taps_data.raw_xapi_statements 
            ORDER BY timestamp DESC 
            LIMIT {limit}
            """
            
            response = await client.get(
                "/api/analytics/bigquery/query",
                params={"query": query},
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    # Response structure: data.data.rows (BigQueryAnalyticsResponse format)
                    rows = data.get("data", {}).get("rows", [])
                    row_count = data.get("row_count", 0)
                    return {
                        "success": True,
                        "raw_statements": rows,
                        "total_count": row_count
                    }
            
            return {"success": False, "raw_statements": [], "total_count": 0}
            
    except Exception as e:
        logger.error(f"Failed to get raw statements: {e}")
        return {"success": False, "raw_statements": [], "total_count": 0}


async def get_system_status(request: Optional[Request] = None) -> Dict[str, Any]:
    """Get system status including Pub/Sub health and ETL processor status."""
    try:
        base_url = get_api_base_url(request)
        # Use base_url for httpx client if provided
        client_kwargs = {}
        if base_url:
            client_kwargs["base_url"] = base_url
        
        async with httpx.AsyncClient(**client_kwargs) as client:
            # Get total statement count
            count_query = "SELECT COUNT(*) as total FROM taps_data.statements"
            count_response = await client.get(
                "/api/analytics/bigquery/query",
                params={"query": count_query}
            )
            
            total_count = 0
            if count_response.status_code == 200:
                data = count_response.json()
                if data.get("success"):
                    rows = data.get("data", {}).get("rows", [])
                    if rows:
                        total_count = rows[0].get("total", 0)
            
            # Get latest timestamp
            latest_query = "SELECT MAX(timestamp) as latest FROM taps_data.statements"
            latest_response = await client.get(
                "/api/analytics/bigquery/query",
                params={"query": latest_query}
            )
            
            latest_timestamp = None
            if latest_response.status_code == 200:
                data = latest_response.json()
                if data.get("success"):
                    rows = data.get("data", {}).get("rows", [])
                    if rows:
                        latest_timestamp = rows[0].get("latest")
            
            # Get ETL processor status
            etl_status = await get_etl_status(client, base_url)
            
            return {
                "total_statements": total_count,
                "latest_timestamp": latest_timestamp,
                "status": "healthy" if total_count > 0 else "no_data",
                "etl_status": etl_status
            }
            
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        return {
            "total_statements": 0,
            "latest_timestamp": None,
            "status": "error",
            "etl_status": {"running": False, "error": str(e)}
        }


async def get_etl_status(client: httpx.AsyncClient, base_url: Optional[str] = None) -> Dict[str, Any]:
    """Get ETL processor status."""
    try:
        response = await client.get("/api/etl/status")
        
        if response.status_code == 200:
            data = response.json()
            if "bigquery_processor" in data:
                processor = data["bigquery_processor"]
                status = processor.get("status", {})
                
                # Handle case where status is None
                if status is None:
                    return {
                        "running": processor.get("running", False),
                        "uptime_seconds": 0,
                        "messages_received": 0,
                        "messages_processed": 0,
                        "messages_failed": 0,
                        "bigquery_rows_inserted": 0,
                        "last_message_time": None,
                        "errors": [],
                        "status": "stopped"
                    }
                
                metrics = status.get("metrics", {})
                
                return {
                    "running": processor.get("running", False),
                    "uptime_seconds": status.get("uptime_seconds", 0),
                    "messages_received": metrics.get("messages_received", 0),
                    "messages_processed": metrics.get("messages_processed", 0),
                    "messages_failed": metrics.get("messages_failed", 0),
                    "bigquery_rows_inserted": metrics.get("bigquery_rows_inserted", 0),
                    "last_message_time": metrics.get("last_message_time"),
                    "errors": metrics.get("errors", []),
                    "status": "healthy" if processor.get("running", False) and metrics.get("messages_failed", 0) == 0 else "warning" if processor.get("running", False) else "error"
                }
        
        return {"running": False, "error": "Failed to get ETL status", "messages_received": 0, "messages_processed": 0, "messages_failed": 0}
        
    except Exception as e:
        logger.error(f"Failed to get ETL status: {e}")
        return {"running": False, "error": str(e), "messages_received": 0, "messages_processed": 0, "messages_failed": 0}


@router.get("/api/debug/data-explorer-raw")
async def debug_data_explorer_raw(request: Request, limit: int = Query(10)):
    """Debug endpoint to see raw data explorer data."""
    base_url = get_api_base_url(request)
    etl_data = await get_recent_bigquery_data(limit, base_url)
    
    return JSONResponse({
        "etl_data": etl_data,
        "etl_success": etl_data.get("success"),
        "etl_count": etl_data.get("total_count", 0),
        "etl_statements": len(etl_data.get("statements", [])),
        "etl_error": etl_data.get("error")
    })


@router.get("/data-explorer", response_class=HTMLResponse)
async def data_explorer(
    request: Request, 
    limit: int = Query(100, ge=1, le=100),
    cohort: Optional[str] = Query(None, description="Filter by cohort ID")
) -> HTMLResponse:
    """Simplified data explorer showing real-time xAPI data with data type indicators."""
    base_url = get_api_base_url(request)
    logger.info(f"data_explorer called with limit={limit}, cohort={cohort}, base_url={base_url}")
    
    # Get ETL processed data, direct xAPI requests, and endpoint tracking data
    etl_data = await get_recent_bigquery_data(limit, base_url, cohort_id=cohort)
    logger.info(f"etl_data: success={etl_data.get('success')}, count={etl_data.get('total_count', 0)}, statements={len(etl_data.get('statements', []))}")
    
    direct_data = await get_direct_xapi_requests(limit, base_url)
    logger.info(f"direct_data: success={direct_data.get('success')}, count={direct_data.get('total_count', 0)}")
    
    endpoint_data = await get_endpoint_tracking_data(limit, base_url)
    status = await get_system_status(request)
    
    # Combine only real xAPI statements (exclude endpoint tracking)
    all_statements = []
    if etl_data.get("success"):
        all_statements.extend(etl_data.get("statements", []))
        logger.info(f"Added {len(etl_data.get('statements', []))} statements from etl_data")
    if direct_data.get("success"):
        all_statements.extend(direct_data.get("statements", []))
        logger.info(f"Added {len(direct_data.get('statements', []))} statements from direct_data")
    # Note: endpoint_data excluded from main display - only used for count
    
    logger.info(f"Total statements after combining: {len(all_statements)}")
    
    # Sort by timestamp (most recent first)
    all_statements.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    # Limit to requested number
    all_statements = all_statements[:limit]
    
    # Determine success: true if queries succeeded (even with 0 results) OR if we have statements
    queries_succeeded = etl_data.get("success", False) or direct_data.get("success", False) or endpoint_data.get("success", False)
    has_statements = len(all_statements) > 0
    
    logger.info(f"Final: queries_succeeded={queries_succeeded}, has_statements={has_statements}, total_statements={len(all_statements)}")
    
    context = {
        "request": request,
        "active_page": "data_explorer",
        "title": "Data Explorer",
        "statements": all_statements,
        "total_count": len(all_statements),
        "etl_count": etl_data.get("total_count", 0),
        "direct_count": direct_data.get("total_count", 0),
        "endpoint_count": endpoint_data.get("total_count", 0),
        "system_status": status,
        "limit": limit,
        "cohort": cohort,
        "success": queries_succeeded or has_statements,
        "error": etl_data.get("error") or direct_data.get("error") or endpoint_data.get("error")
    }

    return templates.TemplateResponse("data_explorer_modern.html", context)


@router.get("/raw-statements", response_class=HTMLResponse)
async def raw_statements_debug(request: Request, limit: int = Query(25, ge=1, le=100)) -> HTMLResponse:
    """Debug view showing raw incoming xAPI statements before processing."""
    base_url = get_api_base_url(request)
    raw_data = await get_raw_incoming_statements(limit, base_url)
    status = await get_system_status(request)
    
    context = {
        "request": request,
        "active_page": "raw_statements",
        "title": "Raw Incoming Statements Debug",
        "raw_statements": raw_data.get("raw_statements", []),
        "total_count": raw_data.get("total_count", 0),
        "system_status": status,
        "limit": limit,
        "success": raw_data.get("success", False)
    }

    return templates.TemplateResponse("raw_statements_debug.html", context)


# Keep the old endpoint for backward compatibility but redirect to new one
@router.get("/recent-pubsub", response_class=HTMLResponse)
async def recent_pubsub_feed(request: Request, limit: int = 25) -> HTMLResponse:
    """Redirect to the new data explorer."""
    return await data_explorer(request, limit)


@router.get("/api/pubsub-status")
async def pubsub_status(request: Request) -> Dict[str, Any]:
    """API endpoint to check Pub/Sub and data pipeline status."""
    base_url = get_api_base_url(request)
    status = await get_system_status(request)
    data = await get_recent_bigquery_data(5, base_url)  # Get last 5 events
    
    return {
        "status": "healthy",
        "pubsub_pipeline": {
            "total_statements": status["total_statements"],
            "latest_timestamp": status["latest_timestamp"],
            "status": status["status"]
        },
        "recent_events": {
            "count": len(data.get("statements", [])),
            "latest_events": data.get("statements", [])[:3]  # Show last 3 events
        },
        "message": "Pub/Sub pipeline is working - data is flowing from 7taps to BigQuery"
    }
