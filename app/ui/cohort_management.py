"""
Cohort Management UI
Allows creating, editing, and managing cohorts, plus matching them to user groups.
"""

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timezone

from app.config.gcp_config import get_gcp_config

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


class CohortCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    group_filter: Optional[str] = None
    team_filter: Optional[str] = None


class CohortUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    group_filter: Optional[str] = None
    team_filter: Optional[str] = None


class CohortGroupMappingRequest(BaseModel):
    cohort_id: str
    group_name: str
    team_name: Optional[str] = None


@router.get("/cohort-management", response_class=HTMLResponse)
async def cohort_management_page(request: Request) -> HTMLResponse:
    """Cohort management page."""
    context = {
        "request": request,
        "active_page": "cohort_management",
        "title": "Cohort Management"
    }
    return templates.TemplateResponse("cohort_management.html", context)


@router.get("/api/cohorts")
async def get_all_cohorts() -> JSONResponse:
    """Get all cohorts with their member counts."""
    try:
        gcp_config = get_gcp_config()
        client = gcp_config.bigquery_client
        dataset_id = gcp_config.bigquery_dataset
        
        # Get cohorts from the cohort_safety.json file
        cohorts_data = load_cohort_trigger_words()
        cohorts = cohorts_data.get("cohorts", {})
        
        # Get member counts for each cohort
        cohort_list = []
        for cohort_id, cohort_info in cohorts.items():
            # Count users in this cohort
            member_count = await get_cohort_member_count(cohort_id)
            
            cohort_list.append({
                "id": cohort_id,
                "name": cohort_info.get("name", cohort_id),
                "description": cohort_info.get("description", ""),
                "member_count": member_count,
                "word_count": len(cohort_info.get("words", [])),
                "created_at": cohort_info.get("created_at", ""),
                "active": cohort_info.get("active", True)
            })
        
        # Sort by member count (descending)
        cohort_list.sort(key=lambda x: x["member_count"], reverse=True)
        
        return JSONResponse({
            "success": True,
            "cohorts": cohort_list
        })
        
    except Exception as e:
        logger.error(f"Error getting cohorts: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.post("/api/cohorts")
async def create_cohort(request: CohortCreateRequest) -> JSONResponse:
    """Create a new cohort."""
    try:
        cohorts_data = load_cohort_trigger_words()
        cohorts = cohorts_data.get("cohorts", {})
        
        cohort_id = request.name.lower().replace(" ", "_").replace("-", "_")
        
        # Check if cohort already exists
        if cohort_id in cohorts:
            return JSONResponse({
                "success": False,
                "error": f"Cohort '{request.name}' already exists"
            }, status_code=400)
        
        # Create new cohort
        cohorts[cohort_id] = {
            "name": request.name,
            "description": request.description or f"Cohort: {request.name}",
            "group_filter": request.group_filter,
            "team_filter": request.team_filter,
            "words": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active": True
        }
        
        cohorts_data["cohorts"] = cohorts
        save_cohort_trigger_words(cohorts_data)
        
        logger.info(f"Created cohort: {request.name} (ID: {cohort_id})")
        
        return JSONResponse({
            "success": True,
            "message": f"Cohort '{request.name}' created successfully",
            "cohort": {
                "id": cohort_id,
                "name": request.name,
                "description": request.description,
                "member_count": 0
            }
        })
        
    except Exception as e:
        logger.error(f"Error creating cohort: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.put("/api/cohorts/{cohort_id}")
async def update_cohort(cohort_id: str, request: CohortUpdateRequest) -> JSONResponse:
    """Update an existing cohort."""
    try:
        cohorts_data = load_cohort_trigger_words()
        cohorts = cohorts_data.get("cohorts", {})
        
        if cohort_id not in cohorts:
            return JSONResponse({
                "success": False,
                "error": f"Cohort '{cohort_id}' not found"
            }, status_code=404)
        
        # Update cohort fields
        cohort = cohorts[cohort_id]
        if request.name is not None:
            cohort["name"] = request.name
        if request.description is not None:
            cohort["description"] = request.description
        if request.group_filter is not None:
            cohort["group_filter"] = request.group_filter
        if request.team_filter is not None:
            cohort["team_filter"] = request.team_filter
        
        cohort["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        cohorts_data["cohorts"] = cohorts
        save_cohort_trigger_words(cohorts_data)
        
        logger.info(f"Updated cohort: {cohort_id}")
        
        return JSONResponse({
            "success": True,
            "message": f"Cohort '{cohort_id}' updated successfully"
        })
        
    except Exception as e:
        logger.error(f"Error updating cohort: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.delete("/api/cohorts/{cohort_id}")
async def delete_cohort(cohort_id: str) -> JSONResponse:
    """Delete a cohort."""
    try:
        cohorts_data = load_cohort_trigger_words()
        cohorts = cohorts_data.get("cohorts", {})
        
        if cohort_id not in cohorts:
            return JSONResponse({
                "success": False,
                "error": f"Cohort '{cohort_id}' not found"
            }, status_code=404)
        
        # Remove cohort
        cohort_name = cohorts[cohort_id]["name"]
        del cohorts[cohort_id]
        
        cohorts_data["cohorts"] = cohorts
        save_cohort_trigger_words(cohorts_data)
        
        logger.info(f"Deleted cohort: {cohort_id} ({cohort_name})")
        
        return JSONResponse({
            "success": True,
            "message": f"Cohort '{cohort_name}' deleted successfully"
        })
        
    except Exception as e:
        logger.error(f"Error deleting cohort: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.get("/api/cohorts/{cohort_id}/members")
async def get_cohort_members(cohort_id: str) -> JSONResponse:
    """Get members of a specific cohort."""
    try:
        gcp_config = get_gcp_config()
        client = gcp_config.bigquery_client
        dataset_id = gcp_config.bigquery_dataset
        
        # Get cohort info
        cohorts_data = load_cohort_trigger_words()
        cohorts = cohorts_data.get("cohorts", {})
        
        if cohort_id not in cohorts:
            return JSONResponse({
                "success": False,
                "error": f"Cohort '{cohort_id}' not found"
            }, status_code=404)
        
        cohort = cohorts[cohort_id]
        group_filter = cohort.get("group_filter")
        team_filter = cohort.get("team_filter")
        
        # Build query based on filters
        where_conditions = []
        if group_filter and group_filter != "X":
            where_conditions.append(f"JSON_EXTRACT_SCALAR(csv_data[OFFSET(0)], '$.Group') = '{group_filter}'")
        if team_filter and team_filter != "X":
            where_conditions.append(f"JSON_EXTRACT_SCALAR(csv_data[OFFSET(0)], '$.Team') = '{team_filter}'")
        
        if not where_conditions:
            # If no filters, get all users
            where_clause = "1=1"
        else:
            where_clause = " AND ".join(where_conditions)
        
        query = f"""
        SELECT 
            user_id,
            email,
            name,
            first_seen,
            last_seen,
            activity_count,
            JSON_EXTRACT_SCALAR(csv_data[OFFSET(0)], '$.Group') as group_name,
            JSON_EXTRACT_SCALAR(csv_data[OFFSET(0)], '$.Team') as team_name
        FROM `{dataset_id}.users`
        WHERE {where_clause}
        ORDER BY last_seen DESC
        LIMIT 100
        """
        
        results = list(client.query(query).result())
        
        members = []
        for row in results:
            members.append({
                "user_id": row.user_id,
                "email": row.email,
                "name": row.name,
                "first_seen": row.first_seen.isoformat() if row.first_seen else None,
                "last_seen": row.last_seen.isoformat() if row.last_seen else None,
                "activity_count": row.activity_count,
                "group_name": row.group_name,
                "team_name": row.team_name
            })
        
        return JSONResponse({
            "success": True,
            "cohort_id": cohort_id,
            "cohort_name": cohort["name"],
            "members": members,
            "total_count": len(members)
        })
        
    except Exception as e:
        logger.error(f"Error getting cohort members: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.get("/api/cohorts/available-groups")
async def get_available_groups() -> JSONResponse:
    """Get all available groups and teams from user data."""
    try:
        gcp_config = get_gcp_config()
        client = gcp_config.bigquery_client
        dataset_id = gcp_config.bigquery_dataset
        
        query = f"""
        SELECT 
            JSON_EXTRACT_SCALAR(csv_data[OFFSET(0)], '$.Group') as group_name,
            JSON_EXTRACT_SCALAR(csv_data[OFFSET(0)], '$.Team') as team_name,
            COUNT(*) as user_count
        FROM `{dataset_id}.users`
        WHERE csv_data IS NOT NULL 
            AND ARRAY_LENGTH(csv_data) > 0
        GROUP BY group_name, team_name
        ORDER BY user_count DESC
        """
        
        results = list(client.query(query).result())
        
        groups = []
        for row in results:
            group_name = row.group_name or "X"
            team_name = row.team_name or "X"
            cohort_name = f"{group_name} {team_name}".strip()
            
            groups.append({
                "group_name": group_name,
                "team_name": team_name,
                "cohort_name": cohort_name,
                "user_count": row.user_count
            })
        
        return JSONResponse({
            "success": True,
            "groups": groups
        })
        
    except Exception as e:
        logger.error(f"Error getting available groups: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


async def get_cohort_member_count(cohort_id: str) -> int:
    """Get the number of members in a cohort."""
    try:
        gcp_config = get_gcp_config()
        client = gcp_config.bigquery_client
        dataset_id = gcp_config.bigquery_dataset
        
        # Get cohort filters
        cohorts_data = load_cohort_trigger_words()
        cohorts = cohorts_data.get("cohorts", {})
        
        if cohort_id not in cohorts:
            return 0
        
        cohort = cohorts[cohort_id]
        group_filter = cohort.get("group_filter")
        team_filter = cohort.get("team_filter")
        
        # Build query based on filters
        where_conditions = []
        if group_filter and group_filter != "X":
            where_conditions.append(f"JSON_EXTRACT_SCALAR(csv_data[OFFSET(0)], '$.Group') = '{group_filter}'")
        if team_filter and team_filter != "X":
            where_conditions.append(f"JSON_EXTRACT_SCALAR(csv_data[OFFSET(0)], '$.Team') = '{team_filter}'")
        
        if not where_conditions:
            where_clause = "1=1"
        else:
            where_clause = " AND ".join(where_conditions)
        
        query = f"""
        SELECT COUNT(*) as member_count
        FROM `{dataset_id}.users`
        WHERE {where_clause}
        """
        
        results = list(client.query(query).result())
        return results[0].member_count if results else 0
        
    except Exception as e:
        logger.error(f"Error getting cohort member count: {e}")
        return 0


def load_cohort_trigger_words() -> Dict[str, Any]:
    """Load cohort trigger words from JSON file."""
    import json
    import os
    
    file_path = "data/cohort_trigger_words.json"
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    else:
        return {"cohorts": {}}


def save_cohort_trigger_words(data: Dict[str, Any]) -> None:
    """Save cohort trigger words to JSON file."""
    import json
    import os
    
    file_path = "data/cohort_trigger_words.json"
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
