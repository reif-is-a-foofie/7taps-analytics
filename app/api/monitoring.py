"""
Monitoring API endpoints for production monitoring system
Provides health checks, metrics, alerts, and performance monitoring
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db_pool
from app.monitoring import AlertLevel, ProductionMonitor
from app.redis_client import get_redis_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Global monitor instance
monitor: Optional[ProductionMonitor] = None


def get_monitor() -> ProductionMonitor:
    """Get or create the production monitor instance"""
    global monitor
    if monitor is None:
        db_pool = get_db_pool()
        redis_client = get_redis_client()
        monitor = ProductionMonitor(db_pool, redis_client)
    return monitor


@router.get("/health")
async def health_check():
    """System health check endpoint"""
    try:
        monitor = get_monitor()
        health_data = monitor.get_system_health()

        if "error" in health_data:
            raise HTTPException(status_code=503, detail=health_data["error"])

        # Determine overall health status
        is_healthy = (
            health_data["database_connected"]
            and health_data["redis_connected"]
            and health_data["cpu_percent"] < 90
            and health_data["memory_percent"] < 95
            and health_data["disk_percent"] < 95
        )

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {
                "database": health_data["database_connected"],
                "redis": health_data["redis_connected"],
                "cpu": health_data["cpu_percent"] < 90,
                "memory": health_data["memory_percent"] < 95,
                "disk": health_data["disk_percent"] < 95,
            },
            "metrics": health_data,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")


@router.get("/metrics")
async def get_metrics():
    """Get comprehensive system and data metrics"""
    try:
        monitor = get_monitor()

        system_health = monitor.get_system_health()
        data_metrics = monitor.get_data_metrics()
        performance_metrics = monitor.get_performance_metrics()

        return {
            "timestamp": datetime.now().isoformat(),
            "system_health": system_health,
            "data_metrics": data_metrics,
            "performance_metrics": performance_metrics,
        }
    except Exception as e:
        logger.error(f"Metrics retrieval failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Metrics retrieval failed: {str(e)}"
        )


@router.get("/alerts")
async def get_alerts(active_only: bool = True):
    """Get system alerts"""
    try:
        monitor = get_monitor()

        # Check for new alerts
        new_alerts = monitor.check_alerts()

        # Get all alerts or only active ones
        if active_only:
            alerts = [asdict(alert) for alert in monitor.alerts if not alert.resolved]
        else:
            alerts = [asdict(alert) for alert in monitor.alerts]

        return {
            "timestamp": datetime.now().isoformat(),
            "new_alerts": new_alerts,
            "all_alerts": alerts,
            "summary": {
                "total": len(alerts),
                "critical": len([a for a in alerts if a["level"] == "critical"]),
                "warning": len([a for a in alerts if a["level"] == "warning"]),
                "error": len([a for a in alerts if a["level"] == "error"]),
                "info": len([a for a in alerts if a["level"] == "info"]),
            },
        }
    except Exception as e:
        logger.error(f"Alerts retrieval failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Alerts retrieval failed: {str(e)}"
        )


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Mark an alert as resolved"""
    try:
        monitor = get_monitor()
        success = monitor.resolve_alert(alert_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

        return {
            "message": f"Alert {alert_id} resolved successfully",
            "timestamp": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Alert resolution failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Alert resolution failed: {str(e)}"
        )


@router.get("/performance")
async def get_performance_metrics():
    """Get detailed performance metrics"""
    try:
        monitor = get_monitor()
        performance = monitor.get_performance_metrics()

        return {"timestamp": datetime.now().isoformat(), "performance": performance}
    except Exception as e:
        logger.error(f"Performance metrics retrieval failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Performance metrics retrieval failed: {str(e)}"
        )


@router.get("/api/analytics")
async def get_analytics_insights():
    """Get analytics insights from data normalization"""
    try:
        monitor = get_monitor()
        insights = monitor.get_analytics_insights()

        return {"timestamp": datetime.now().isoformat(), "insights": insights}
    except Exception as e:
        logger.error(f"Analytics insights retrieval failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Analytics insights retrieval failed: {str(e)}"
        )


@router.get("/api/analytics/migration-status")
async def get_migration_status():
    """Report stuck, migrated, and failed statements and last migration time/status."""
    try:
        monitor = get_monitor()
        # Example: get counts from DB
        conn = monitor.db_pool.getconn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM statements_flat")
        stuck = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM statements_normalized")
        migrated = cursor.fetchone()[0]
        # Optionally, track failed migrations if you have a log
        failed = 0
        last_migration_time = None
        cursor.execute("SELECT MAX(processed_at) FROM statements_normalized")
        row = cursor.fetchone()
        if row and row[0]:
            last_migration_time = row[0].isoformat()
        cursor.close()
        monitor.db_pool.putconn(conn)
        return {
            "stuck_statements": stuck,
            "migrated_statements": migrated,
            "failed_statements": failed,
            "last_migration_time": last_migration_time
        }
    except Exception as e:
        logger.error(f"Migration status retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Migration status retrieval failed: {str(e)}")


@router.get("/metrics/history")
async def get_metrics_history(hours: int = 24):
    """Get metrics history for the specified hours"""
    try:
        monitor = get_monitor()
        history = monitor.get_metrics_history(hours)

        return {"timestamp": datetime.now().isoformat(), "history": history}
    except Exception as e:
        logger.error(f"Metrics history retrieval failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Metrics history retrieval failed: {str(e)}"
        )


@router.get("/status")
async def get_system_status():
    """Get comprehensive system status overview"""
    try:
        monitor = get_monitor()

        # Get all metrics
        system_health = monitor.get_system_health()
        data_metrics = monitor.get_data_metrics()
        performance = monitor.get_performance_metrics()
        alerts = monitor.check_alerts()

        # Determine overall status
        critical_alerts = len([a for a in alerts if a["level"] == "critical"])
        warning_alerts = len([a for a in alerts if a["level"] == "warning"])

        if critical_alerts > 0:
            status = "critical"
        elif warning_alerts > 0:
            status = "warning"
        elif "error" in system_health or "error" in data_metrics:
            status = "error"
        else:
            status = "healthy"

        return {
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "summary": {
                "system_health": (
                    "healthy" if "error" not in system_health else "unhealthy"
                ),
                "data_processing": (
                    "healthy" if "error" not in data_metrics else "unhealthy"
                ),
                "critical_alerts": critical_alerts,
                "warning_alerts": warning_alerts,
                "database_connected": system_health.get("database_connected", False),
                "redis_connected": system_health.get("redis_connected", False),
            },
            "quick_metrics": {
                "cpu_percent": system_health.get("cpu_percent", 0),
                "memory_percent": system_health.get("memory_percent", 0),
                "disk_percent": system_health.get("disk_percent", 0),
                "statements_flat": data_metrics.get("statements_flat_count", 0),
                "statements_normalized": data_metrics.get(
                    "statements_normalized_count", 0
                ),
                "processing_rate": data_metrics.get("processing_rate", 0),
            },
        }
    except Exception as e:
        logger.error(f"System status retrieval failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"System status retrieval failed: {str(e)}"
        )


@router.get("/config")
async def get_monitoring_config():
    """Get monitoring configuration and thresholds"""
    try:
        monitor = get_monitor()

        return {
            "timestamp": datetime.now().isoformat(),
            "thresholds": monitor.thresholds,
            "environment": {
                "database_url": os.getenv("DATABASE_URL", "not_set"),
                "redis_url": os.getenv("REDIS_URL", "not_set"),
                "environment": os.getenv("ENVIRONMENT", "development"),
            },
        }
    except Exception as e:
        logger.error(f"Monitoring config retrieval failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Monitoring config retrieval failed: {str(e)}"
        )
