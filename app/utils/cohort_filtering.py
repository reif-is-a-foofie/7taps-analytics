"""
Cohort Filtering Utilities

Provides helper functions for filtering BigQuery queries by cohort.
Cohorts are stored in statement extensions: context.extensions["https://7taps.com/csv-metadata"].cohort_id
"""

from typing import Optional
from app.logging_config import get_logger
from app.config.gcp_config import get_gcp_config

logger = get_logger("cohort_filtering")


def build_cohort_filter_sql(cohort_id: Optional[str] = None, cohort_name: Optional[str] = None) -> str:
    """
    Build SQL WHERE clause for filtering by cohort.
    
    Args:
        cohort_id: Filter by cohort_id (e.g., "uvm_uvm")
        cohort_name: Filter by cohort_name (e.g., "UVM UVM")
    
    Returns:
        SQL WHERE clause string (empty if no filter)
    """
    if not cohort_id and not cohort_name:
        return ""
    
    # Cohort data is stored in raw_json as:
    # context.extensions["https://7taps.com/csv-metadata"].cohort_id
    # or context.extensions["https://7taps.com/csv-metadata"].cohort_name
    
    conditions = []
    
    if cohort_id:
        # Filter by cohort_id
        conditions.append(
            f"JSON_EXTRACT_SCALAR(raw_json, '$.context.extensions.\"https://7taps.com/csv-metadata\".cohort_id') = '{cohort_id}'"
        )
    
    if cohort_name:
        # Filter by cohort_name
        conditions.append(
            f"JSON_EXTRACT_SCALAR(raw_json, '$.context.extensions.\"https://7taps.com/csv-metadata\".cohort_name') = '{cohort_name}'"
        )
    
    if conditions:
        return f"AND ({' OR '.join(conditions)})"
    
    return ""


def get_cohort_from_statement(statement: dict) -> Optional[dict]:
    """
    Extract cohort information from a statement.
    
    Returns:
        Dict with cohort_id and cohort_name, or None if not found
    """
    try:
        context = statement.get("context", {})
        extensions = context.get("extensions", {})
        csv_metadata = extensions.get("https://7taps.com/csv-metadata", {})
        
        if csv_metadata:
            return {
                "cohort_id": csv_metadata.get("cohort_id"),
                "cohort_name": csv_metadata.get("cohort_name"),
                "team": csv_metadata.get("team"),
                "group": csv_metadata.get("group")
            }
    except Exception as e:
        logger.debug(f"Error extracting cohort from statement: {e}")
    
    return None


async def get_available_cohorts_from_statements() -> list:
    """
    Get list of all available cohorts from statements table.
    
    Returns:
        List of cohort dicts with cohort_id, cohort_name, and counts
    """
    try:
        gcp_config = get_gcp_config()
        client = gcp_config.bigquery_client
        dataset_id = gcp_config.bigquery_dataset
        
        query = f"""
        SELECT 
            JSON_EXTRACT_SCALAR(raw_json, '$.context.extensions."https://7taps.com/csv-metadata".cohort_id') as cohort_id,
            JSON_EXTRACT_SCALAR(raw_json, '$.context.extensions."https://7taps.com/csv-metadata".cohort_name') as cohort_name,
            COUNT(*) as statement_count,
            COUNT(DISTINCT actor_id) as user_count,
            MAX(timestamp) as last_activity
        FROM `{dataset_id}.statements`
        WHERE JSON_EXTRACT_SCALAR(raw_json, '$.context.extensions."https://7taps.com/csv-metadata".cohort_id') IS NOT NULL
        GROUP BY cohort_id, cohort_name
        ORDER BY statement_count DESC
        """
        
        results = list(client.query(query).result())
        
        cohorts = []
        for row in results:
            if row.cohort_id:
                cohorts.append({
                    "cohort_id": row.cohort_id,
                    "cohort_name": row.cohort_name or row.cohort_id,
                    "statement_count": row.statement_count,
                    "user_count": row.user_count,
                    "last_activity": row.last_activity.isoformat() if row.last_activity else None
                })
        
        return cohorts
        
    except Exception as e:
        logger.error(f"Error getting available cohorts: {e}")
        return []


async def get_available_cohorts_from_users() -> list:
    """
    Get list of all available cohorts from cohorts table (preferred) or users table (fallback).
    
    Returns:
        List of cohort dicts with cohort_id, cohort_name, and user counts
    """
    try:
        gcp_config = get_gcp_config()
        client = gcp_config.bigquery_client
        dataset_id = gcp_config.bigquery_dataset
        
        # Try to get from cohorts table first
        try:
            query = f"""
            SELECT 
                cohort_id,
                cohort_name,
                team,
                group_name,
                user_count,
                statement_count,
                last_activity
            FROM `{dataset_id}.cohorts`
            WHERE active = TRUE
            ORDER BY user_count DESC
            """
            
            results = list(client.query(query).result())
            
            cohorts = []
            for row in results:
                cohorts.append({
                    "cohort_id": row.cohort_id,
                    "cohort_name": row.cohort_name,
                    "team": row.team,
                    "group": row.group_name,
                    "user_count": row.user_count,
                    "statement_count": getattr(row, 'statement_count', 0),
                    "last_activity": row.last_activity.isoformat() if row.last_activity else None
                })
            
            if cohorts:
                return cohorts
        except Exception as e:
            logger.debug(f"cohorts table not available, falling back to users table: {e}")
        
        # Fallback to users table if cohorts table doesn't exist
        query = f"""
        SELECT 
            csv_data[OFFSET(0)].group as group_name,
            csv_data[OFFSET(0)].team as team_name,
            COUNT(*) as user_count
        FROM `{dataset_id}.users`
        WHERE csv_data IS NOT NULL 
            AND ARRAY_LENGTH(csv_data) > 0
            AND csv_data[OFFSET(0)].group IS NOT NULL
        GROUP BY group_name, team_name
        ORDER BY user_count DESC
        """
        
        results = list(client.query(query).result())
        
        cohorts = []
        for row in results:
            group = row.group_name or "X"
            team = row.team_name or "X"
            cohort_name = f"{group} {team}".strip()
            cohort_id = cohort_name.lower().replace(" ", "_").replace("-", "_")
            
            cohorts.append({
                "cohort_id": cohort_id,
                "cohort_name": cohort_name,
                "team": team,
                "group": group,
                "user_count": row.user_count
            })
        
        return cohorts
        
    except Exception as e:
        logger.error(f"Error getting cohorts from users: {e}")
        return []


async def get_all_available_cohorts() -> list:
    """
    Get all available cohorts from both statements and users tables.
    Combines and deduplicates results.
    
    Returns:
        List of unique cohorts with counts from both sources
    """
    statement_cohorts = await get_available_cohorts_from_statements()
    user_cohorts = await get_available_cohorts_from_users()
    
    # Combine and deduplicate by cohort_id
    cohort_map = {}
    
    # Add user cohorts first (they have user counts)
    for cohort in user_cohorts:
        cohort_id = cohort["cohort_id"]
        cohort_map[cohort_id] = cohort.copy()
        cohort_map[cohort_id]["statement_count"] = 0
    
    # Merge statement cohorts (they have statement counts)
    for cohort in statement_cohorts:
        cohort_id = cohort["cohort_id"]
        if cohort_id in cohort_map:
            cohort_map[cohort_id]["statement_count"] = cohort.get("statement_count", 0)
            cohort_map[cohort_id]["last_activity"] = cohort.get("last_activity")
        else:
            cohort_map[cohort_id] = cohort.copy()
            cohort_map[cohort_id]["user_count"] = 0
    
    return list(cohort_map.values())

