"""
User Matching UI for manually matching users between CSV and xAPI data.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from app.logging_config import get_logger
from app.config.gcp_config import get_gcp_config

logger = get_logger("user_matching")
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


class MergeUsersRequest(BaseModel):
    csv_email: str
    xapi_email: str


@router.get("/user-matching", response_class=HTMLResponse)
async def user_matching_page(request: Request) -> HTMLResponse:
    """User matching page for manually matching users."""
    context = {
        "request": request,
        "active_page": "user_matching",
        "title": "User Matching"
    }
    return templates.TemplateResponse("user_matching.html", context)


@router.get("/user-matching/data")
async def get_user_matching_data() -> JSONResponse:
    """Get data for user matching interface."""
    try:
        gcp_config = get_gcp_config()
        client = gcp_config.bigquery_client
        dataset_id = gcp_config.bigquery_dataset
        
        # Get CSV-only users (users with CSV data but no xAPI activities)
        csv_only_query = f"""
        SELECT 
            u.user_id,
            u.email,
            u.name,
            u.first_seen,
            u.last_seen,
            u.activity_count,
            JSON_EXTRACT_SCALAR(u.csv_data[OFFSET(0)], '$.Group') as cohort_group,
            JSON_EXTRACT_SCALAR(u.csv_data[OFFSET(0)], '$.Team') as cohort_team
        FROM `{dataset_id}.users` u
        WHERE 'csv' IN UNNEST(u.sources)
            AND NOT EXISTS (
                SELECT 1 FROM `{dataset_id}.user_activities` ua 
                WHERE ua.user_email = u.email
            )
        ORDER BY u.last_seen DESC
        LIMIT 50
        """
        
        # Get xAPI-only users (users with activities but no CSV data)
        xapi_only_query = f"""
        SELECT 
            u.user_id,
            u.email,
            u.name,
            u.first_seen,
            u.last_seen,
            u.activity_count
        FROM `{dataset_id}.users` u
        WHERE 'xapi' IN UNNEST(u.sources)
            AND NOT EXISTS (
                SELECT 1 FROM `{dataset_id}.csv_imports` ci 
                WHERE ci.normalized_user_id = u.user_id
            )
        ORDER BY u.activity_count DESC
        LIMIT 50
        """
        
        # Get duplicate emails
        duplicate_query = f"""
        SELECT 
            email,
            COUNT(*) as user_count,
            ARRAY_AGG(
                STRUCT(
                    user_id,
                    name,
                    sources,
                    activity_count,
                    first_seen,
                    last_seen
                )
            ) as users
        FROM `{dataset_id}.users`
        WHERE email IS NOT NULL 
            AND email != ''
        GROUP BY email
        HAVING COUNT(*) > 1
        ORDER BY user_count DESC
        LIMIT 20
        """
        
        # Execute queries
        csv_only_results = list(client.query(csv_only_query).result())
        xapi_only_results = list(client.query(xapi_only_query).result())
        duplicate_results = list(client.query(duplicate_query).result())
        
        # Format results
        csv_only_users = []
        for row in csv_only_results:
            cohort = f"{row.cohort_group or 'X'} {row.cohort_team or 'X'}".strip()
            csv_only_users.append({
                "user_id": row.user_id,
                "email": row.email,
                "name": row.name,
                "first_seen": row.first_seen.isoformat() if row.first_seen else None,
                "last_seen": row.last_seen.isoformat() if row.last_seen else None,
                "activity_count": row.activity_count,
                "cohort": cohort if cohort != "X X" else "Unassigned"
            })
        
        xapi_only_users = []
        for row in xapi_only_results:
            xapi_only_users.append({
                "user_id": row.user_id,
                "email": row.email,
                "name": row.name,
                "first_seen": row.first_seen.isoformat() if row.first_seen else None,
                "last_seen": row.last_seen.isoformat() if row.last_seen else None,
                "activity_count": row.activity_count
            })
        
        duplicate_users = []
        for row in duplicate_results:
            users = []
            for user in row.users:
                users.append({
                    "user_id": user.user_id,
                    "name": user.name,
                    "sources": user.sources,
                    "activity_count": user.activity_count,
                    "first_seen": user.first_seen.isoformat() if user.first_seen else None,
                    "last_seen": user.last_seen.isoformat() if user.last_seen else None
                })
            
            duplicate_users.append({
                "email": row.email,
                "user_count": row.user_count,
                "users": users
            })
        
        summary = {
            "csv_only_count": len(csv_only_users),
            "xapi_only_count": len(xapi_only_users),
            "duplicate_count": len(duplicate_users)
        }
        
        return JSONResponse({
            "success": True,
            "summary": summary,
            "csv_only_users": csv_only_users,
            "xapi_only_users": xapi_only_users,
            "duplicate_users": duplicate_users
        })
        
    except Exception as e:
        logger.error(f"Error getting user matching data: {e}")
        return JSONResponse({
            "success": False,
            "message": str(e)
        }, status_code=500)


@router.post("/user-matching/merge")
async def merge_users(request: MergeUsersRequest) -> JSONResponse:
    """Manually merge two users."""
    try:
        gcp_config = get_gcp_config()
        client = gcp_config.bigquery_client
        dataset_id = gcp_config.bigquery_dataset
        
        csv_email = request.csv_email.lower().strip()
        xapi_email = request.xapi_email.lower().strip()
        
        # Check if both users exist
        check_query = f"""
        SELECT 
            user_id,
            email,
            name,
            sources,
            activity_count,
            first_seen,
            last_seen
        FROM `{dataset_id}.users`
        WHERE email IN ('{csv_email}', '{xapi_email}')
        """
        
        results = list(client.query(check_query).result())
        
        if len(results) != 2:
            return JSONResponse({
                "success": False,
                "message": "One or both users not found"
            }, status_code=400)
        
        # Find which is CSV and which is xAPI
        csv_user = None
        xapi_user = None
        
        for user in results:
            if csv_email in user.sources and xapi_email not in user.sources:
                csv_user = user
            elif xapi_email in user.sources and csv_email not in user.sources:
                xapi_user = user
        
        if not csv_user or not xapi_user:
            return JSONResponse({
                "success": False,
                "message": "Users must be from different sources (one CSV, one xAPI)"
            }, status_code=400)
        
        # Merge users by updating the CSV user with xAPI data
        merge_query = f"""
        UPDATE `{dataset_id}.users`
        SET 
            sources = ARRAY_CONCAT(sources, ['{xapi_email}']),
            activity_count = activity_count + {xapi_user.activity_count},
            first_seen = LEAST(first_seen, TIMESTAMP('{xapi_user.first_seen.isoformat()}')),
            last_seen = GREATEST(last_seen, TIMESTAMP('{xapi_user.last_seen.isoformat()}')),
            updated_at = CURRENT_TIMESTAMP()
        WHERE user_id = '{csv_user.user_id}';
        
        -- Delete the xAPI user
        DELETE FROM `{dataset_id}.users`
        WHERE user_id = '{xapi_user.user_id}';
        """
        
        client.query(merge_query)
        
        logger.info(f"Merged users: {csv_email} + {xapi_email}")
        
        return JSONResponse({
            "success": True,
            "message": f"Successfully merged {csv_user.name or csv_email} with {xapi_user.name or xapi_email}"
        })
        
    except Exception as e:
        logger.error(f"Error merging users: {e}")
        return JSONResponse({
            "success": False,
            "message": str(e)
        }, status_code=500)
