"""
Learning Locker Sync API endpoints.
"""

import asyncio
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.sync_learninglocker import learninglocker_sync

router = APIRouter()


@router.post("/sync-learninglocker")
async def sync_to_learninglocker() -> Dict[str, Any]:
    """
    Sync xAPI statements from Redis to Learning Locker.
    """
    try:
        result = await learninglocker_sync.sync_redis_to_learninglocker(
            max_statements=20
        )

        return {
            "status": "success",
            "message": f"Synced {result['synced_count']} statements to Learning Locker",
            "sync_result": result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/sync-status")
async def get_sync_status() -> Dict[str, Any]:
    """
    Get Learning Locker sync status.
    """
    try:
        status = await learninglocker_sync.get_sync_status()

        return {
            "status": "active",
            "learninglocker_sync": status,
            "message": "Learning Locker sync status retrieved",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get sync status: {str(e)}"
        )


@router.get("/learninglocker-info")
async def get_learninglocker_info() -> Dict[str, Any]:
    """
    Get Learning Locker connection information.
    """
    return {
        "learninglocker_url": learninglocker_sync.learninglocker_url,
        "learninglocker_username": learninglocker_sync.learninglocker_username,
        "admin_interface": f"{learninglocker_sync.learninglocker_url}/admin",
        "xapi_endpoint": f"{learninglocker_sync.learninglocker_url}/data/xAPI/statements",
        "features": [
            "Statement Browser",
            "Advanced Queries",
            "Data Export",
            "Visual Analytics",
            "xAPI Compliance",
        ],
        "message": "Learning Locker provides advanced xAPI data exploration",
    }
