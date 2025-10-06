"""
Health monitoring endpoints for POL Analytics.

This module provides comprehensive health checks, system status monitoring,
resource usage tracking, and alert system integration.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import psutil
import time
from datetime import datetime
import os

from app.logging_config import get_logger, performance_tracker
from app.api.bigquery_analytics import get_bigquery_connection_status
from app.config.gcp_config import get_gcp_config

router = APIRouter()
logger = get_logger("health")

class HealthMonitor:
    """Monitor system health and performance."""
    
    def __init__(self):
        self.start_time = time.time()
        
    async def check_queue_health(self) -> Dict[str, Any]:
        """Check Pub/Sub configuration and basic connectivity."""
        try:
            with performance_tracker.track_operation("pubsub_health_check"):
                gcp_config = get_gcp_config()
                topic_path = gcp_config.get_topic_path()
                publisher = gcp_config.pubsub_publisher
                publisher.get_topic(request={"topic": topic_path})

                return {
                    "status": "healthy",
                    "connection": "pubsub",
                    "project_id": gcp_config.project_id,
                    "topic": gcp_config.pubsub_topic,
                    "response_time_ms": 0,
                }

        except Exception as exc:
            logger.error("Pub/Sub health check failed", error=exc)
            return {
                "status": "unhealthy",
                "connection": "pubsub",
                "error": str(exc),
                "response_time_ms": 0,
            }
    
    async def check_database_health(self) -> Dict[str, Any]:
        """Check BigQuery connection and performance."""
        try:
            with performance_tracker.track_operation("database_health_check"):
                status = await get_bigquery_connection_status()
                ok = status.get("status") == "connected"
                return {
                    "status": "healthy" if ok else status.get("status", "unknown"),
                    "connection": "bigquery",
                    "project_id": status.get("project_id"),
                    "dataset_id": status.get("dataset_id"),
                    "tables_count": status.get("tables_count", 0),
                    "response_time_ms": 0
                }

        except Exception as e:
            logger.error("Database health check failed", error=e)
            return {
                "status": "unhealthy",
                "connection": "disconnected",
                "error": str(e),
                "response_time_ms": 0
            }
    
    async def get_system_resources(self) -> Dict[str, Any]:
        """Get system resource usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_percent": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "used_percent": round((disk.used / disk.total) * 100, 2)
                }
            }
        except Exception as e:
            logger.error("System resources check failed", error=e)
            return {"error": str(e)}
    
    async def get_application_metrics(self) -> Dict[str, Any]:
        """Get application-specific metrics."""
        uptime_seconds = time.time() - self.start_time
        
        return {
            "uptime_seconds": int(uptime_seconds),
            "uptime_human": f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m",
            "environment": os.getenv("ENVIRONMENT", "production"),
            "version": "1.0.0"
        }

# Global health monitor
health_monitor = HealthMonitor()

@router.get("/health")
async def basic_health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "POL-analytics"
    }

@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check with all system components."""
    try:
        with performance_tracker.track_operation("detailed_health_check"):
            queue_health = await health_monitor.check_queue_health()
            db_health = await health_monitor.check_database_health()
            system_resources = await health_monitor.get_system_resources()
            app_metrics = await health_monitor.get_application_metrics()
            
            # Determine overall health
            overall_status = "healthy"
            if queue_health["status"] == "unhealthy" or db_health["status"] == "unhealthy":
                overall_status = "unhealthy"
            
            return {
                "status": overall_status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "components": {
                    "queue": queue_health,
                    "database": db_health,
                    "system": system_resources
                },
                "application": app_metrics
            }
            
    except Exception as e:
        logger.error("Detailed health check failed", error=e)
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@router.get("/health/redis")
async def redis_health_check() -> Dict[str, Any]:
    """Compatibility endpoint exposing Pub/Sub queue health."""
    return await health_monitor.check_queue_health()

@router.get("/health/database")
async def database_health_check() -> Dict[str, Any]:
    """Database-specific health check."""
    return await health_monitor.check_database_health()

@router.get("/health/system")
async def system_health_check() -> Dict[str, Any]:
    """System resources health check."""
    return await health_monitor.get_system_resources()

@router.get("/health/metrics")
async def application_metrics() -> Dict[str, Any]:
    """Application metrics endpoint."""
    return await health_monitor.get_application_metrics()

@router.get("/health/ready")
async def readiness_probe() -> Dict[str, Any]:
    """Readiness probe for Kubernetes/container orchestration."""
    try:
        queue_health = await health_monitor.check_queue_health()
        db_health = await health_monitor.check_database_health()

        # Service is ready if both Pub/Sub queue and database are healthy
        is_ready = (
            queue_health["status"] == "healthy"
            and db_health["status"] == "healthy"
        )

        return {
            "ready": is_ready,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {
                "queue": queue_health["status"] == "healthy",
                "database": db_health["status"] == "healthy"
            }
        }
        
    except Exception as e:
        logger.error("Readiness probe failed", error=e)
        return {
            "ready": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }

@router.get("/health/live")
async def liveness_probe() -> Dict[str, Any]:
    """Liveness probe for Kubernetes/container orchestration."""
    return {
        "alive": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid()
    }

@router.get("/health/status")
async def comprehensive_status() -> Dict[str, Any]:
    """Comprehensive system status with alerts."""
    try:
        with performance_tracker.track_operation("comprehensive_status_check"):
            # Get all health checks
            queue_health = await health_monitor.check_queue_health()
            db_health = await health_monitor.check_database_health()
            system_resources = await health_monitor.get_system_resources()
            app_metrics = await health_monitor.get_application_metrics()
            
            # Generate alerts based on thresholds
            alerts = []
            
            # CPU alert
            if "cpu_percent" in system_resources and system_resources["cpu_percent"] > 80:
                alerts.append({
                    "level": "warning",
                    "message": f"High CPU usage: {system_resources['cpu_percent']}%",
                    "component": "system"
                })
            
            # Memory alert
            if "memory" in system_resources and system_resources["memory"]["used_percent"] > 85:
                alerts.append({
                    "level": "warning",
                    "message": f"High memory usage: {system_resources['memory']['used_percent']}%",
                    "component": "system"
                })
            
            # Disk alert
            if "disk" in system_resources and system_resources["disk"]["used_percent"] > 90:
                alerts.append({
                    "level": "critical",
                    "message": f"High disk usage: {system_resources['disk']['used_percent']}%",
                    "component": "system"
                })
            
            # Queue alert
            if queue_health["status"] == "unhealthy":
                alerts.append({
                    "level": "critical",
                    "message": "Pub/Sub queue connection failed",
                    "component": "queue"
                })
            
            # Database alert
            if db_health["status"] == "unhealthy":
                alerts.append({
                    "level": "critical",
                    "message": "Database connection failed",
                    "component": "database"
                })
            
            # Determine overall status
            overall_status = "healthy"
            if any(alert["level"] == "critical" for alert in alerts):
                overall_status = "critical"
            elif any(alert["level"] == "warning" for alert in alerts):
                overall_status = "warning"
            
            return {
                "status": overall_status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "components": {
                    "queue": queue_health,
                    "database": db_health,
                    "system": system_resources
                },
                "application": app_metrics,
                "alerts": alerts,
                "alert_count": len(alerts)
            }
            
    except Exception as e:
        logger.error("Comprehensive status check failed", error=e)
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}") 
