"""
Production Monitoring System for 7taps Analytics
Tracks system health, performance, and errors with real-time metrics
"""

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import psutil
import psycopg2
import redis
from psycopg2.pool import SimpleConnectionPool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class SystemMetrics:
    """System performance metrics"""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    active_connections: int
    redis_connected: bool
    database_connected: bool


@dataclass
class DataMetrics:
    """Data processing metrics"""

    timestamp: datetime
    statements_flat_count: int
    statements_normalized_count: int
    actors_count: int
    activities_count: int
    verbs_count: int
    processing_rate: float  # statements per minute
    error_rate: float  # errors per minute


@dataclass
class Alert:
    """System alert"""

    id: str
    level: AlertLevel
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class ProductionMonitor:
    """Comprehensive production monitoring system"""

    def __init__(self, db_pool: SimpleConnectionPool, redis_client: redis.Redis):
        self.db_pool = db_pool
        self.redis_client = redis_client
        self.alerts: List[Alert] = []
        self.metrics_history: List[SystemMetrics] = []
        self.data_metrics_history: List[DataMetrics] = []
        self.last_check = datetime.now()

        # Thresholds for alerts
        self.thresholds = {
            "cpu_warning": 70.0,
            "cpu_critical": 90.0,
            "memory_warning": 80.0,
            "memory_critical": 95.0,
            "disk_warning": 85.0,
            "disk_critical": 95.0,
            "error_rate_warning": 5.0,
            "error_rate_critical": 20.0,
            "processing_rate_min": 1.0,  # minimum statements per minute
        }

    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status"""
        try:
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Database connection check
            db_connected = False
            active_connections = 0
            try:
                conn = self.db_pool.getconn()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
                    )
                    active_connections = cursor.fetchone()[0]
                    cursor.close()
                    self.db_pool.putconn(conn)
                    db_connected = True
            except Exception as e:
                logger.error(f"Database connection check failed: {e}")

            # Redis connection check
            redis_connected = False
            try:
                self.redis_client.ping()
                redis_connected = True
            except Exception as e:
                logger.error(f"Redis connection check failed: {e}")

            metrics = SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=disk.percent,
                active_connections=active_connections,
                redis_connected=redis_connected,
                database_connected=db_connected,
            )

            self.metrics_history.append(metrics)

            # Keep only last 1000 metrics
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-1000:]

            return asdict(metrics)

        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {"error": str(e)}

    def get_data_metrics(self) -> Dict[str, Any]:
        """Get data processing metrics from database"""
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            # Get table counts
            cursor.execute("SELECT COUNT(*) FROM statements_flat")
            statements_flat_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM statements_normalized")
            statements_normalized_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM actors")
            actors_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM activities")
            activities_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM verbs")
            verbs_count = cursor.fetchone()[0]

            # Calculate processing rate (statements per minute)
            cursor.execute(
                """
                SELECT COUNT(*) FROM statements_flat 
                WHERE ingested_at >= NOW() - INTERVAL '1 minute'
            """
            )
            recent_statements = cursor.fetchone()[0]
            processing_rate = recent_statements

            # Calculate error rate
            cursor.execute(
                """
                SELECT COUNT(*) FROM statements_flat 
                WHERE ingested_at >= NOW() - INTERVAL '1 minute' 
                AND raw_statement::text LIKE '%error%'
            """
            )
            recent_errors = cursor.fetchone()[0]
            error_rate = recent_errors

            cursor.close()
            self.db_pool.putconn(conn)

            metrics = DataMetrics(
                timestamp=datetime.now(),
                statements_flat_count=statements_flat_count,
                statements_normalized_count=statements_normalized_count,
                actors_count=actors_count,
                activities_count=activities_count,
                verbs_count=verbs_count,
                processing_rate=processing_rate,
                error_rate=error_rate,
            )

            self.data_metrics_history.append(metrics)

            # Keep only last 1000 metrics
            if len(self.data_metrics_history) > 1000:
                self.data_metrics_history = self.data_metrics_history[-1000:]

            return asdict(metrics)

        except Exception as e:
            logger.error(f"Error getting data metrics: {e}")
            return {"error": str(e)}

    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for system alerts based on current metrics"""
        alerts = []

        # Get latest metrics
        system_health = self.get_system_health()
        data_metrics = self.get_data_metrics()

        if "error" in system_health:
            alert = Alert(
                id=f"system_error_{int(time.time())}",
                level=AlertLevel.ERROR,
                message=f"System health check failed: {system_health['error']}",
                timestamp=datetime.now(),
            )
            alerts.append(asdict(alert))
            return alerts

        # CPU alerts
        if system_health["cpu_percent"] > self.thresholds["cpu_critical"]:
            alert = Alert(
                id=f"cpu_critical_{int(time.time())}",
                level=AlertLevel.CRITICAL,
                message=f"CPU usage critical: {system_health['cpu_percent']:.1f}%",
                timestamp=datetime.now(),
            )
            alerts.append(asdict(alert))
        elif system_health["cpu_percent"] > self.thresholds["cpu_warning"]:
            alert = Alert(
                id=f"cpu_warning_{int(time.time())}",
                level=AlertLevel.WARNING,
                message=f"CPU usage high: {system_health['cpu_percent']:.1f}%",
                timestamp=datetime.now(),
            )
            alerts.append(asdict(alert))

        # Memory alerts
        if system_health["memory_percent"] > self.thresholds["memory_critical"]:
            alert = Alert(
                id=f"memory_critical_{int(time.time())}",
                level=AlertLevel.CRITICAL,
                message=f"Memory usage critical: {system_health['memory_percent']:.1f}%",
                timestamp=datetime.now(),
            )
            alerts.append(asdict(alert))
        elif system_health["memory_percent"] > self.thresholds["memory_warning"]:
            alert = Alert(
                id=f"memory_warning_{int(time.time())}",
                level=AlertLevel.WARNING,
                message=f"Memory usage high: {system_health['memory_percent']:.1f}%",
                timestamp=datetime.now(),
            )
            alerts.append(asdict(alert))

        # Disk alerts
        if system_health["disk_percent"] > self.thresholds["disk_critical"]:
            alert = Alert(
                id=f"disk_critical_{int(time.time())}",
                level=AlertLevel.CRITICAL,
                message=f"Disk usage critical: {system_health['disk_percent']:.1f}%",
                timestamp=datetime.now(),
            )
            alerts.append(asdict(alert))
        elif system_health["disk_percent"] > self.thresholds["disk_warning"]:
            alert = Alert(
                id=f"disk_warning_{int(time.time())}",
                level=AlertLevel.WARNING,
                message=f"Disk usage high: {system_health['disk_percent']:.1f}%",
                timestamp=datetime.now(),
            )
            alerts.append(asdict(alert))

        # Database connection alerts
        if not system_health["database_connected"]:
            alert = Alert(
                id=f"db_disconnected_{int(time.time())}",
                level=AlertLevel.CRITICAL,
                message="Database connection lost",
                timestamp=datetime.now(),
            )
            alerts.append(asdict(alert))

        # Redis connection alerts
        if not system_health["redis_connected"]:
            alert = Alert(
                id=f"redis_disconnected_{int(time.time())}",
                level=AlertLevel.CRITICAL,
                message="Redis connection lost",
                timestamp=datetime.now(),
            )
            alerts.append(asdict(alert))

        # Data processing alerts
        if "error" not in data_metrics:
            if data_metrics["error_rate"] > self.thresholds["error_rate_critical"]:
                alert = Alert(
                    id=f"error_rate_critical_{int(time.time())}",
                    level=AlertLevel.CRITICAL,
                    message=f"Error rate critical: {data_metrics['error_rate']:.1f} errors/min",
                    timestamp=datetime.now(),
                )
                alerts.append(asdict(alert))
            elif data_metrics["error_rate"] > self.thresholds["error_rate_warning"]:
                alert = Alert(
                    id=f"error_rate_warning_{int(time.time())}",
                    level=AlertLevel.WARNING,
                    message=f"Error rate high: {data_metrics['error_rate']:.1f} errors/min",
                    timestamp=datetime.now(),
                )
                alerts.append(asdict(alert))

            if data_metrics["processing_rate"] < self.thresholds["processing_rate_min"]:
                alert = Alert(
                    id=f"processing_slow_{int(time.time())}",
                    level=AlertLevel.WARNING,
                    message=f"Processing rate low: {data_metrics['processing_rate']:.1f} statements/min",
                    timestamp=datetime.now(),
                )
                alerts.append(asdict(alert))

        # Add new alerts to history
        for alert_dict in alerts:
            alert_obj = Alert(**alert_dict)
            self.alerts.append(alert_obj)

        # Keep only last 1000 alerts
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-1000:]

        return alerts

    def get_analytics_insights(self) -> Dict[str, Any]:
        """Get analytics insights from data normalization"""
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            insights = {}

            # Top activities by engagement
            cursor.execute(
                """
                SELECT a.activity_name, COUNT(*) as engagement_count
                FROM statements_normalized sn
                JOIN activities a ON sn.activity_id = a.activity_id
                WHERE sn.timestamp >= NOW() - INTERVAL '24 hours'
                GROUP BY a.activity_id, a.activity_name
                ORDER BY engagement_count DESC
                LIMIT 10
            """
            )
            top_activities = cursor.fetchall()
            insights["top_activities"] = [
                {"activity": activity, "count": count}
                for activity, count in top_activities
            ]

            # Top actors by activity
            cursor.execute(
                """
                SELECT ac.actor_name, COUNT(*) as activity_count
                FROM statements_normalized sn
                JOIN actors ac ON sn.actor_id = ac.actor_id
                WHERE sn.timestamp >= NOW() - INTERVAL '24 hours'
                GROUP BY ac.actor_id, ac.actor_name
                ORDER BY activity_count DESC
                LIMIT 10
            """
            )
            top_actors = cursor.fetchall()
            insights["top_actors"] = [
                {"actor": actor, "count": count} for actor, count in top_actors
            ]

            # Processing efficiency
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total_statements,
                    COUNT(CASE WHEN result_success = true THEN 1 END) as successful_statements,
                    ROUND(
                        COUNT(CASE WHEN result_success = true THEN 1 END) * 100.0 / COUNT(*), 2
                    ) as success_rate
                FROM statements_normalized
                WHERE timestamp >= NOW() - INTERVAL '24 hours'
            """
            )
            efficiency = cursor.fetchone()
            insights["processing_efficiency"] = {
                "total_statements": efficiency[0],
                "successful_statements": efficiency[1],
                "success_rate": efficiency[2],
            }

            # Cohort analytics (if available)
            cursor.execute(
                """
                SELECT 
                    cohort_name,
                    COUNT(*) as member_count,
                    COUNT(DISTINCT actor_id) as active_learners
                FROM statements_normalized
                WHERE cohort_name IS NOT NULL 
                AND timestamp >= NOW() - INTERVAL '24 hours'
                GROUP BY cohort_name
                ORDER BY member_count DESC
            """
            )
            cohort_analytics = cursor.fetchall()
            insights["cohort_analytics"] = [
                {
                    "cohort": cohort,
                    "member_count": member_count,
                    "active_learners": active_learners,
                }
                for cohort, member_count, active_learners in cohort_analytics
            ]

            cursor.close()
            self.db_pool.putconn(conn)

            return insights

        except Exception as e:
            logger.error(f"Error getting analytics insights: {e}")
            return {"error": str(e)}

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        try:
            # System performance over time
            recent_metrics = (
                self.metrics_history[-60:]
                if len(self.metrics_history) >= 60
                else self.metrics_history
            )

            avg_cpu = (
                sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
                if recent_metrics
                else 0
            )
            avg_memory = (
                sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
                if recent_metrics
                else 0
            )
            avg_disk = (
                sum(m.disk_percent for m in recent_metrics) / len(recent_metrics)
                if recent_metrics
                else 0
            )

            # Data processing performance
            recent_data_metrics = (
                self.data_metrics_history[-60:]
                if len(self.data_metrics_history) >= 60
                else self.data_metrics_history
            )

            avg_processing_rate = (
                sum(m.processing_rate for m in recent_data_metrics)
                / len(recent_data_metrics)
                if recent_data_metrics
                else 0
            )
            avg_error_rate = (
                sum(m.error_rate for m in recent_data_metrics)
                / len(recent_data_metrics)
                if recent_data_metrics
                else 0
            )

            return {
                "system_performance": {
                    "avg_cpu_percent": round(avg_cpu, 2),
                    "avg_memory_percent": round(avg_memory, 2),
                    "avg_disk_percent": round(avg_disk, 2),
                    "connection_stability": {
                        "database": (
                            all(m.database_connected for m in recent_metrics[-10:])
                            if recent_metrics
                            else False
                        ),
                        "redis": (
                            all(m.redis_connected for m in recent_metrics[-10:])
                            if recent_metrics
                            else False
                        ),
                    },
                },
                "data_performance": {
                    "avg_processing_rate": round(avg_processing_rate, 2),
                    "avg_error_rate": round(avg_error_rate, 2),
                    "data_integrity": {
                        "statements_flat": (
                            self.data_metrics_history[-1].statements_flat_count
                            if self.data_metrics_history
                            else 0
                        ),
                        "statements_normalized": (
                            self.data_metrics_history[-1].statements_normalized_count
                            if self.data_metrics_history
                            else 0
                        ),
                        "normalization_ratio": (
                            round(
                                (
                                    self.data_metrics_history[
                                        -1
                                    ].statements_normalized_count
                                    / max(
                                        self.data_metrics_history[
                                            -1
                                        ].statements_flat_count,
                                        1,
                                    )
                                )
                                * 100,
                                2,
                            )
                            if self.data_metrics_history
                            else 0
                        ),
                    },
                },
                "alerts_summary": {
                    "total_alerts": len(self.alerts),
                    "active_alerts": len([a for a in self.alerts if not a.resolved]),
                    "critical_alerts": len(
                        [
                            a
                            for a in self.alerts
                            if a.level == AlertLevel.CRITICAL and not a.resolved
                        ]
                    ),
                    "warning_alerts": len(
                        [
                            a
                            for a in self.alerts
                            if a.level == AlertLevel.WARNING and not a.resolved
                        ]
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {"error": str(e)}

    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                return True
        return False

    def get_metrics_history(self, hours: int = 24) -> Dict[str, Any]:
        """Get metrics history for the specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        system_metrics = [
            asdict(m) for m in self.metrics_history if m.timestamp >= cutoff_time
        ]

        data_metrics = [
            asdict(m) for m in self.data_metrics_history if m.timestamp >= cutoff_time
        ]

        return {
            "system_metrics": system_metrics,
            "data_metrics": data_metrics,
            "time_range": f"Last {hours} hours",
        }
