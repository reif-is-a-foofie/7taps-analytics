"""
Comprehensive logging configuration for 7taps Analytics.

This module provides structured JSON logging with different log levels,
performance metrics, and error tracking for production monitoring.
"""

import json
import logging
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Optional

import structlog
from structlog.stdlib import LoggerFactory

# Configure structlog for structured JSON logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)


# Performance tracking
class PerformanceTracker:
    """Track performance metrics for logging."""

    def __init__(self):
        self.start_time = None
        self.operation_name = None

    @contextmanager
    def track_operation(self, operation_name: str):
        """Track operation performance."""
        self.operation_name = operation_name
        self.start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - self.start_time
            logger = structlog.get_logger()
            logger.info(
                "operation_completed",
                operation=operation_name,
                duration_ms=round(duration * 1000, 2),
                success=True,
            )

    def track_error(self, operation_name: str, error: Exception):
        """Track error performance."""
        duration = time.time() - self.start_time if self.start_time else 0
        logger = structlog.get_logger()
        logger.error(
            "operation_failed",
            operation=operation_name,
            duration_ms=round(duration * 1000, 2),
            error_type=type(error).__name__,
            error_message=str(error),
            success=False,
        )


# Global performance tracker
performance_tracker = PerformanceTracker()


class StructuredLogger:
    """Structured logger with performance tracking and error handling."""

    def __init__(self, name: str):
        self.logger = structlog.get_logger(name)
        self.name = name

    def info(self, message: str, **kwargs):
        """Log info message with structured data."""
        self.logger.info(message, **kwargs)

    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log error message with structured data."""
        log_data = kwargs.copy()
        if error:
            log_data.update(
                {
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "error_traceback": getattr(error, "__traceback__", None),
                }
            )
        self.logger.error(message, **log_data)

    def warning(self, message: str, **kwargs):
        """Log warning message with structured data."""
        self.logger.warning(message, **kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message with structured data."""
        self.logger.debug(message, **kwargs)

    def critical(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log critical message with structured data."""
        log_data = kwargs.copy()
        if error:
            log_data.update(
                {
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "error_traceback": getattr(error, "__traceback__", None),
                }
            )
        self.logger.critical(message, **log_data)

    def track_performance(self, operation_name: str):
        """Track performance for an operation."""
        return performance_tracker.track_operation(operation_name)

    def log_api_request(
        self, method: str, path: str, status_code: int, duration_ms: float, **kwargs
    ):
        """Log API request with performance metrics."""
        self.logger.info(
            "api_request",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
            **kwargs,
        )

    def log_database_operation(
        self,
        operation: str,
        table: str,
        duration_ms: float,
        rows_affected: int = None,
        **kwargs,
    ):
        """Log database operation with performance metrics."""
        log_data = {
            "operation": operation,
            "table": table,
            "duration_ms": round(duration_ms, 2),
            **kwargs,
        }
        if rows_affected is not None:
            log_data["rows_affected"] = rows_affected
        self.logger.info("database_operation", **log_data)

    def log_redis_operation(
        self, operation: str, key: str, duration_ms: float, **kwargs
    ):
        """Log Redis operation with performance metrics."""
        self.logger.info(
            "redis_operation",
            operation=operation,
            key=key,
            duration_ms=round(duration_ms, 2),
            **kwargs,
        )

    def log_etl_operation(
        self, operation: str, statements_processed: int, duration_ms: float, **kwargs
    ):
        """Log ETL operation with performance metrics."""
        self.logger.info(
            "etl_operation",
            operation=operation,
            statements_processed=statements_processed,
            duration_ms=round(duration_ms, 2),
            **kwargs,
        )


# Configure standard logging to use structlog
logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)

# Create logger instances for different components
etl_logger = StructuredLogger("etl")
api_logger = StructuredLogger("api")
db_logger = StructuredLogger("database")
redis_logger = StructuredLogger("redis")
security_logger = StructuredLogger("security")


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger for a specific component."""
    return StructuredLogger(name)


# Log levels configuration
LOG_LEVELS = {
    "development": logging.DEBUG,
    "staging": logging.INFO,
    "production": logging.WARNING,
}


def configure_log_level(environment: str = "production"):
    """Configure log level based on environment."""
    level = LOG_LEVELS.get(environment, logging.INFO)
    logging.getLogger().setLevel(level)
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


# Performance monitoring decorator
def log_performance(operation_name: str):
    """Decorator to log performance of functions."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            logger = get_logger(func.__module__)

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(
                    "function_completed",
                    function=func.__name__,
                    operation=operation_name,
                    duration_ms=round(duration * 1000, 2),
                    success=True,
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    "function_failed",
                    function=func.__name__,
                    operation=operation_name,
                    duration_ms=round(duration * 1000, 2),
                    error_type=type(e).__name__,
                    error_message=str(e),
                    success=False,
                )
                raise

        return wrapper

    return decorator


# Error tracking
class ErrorTracker:
    """Track and log errors with context."""

    def __init__(self):
        self.error_count = 0
        self.error_types = {}

    def track_error(self, error: Exception, context: Dict[str, Any] = None):
        """Track an error with context."""
        self.error_count += 1
        error_type = type(error).__name__
        self.error_types[error_type] = self.error_types.get(error_type, 0) + 1

        logger = get_logger("error_tracker")
        logger.error(
            "error_occurred",
            error_type=error_type,
            error_message=str(error),
            error_count=self.error_count,
            context=context or {},
        )

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        return {
            "total_errors": self.error_count,
            "error_types": self.error_types,
            "most_common_error": (
                max(self.error_types.items(), key=lambda x: x[1])
                if self.error_types
                else None
            ),
        }


# Global error tracker
error_tracker = ErrorTracker()

# Initialize logging for current environment
environment = "production"  # Can be set via environment variable
configure_log_level(environment)
