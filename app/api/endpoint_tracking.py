"""
Endpoint Tracking API - Comprehensive request monitoring and analytics
Tracks all API endpoint hits, response times, and provides real-time analytics.
"""

from fastapi import APIRouter, Request, Response
from typing import Dict, Any, List, Optional
import time
import logging
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque
from pydantic import BaseModel, Field
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Global tracking storage (thread-safe)
_endpoint_stats = defaultdict(lambda: {
    "total_hits": 0,
    "successful_hits": 0,
    "failed_hits": 0,
    "total_response_time": 0.0,
    "min_response_time": float('inf'),
    "max_response_time": 0.0,
    "last_hit": None,
    "first_hit": None,
    "recent_hits": deque(maxlen=100)  # Keep last 100 hits per endpoint
})

_global_stats = {
    "total_requests": 0,
    "total_successful": 0,
    "total_failed": 0,
    "total_response_time": 0.0,
    "start_time": datetime.now(timezone.utc),
    "last_request": None,
    "requests_per_minute": deque(maxlen=60),  # Last 60 minutes
    "hourly_requests": defaultdict(int)
}

_lock = threading.Lock()

class EndpointStats(BaseModel):
    """Individual endpoint statistics."""
    endpoint: str = Field(..., description="Endpoint path")
    method: str = Field(..., description="HTTP method")
    total_hits: int = Field(..., description="Total number of hits")
    successful_hits: int = Field(..., description="Number of successful responses (2xx)")
    failed_hits: int = Field(..., description="Number of failed responses (4xx, 5xx)")
    success_rate: float = Field(..., description="Success rate percentage")
    avg_response_time: float = Field(..., description="Average response time in ms")
    min_response_time: float = Field(..., description="Minimum response time in ms")
    max_response_time: float = Field(..., description="Maximum response time in ms")
    last_hit: Optional[str] = Field(None, description="Last hit timestamp")
    first_hit: Optional[str] = Field(None, description="First hit timestamp")
    recent_hits_count: int = Field(..., description="Number of recent hits tracked")

class GlobalStats(BaseModel):
    """Global request statistics."""
    total_requests: int = Field(..., description="Total requests across all endpoints")
    total_successful: int = Field(..., description="Total successful requests")
    total_failed: int = Field(..., description="Total failed requests")
    global_success_rate: float = Field(..., description="Global success rate percentage")
    avg_response_time: float = Field(..., description="Global average response time in ms")
    uptime_seconds: int = Field(..., description="System uptime in seconds")
    requests_per_minute: List[int] = Field(..., description="Requests per minute for last 60 minutes")
    hourly_requests: Dict[str, int] = Field(..., description="Requests per hour")
    last_request: Optional[str] = Field(None, description="Last request timestamp")

class EndpointAnalytics(BaseModel):
    """Comprehensive endpoint analytics."""
    global_stats: GlobalStats = Field(..., description="Global request statistics")
    endpoint_stats: List[EndpointStats] = Field(..., description="Per-endpoint statistics")
    top_endpoints: List[Dict[str, Any]] = Field(..., description="Most hit endpoints")
    recent_activity: List[Dict[str, Any]] = Field(..., description="Recent endpoint activity")

def track_request(request: Request, response: Response, process_time: float):
    """Track a single request."""
    with _lock:
        # Extract endpoint info
        endpoint = str(request.url.path)
        method = request.method
        status_code = response.status_code
        endpoint_key = f"{method} {endpoint}"
        
        # Update global stats
        _global_stats["total_requests"] += 1
        _global_stats["total_response_time"] += process_time
        _global_stats["last_request"] = datetime.now(timezone.utc)
        
        if 200 <= status_code < 300:
            _global_stats["total_successful"] += 1
        else:
            _global_stats["total_failed"] += 1
        
        # Update per-endpoint stats
        stats = _endpoint_stats[endpoint_key]
        stats["total_hits"] += 1
        stats["total_response_time"] += process_time
        stats["min_response_time"] = min(stats["min_response_time"], process_time)
        stats["max_response_time"] = max(stats["max_response_time"], process_time)
        stats["last_hit"] = datetime.now(timezone.utc)
        
        if stats["first_hit"] is None:
            stats["first_hit"] = datetime.now(timezone.utc)
        
        if 200 <= status_code < 300:
            stats["successful_hits"] += 1
        else:
            stats["failed_hits"] += 1
        
        # Track recent hits
        hit_info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status_code": status_code,
            "response_time": process_time,
            "method": method,
            "endpoint": endpoint
        }
        stats["recent_hits"].append(hit_info)
        
        # Update requests per minute
        current_minute = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        _global_stats["requests_per_minute"].append(current_minute)
        
        # Update hourly requests
        current_hour = current_minute.replace(minute=0)
        _global_stats["hourly_requests"][current_hour.isoformat()] += 1

