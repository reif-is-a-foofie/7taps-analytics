"""
Comprehensive system monitoring for 7taps Analytics.
Tracks performance, errors, and system health.
"""

import asyncio
import psutil
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from collections import deque, defaultdict

from app.logging_config import get_logger
from app.utils.timestamp_utils import get_current_central_time_str

logger = get_logger("system_monitor")

@dataclass
class SystemMetrics:
    """System performance metrics."""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    active_connections: int
    response_time_avg_ms: float
    error_rate_percent: float
    requests_per_minute: int

@dataclass
class PerformanceAlert:
    """Performance alert data."""
    timestamp: str
    alert_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    message: str
    value: float
    threshold: float
    resolved: bool = False

class SystemMonitor:
    """Comprehensive system monitoring and alerting."""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics_history = deque(maxlen=max_history)
        self.alerts = deque(maxlen=100)
        self.request_times = deque(maxlen=1000)
        self.error_counts = defaultdict(int)
        self.request_counts = defaultdict(int)
        
        # Performance thresholds
        self.thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_usage_percent": 90.0,
            "response_time_ms": 1000.0,
            "error_rate_percent": 5.0
        }
        
        # Start monitoring
        self._start_monitoring()
    
    def _start_monitoring(self):
        """Start background monitoring tasks."""
        asyncio.create_task(self._collect_metrics_loop())
        asyncio.create_task(self._check_alerts_loop())
    
    async def _collect_metrics_loop(self):
        """Continuously collect system metrics."""
        while True:
            try:
                metrics = await self._collect_system_metrics()
                self.metrics_history.append(metrics)
                await self._check_performance_thresholds(metrics)
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
            
            await asyncio.sleep(30)  # Collect every 30 seconds
    
    async def _check_alerts_loop(self):
        """Continuously check for alerts."""
        while True:
            try:
                await self._process_alerts()
            except Exception as e:
                logger.error(f"Error processing alerts: {e}")
            
            await asyncio.sleep(60)  # Check every minute
    
    async def _collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics."""
        # CPU and Memory
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Network connections
        connections = len(psutil.net_connections())
        
        # Calculate response time average
        response_time_avg = 0
        if self.request_times:
            response_time_avg = sum(self.request_times) / len(self.request_times)
        
        # Calculate error rate
        total_requests = sum(self.request_counts.values())
        total_errors = sum(self.error_counts.values())
        error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
        
        # Calculate requests per minute
        now = datetime.now(timezone.utc)
        minute_ago = now - timedelta(minutes=1)
        recent_requests = sum(
            count for timestamp, count in self.request_counts.items()
            if timestamp > minute_ago
        )
        
        return SystemMetrics(
            timestamp=get_current_central_time_str(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory.used / (1024 * 1024),
            memory_available_mb=memory.available / (1024 * 1024),
            disk_usage_percent=disk.percent,
            disk_free_gb=disk.free / (1024 * 1024 * 1024),
            active_connections=connections,
            response_time_avg_ms=response_time_avg,
            error_rate_percent=error_rate,
            requests_per_minute=recent_requests
        )
    
    async def _check_performance_thresholds(self, metrics: SystemMetrics):
        """Check if metrics exceed thresholds and create alerts."""
        checks = [
            ("cpu_percent", metrics.cpu_percent, "CPU usage"),
            ("memory_percent", metrics.memory_percent, "Memory usage"),
            ("disk_usage_percent", metrics.disk_usage_percent, "Disk usage"),
            ("response_time_ms", metrics.response_time_avg_ms, "Response time"),
            ("error_rate_percent", metrics.error_rate_percent, "Error rate")
        ]
        
        for threshold_key, value, description in checks:
            threshold = self.thresholds.get(threshold_key, float('inf'))
            
            if value > threshold:
                severity = self._determine_severity(value, threshold)
                alert = PerformanceAlert(
                    timestamp=get_current_central_time_str(),
                    alert_type=threshold_key,
                    severity=severity,
                    message=f"{description} is {value:.1f}% (threshold: {threshold:.1f}%)",
                    value=value,
                    threshold=threshold
                )
                
                self.alerts.append(alert)
                logger.warning(f"Performance alert: {alert.message}")
    
    def _determine_severity(self, value: float, threshold: float) -> str:
        """Determine alert severity based on how much threshold is exceeded."""
        ratio = value / threshold
        
        if ratio >= 2.0:
            return "CRITICAL"
        elif ratio >= 1.5:
            return "HIGH"
        elif ratio >= 1.2:
            return "MEDIUM"
        else:
            return "LOW"
    
    async def _process_alerts(self):
        """Process and resolve alerts."""
        # Mark old alerts as resolved if conditions improve
        current_metrics = self.metrics_history[-1] if self.metrics_history else None
        if not current_metrics:
            return
        
        for alert in self.alerts:
            if alert.resolved:
                continue
            
            # Check if alert condition is resolved
            if self._is_alert_resolved(alert, current_metrics):
                alert.resolved = True
                logger.info(f"Alert resolved: {alert.message}")
    
    def _is_alert_resolved(self, alert: PerformanceAlert, metrics: SystemMetrics) -> bool:
        """Check if an alert condition is resolved."""
        threshold = alert.threshold * 0.9  # 10% buffer below threshold
        
        if alert.alert_type == "cpu_percent":
            return metrics.cpu_percent < threshold
        elif alert.alert_type == "memory_percent":
            return metrics.memory_percent < threshold
        elif alert.alert_type == "disk_usage_percent":
            return metrics.disk_usage_percent < threshold
        elif alert.alert_type == "response_time_ms":
            return metrics.response_time_avg_ms < threshold
        elif alert.alert_type == "error_rate_percent":
            return metrics.error_rate_percent < threshold
        
        return False
    
    def record_request(self, response_time_ms: float, status_code: int):
        """Record a request for monitoring."""
        self.request_times.append(response_time_ms)
        
        # Record request count by minute
        minute = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        self.request_counts[minute] += 1
        
        # Record error count
        if status_code >= 400:
            self.error_counts[minute] += 1
    
    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """Get the most recent system metrics."""
        return self.metrics_history[-1] if self.metrics_history else None
    
    def get_metrics_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metrics history for the specified number of hours."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        return [
            asdict(metrics) for metrics in self.metrics_history
            if datetime.fromisoformat(metrics.timestamp.replace(' CST', '')) > cutoff_time
        ]
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active (unresolved) alerts."""
        return [
            asdict(alert) for alert in self.alerts
            if not alert.resolved
        ]
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        current_metrics = self.get_current_metrics()
        active_alerts = self.get_active_alerts()
        
        if not current_metrics:
            return {
                "status": "UNKNOWN",
                "message": "No metrics available",
                "timestamp": get_current_central_time_str()
            }
        
        # Determine overall health
        critical_alerts = [a for a in active_alerts if a["severity"] == "CRITICAL"]
        high_alerts = [a for a in active_alerts if a["severity"] == "HIGH"]
        
        if critical_alerts:
            status = "CRITICAL"
            message = f"{len(critical_alerts)} critical alerts active"
        elif high_alerts:
            status = "DEGRADED"
            message = f"{len(high_alerts)} high priority alerts active"
        elif active_alerts:
            status = "WARNING"
            message = f"{len(active_alerts)} alerts active"
        else:
            status = "HEALTHY"
            message = "All systems operational"
        
        return {
            "status": status,
            "message": message,
            "timestamp": get_current_central_time_str(),
            "metrics": asdict(current_metrics),
            "active_alerts": active_alerts,
            "total_alerts": len(active_alerts)
        }


# Global system monitor instance
system_monitor = SystemMonitor()
