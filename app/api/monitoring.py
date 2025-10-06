"""
Monitoring API endpoints for system health and performance tracking.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from app.logging_config import get_logger
from app.monitoring import system_monitor
from app.middleware.error_handling import ErrorHandlingMiddleware
from app.utils.timestamp_utils import get_current_central_time_str

logger = get_logger("monitoring_api")
router = APIRouter()

# Global error handler instance (will be set by main.py)
error_handler: Optional[ErrorHandlingMiddleware] = None

def set_error_handler(handler: ErrorHandlingMiddleware):
    """Set the global error handler instance."""
    global error_handler
    error_handler = handler

@router.get("/health")
async def system_health() -> Dict[str, Any]:
    """Get overall system health status."""
    try:
        health = system_monitor.get_system_health()
        return health
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system health")

@router.get("/metrics")
async def get_metrics(hours: int = 24) -> Dict[str, Any]:
    """Get system metrics for the specified time period."""
    try:
        if hours < 1 or hours > 168:  # Max 1 week
            raise HTTPException(status_code=400, detail="Hours must be between 1 and 168")
        
        metrics_history = system_monitor.get_metrics_history(hours)
        current_metrics = system_monitor.get_current_metrics()
        
        return {
            "current_metrics": current_metrics.__dict__ if current_metrics else None,
            "metrics_history": metrics_history,
            "time_range_hours": hours,
            "timestamp": get_current_central_time_str()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metrics")

@router.get("/alerts")
async def get_alerts(active_only: bool = True) -> Dict[str, Any]:
    """Get system alerts."""
    try:
        if active_only:
            alerts = system_monitor.get_active_alerts()
        else:
            alerts = [alert.__dict__ for alert in system_monitor.alerts]
        
        return {
            "alerts": alerts,
            "active_only": active_only,
            "total_alerts": len(alerts),
            "timestamp": get_current_central_time_str()
        }
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alerts")

@router.get("/errors")
async def get_error_stats() -> Dict[str, Any]:
    """Get error statistics from the error handler."""
    try:
        if not error_handler:
            return {
                "error": "Error handler not available",
                "timestamp": get_current_central_time_str()
            }
        
        error_stats = error_handler.get_error_stats()
        return {
            "error_statistics": error_stats,
            "timestamp": get_current_central_time_str()
        }
    except Exception as e:
        logger.error(f"Error getting error stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get error statistics")

@router.get("/performance")
async def get_performance_summary() -> Dict[str, Any]:
    """Get performance summary with key metrics."""
    try:
        current_metrics = system_monitor.get_current_metrics()
        active_alerts = system_monitor.get_active_alerts()
        
        if not current_metrics:
            return {
                "error": "No metrics available",
                "timestamp": get_current_central_time_str()
            }
        
        # Calculate performance score (0-100)
        performance_score = 100
        
        # Deduct points for high resource usage
        if current_metrics.cpu_percent > 80:
            performance_score -= 20
        elif current_metrics.cpu_percent > 60:
            performance_score -= 10
        
        if current_metrics.memory_percent > 85:
            performance_score -= 20
        elif current_metrics.memory_percent > 70:
            performance_score -= 10
        
        if current_metrics.response_time_avg_ms > 1000:
            performance_score -= 20
        elif current_metrics.response_time_avg_ms > 500:
            performance_score -= 10
        
        if current_metrics.error_rate_percent > 5:
            performance_score -= 20
        elif current_metrics.error_rate_percent > 2:
            performance_score -= 10
        
        # Deduct points for active alerts
        critical_alerts = len([a for a in active_alerts if a["severity"] == "CRITICAL"])
        high_alerts = len([a for a in active_alerts if a["severity"] == "HIGH"])
        
        performance_score -= critical_alerts * 15
        performance_score -= high_alerts * 10
        
        performance_score = max(0, performance_score)
        
        return {
            "performance_score": performance_score,
            "status": "EXCELLENT" if performance_score >= 90 else
                     "GOOD" if performance_score >= 70 else
                     "FAIR" if performance_score >= 50 else
                     "POOR",
            "key_metrics": {
                "cpu_percent": current_metrics.cpu_percent,
                "memory_percent": current_metrics.memory_percent,
                "response_time_ms": current_metrics.response_time_avg_ms,
                "error_rate_percent": current_metrics.error_rate_percent,
                "requests_per_minute": current_metrics.requests_per_minute
            },
            "active_alerts": len(active_alerts),
            "critical_alerts": critical_alerts,
            "high_alerts": high_alerts,
            "timestamp": get_current_central_time_str()
        }
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance summary")

@router.get("/status")
async def get_comprehensive_status() -> Dict[str, Any]:
    """Get comprehensive system status including all monitoring data."""
    try:
        health = system_monitor.get_system_health()
        active_alerts = system_monitor.get_active_alerts()
        current_metrics = system_monitor.get_current_metrics()
        error_stats = error_handler.get_error_stats() if error_handler else {}
        
        return {
            "system_health": health,
            "active_alerts": active_alerts,
            "current_metrics": current_metrics.__dict__ if current_metrics else None,
            "error_statistics": error_stats,
            "monitoring_status": "ACTIVE",
            "timestamp": get_current_central_time_str()
        }
    except Exception as e:
        logger.error(f"Error getting comprehensive status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get comprehensive status")

@router.post("/alerts/resolve/{alert_id}")
async def resolve_alert(alert_id: str) -> Dict[str, Any]:
    """Manually resolve an alert by ID."""
    try:
        # Find and resolve the alert
        for alert in system_monitor.alerts:
            if str(id(alert)) == alert_id:
                alert.resolved = True
                logger.info(f"Alert {alert_id} manually resolved")
                return {
                    "message": "Alert resolved successfully",
                    "alert_id": alert_id,
                    "timestamp": get_current_central_time_str()
                }
        
        raise HTTPException(status_code=404, detail="Alert not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve alert")

@router.get("/circuit-breakers")
async def get_circuit_breaker_status() -> Dict[str, Any]:
    """Get status of all circuit breakers."""
    try:
        from app.middleware.error_handling import (
            bigquery_circuit_breaker,
            pubsub_circuit_breaker,
            storage_circuit_breaker
        )
        
        return {
            "circuit_breakers": {
                "bigquery": bigquery_circuit_breaker.get_state(),
                "pubsub": pubsub_circuit_breaker.get_state(),
                "storage": storage_circuit_breaker.get_state()
            },
            "timestamp": get_current_central_time_str()
        }
    except Exception as e:
        logger.error(f"Error getting circuit breaker status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get circuit breaker status")