def get_endpoint_stats() -> List[EndpointStats]:
    """Get statistics for all endpoints."""
    with _lock:
        stats_list = []
        for endpoint_key, stats in _endpoint_stats.items():
            if stats["total_hits"] == 0:
                continue
                
            method, endpoint = endpoint_key.split(" ", 1)
            success_rate = (stats["successful_hits"] / stats["total_hits"]) * 100 if stats["total_hits"] > 0 else 0
            avg_response_time = (stats["total_response_time"] / stats["total_hits"]) * 1000 if stats["total_hits"] > 0 else 0
            
            stats_list.append(EndpointStats(
                endpoint=endpoint,
                method=method,
                total_hits=stats["total_hits"],
                successful_hits=stats["successful_hits"],
                failed_hits=stats["failed_hits"],
                success_rate=round(success_rate, 2),
                avg_response_time=round(avg_response_time, 2),
                min_response_time=round(stats["min_response_time"] * 1000, 2) if stats["min_response_time"] != float('inf') else 0,
                max_response_time=round(stats["max_response_time"] * 1000, 2),
                last_hit=stats["last_hit"].isoformat() if stats["last_hit"] else None,
                first_hit=stats["first_hit"].isoformat() if stats["first_hit"] else None,
                recent_hits_count=len(stats["recent_hits"])
            ))
        
        return sorted(stats_list, key=lambda x: x.total_hits, reverse=True)

def get_global_stats() -> GlobalStats:
    """Get global request statistics."""
    with _lock:
        uptime = (datetime.now(timezone.utc) - _global_stats["start_time"]).total_seconds()
        global_success_rate = (_global_stats["total_successful"] / _global_stats["total_requests"]) * 100 if _global_stats["total_requests"] > 0 else 0
        avg_response_time = (_global_stats["total_response_time"] / _global_stats["total_requests"]) * 1000 if _global_stats["total_requests"] > 0 else 0
        
        # Count requests per minute
        current_time = datetime.now(timezone.utc)
        requests_per_minute = []
        for i in range(60):
            minute_time = current_time - timedelta(minutes=i)
            minute_count = sum(1 for hit_time in _global_stats["requests_per_minute"] 
                             if hit_time.replace(second=0, microsecond=0) == minute_time.replace(second=0, microsecond=0))
            requests_per_minute.append(minute_count)
        requests_per_minute.reverse()  # Oldest to newest
        
        return GlobalStats(
            total_requests=_global_stats["total_requests"],
            total_successful=_global_stats["total_successful"],
            total_failed=_global_stats["total_failed"],
            global_success_rate=round(global_success_rate, 2),
            avg_response_time=round(avg_response_time, 2),
            uptime_seconds=int(uptime),
            requests_per_minute=requests_per_minute,
            hourly_requests=dict(_global_stats["hourly_requests"]),
            last_request=_global_stats["last_request"].isoformat() if _global_stats["last_request"] else None
        )

@router.get("/endpoint-analytics", response_model=EndpointAnalytics)
async def get_endpoint_analytics():
    """Get comprehensive endpoint analytics."""
    try:
        global_stats = get_global_stats()
        endpoint_stats = get_endpoint_stats()
        
        # Get top endpoints
        top_endpoints = [
            {
                "endpoint": stat.endpoint,
                "method": stat.method,
                "total_hits": stat.total_hits,
                "success_rate": stat.success_rate,
                "avg_response_time": stat.avg_response_time
            }
            for stat in endpoint_stats[:10]
        ]
        
        # Get recent activity (last 20 hits across all endpoints)
        recent_activity = []
        with _lock:
            all_recent_hits = []
            for stats in _endpoint_stats.values():
                all_recent_hits.extend(list(stats["recent_hits"]))
            
            # Sort by timestamp and take last 20
            all_recent_hits.sort(key=lambda x: x["timestamp"], reverse=True)
            recent_activity = all_recent_hits[:20]
        
        return EndpointAnalytics(
            global_stats=global_stats,
            endpoint_stats=endpoint_stats,
            top_endpoints=top_endpoints,
            recent_activity=recent_activity
        )
        
    except Exception as e:
        logger.error(f"Error getting endpoint analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")

@router.get("/endpoint-stats", response_model=List[EndpointStats])
async def get_endpoint_statistics():
    """Get detailed statistics for all endpoints."""
    try:
        return get_endpoint_stats()
    except Exception as e:
        logger.error(f"Error getting endpoint stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@router.get("/global-stats", response_model=GlobalStats)
async def get_global_statistics():
    """Get global request statistics."""
    try:
        return get_global_stats()
    except Exception as e:
        logger.error(f"Error getting global stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get global stats: {str(e)}")

@router.post("/reset-stats")
async def reset_statistics():
    """Reset all tracking statistics."""
    try:
        with _lock:
            _endpoint_stats.clear()
            _global_stats.update({
                "total_requests": 0,
                "total_successful": 0,
                "total_failed": 0,
                "total_response_time": 0.0,
                "start_time": datetime.now(timezone.utc),
                "last_request": None,
                "requests_per_minute": deque(maxlen=60),
                "hourly_requests": defaultdict(int)
            })
        
        return {"message": "Statistics reset successfully", "timestamp": datetime.now(timezone.utc).isoformat()}
        
    except Exception as e:
        logger.error(f"Error resetting stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset stats: {str(e)}")

@router.get("/health")
async def endpoint_tracking_health():
    """Health check for endpoint tracking service."""
    return {
        "status": "healthy",
        "service": "endpoint-tracking",
        "endpoints_tracked": len(_endpoint_stats),
        "total_requests": _global_stats["total_requests"],
        "uptime_seconds": int((datetime.now(timezone.utc) - _global_stats["start_time"]).total_seconds())
    }
