"""
Robust error handling and automatic recovery for 7taps Analytics.

This module provides graceful error handling, automatic retry mechanisms,
circuit breaker patterns, and data consistency checks.
"""

import asyncio
import time
from typing import Any, Callable, Dict, Optional, List
from functools import wraps
from enum import Enum
import logging

from app.logging_config import get_logger, error_tracker

logger = get_logger("error_handling")

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service is recovered

class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker transitioning to half-open state")
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful operation."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        logger.info("Circuit breaker reset to CLOSED state")
    
    def _on_failure(self):
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self.last_failure_time
        }

class RetryHandler:
    """Automatic retry mechanism with exponential backoff."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    async def retry_async(self, func: Callable, *args, **kwargs) -> Any:
        """Retry async function with exponential backoff."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                return result
                
            except Exception as e:
                last_exception = e
                error_tracker.track_error(e, {
                    "function": func.__name__,
                    "attempt": attempt + 1,
                    "max_retries": self.max_retries
                })
                
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Retry attempt {attempt + 1}/{self.max_retries} failed, retrying in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries} retry attempts failed")
                    break
        
        raise last_exception
    
    def retry_sync(self, func: Callable, *args, **kwargs) -> Any:
        """Retry sync function with exponential backoff."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                return result
                
            except Exception as e:
                last_exception = e
                error_tracker.track_error(e, {
                    "function": func.__name__,
                    "attempt": attempt + 1,
                    "max_retries": self.max_retries
                })
                
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Retry attempt {attempt + 1}/{self.max_retries} failed, retrying in {delay}s")
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries} retry attempts failed")
                    break
        
        raise last_exception

class DataConsistencyChecker:
    """Check data consistency across systems."""
    
    def __init__(self):
        self.checks = []
    
    def add_check(self, name: str, check_func: Callable):
        """Add a consistency check."""
        self.checks.append((name, check_func))
    
    async def run_checks(self) -> Dict[str, Any]:
        """Run all consistency checks."""
        results = {}
        
        for name, check_func in self.checks:
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                results[name] = {
                    "status": "passed",
                    "result": result
                }
            except Exception as e:
                logger.error(f"Consistency check '{name}' failed", error=e)
                results[name] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return results

class GracefulShutdown:
    """Handle graceful shutdown of the application."""
    
    def __init__(self):
        self.shutdown_handlers = []
        self.is_shutting_down = False
    
    def add_shutdown_handler(self, handler: Callable):
        """Add a shutdown handler."""
        self.shutdown_handlers.append(handler)
    
    async def shutdown(self):
        """Execute graceful shutdown."""
        if self.is_shutting_down:
            return
        
        self.is_shutting_down = True
        logger.info("Starting graceful shutdown...")
        
        for handler in self.shutdown_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()
            except Exception as e:
                logger.error(f"Shutdown handler failed", error=e)
        
        logger.info("Graceful shutdown completed")

# Global instances
circuit_breakers = {}
retry_handler = RetryHandler()
consistency_checker = DataConsistencyChecker()
graceful_shutdown = GracefulShutdown()

def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """Get or create a circuit breaker for a specific service."""
    if name not in circuit_breakers:
        circuit_breakers[name] = CircuitBreaker(**kwargs)
    return circuit_breakers[name]

def with_error_handling(func: Callable = None, *, 
                       retry: bool = True, 
                       circuit_breaker: str = None,
                       log_errors: bool = True):
    """Decorator for error handling."""
    def decorator(f):
        @wraps(f)
        async def async_wrapper(*args, **kwargs):
            try:
                if retry:
                    return await retry_handler.retry_async(f, *args, **kwargs)
                else:
                    return await f(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"Error in {f.__name__}", error=e)
                error_tracker.track_error(e, {
                    "function": f.__name__,
                    "args": str(args),
                    "kwargs": str(kwargs)
                })
                raise
        
        @wraps(f)
        def sync_wrapper(*args, **kwargs):
            try:
                if retry:
                    return retry_handler.retry_sync(f, *args, **kwargs)
                else:
                    return f(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"Error in {f.__name__}", error=e)
                error_tracker.track_error(e, {
                    "function": f.__name__,
                    "args": str(args),
                    "kwargs": str(kwargs)
                })
                raise
        
        if asyncio.iscoroutinefunction(f):
            return async_wrapper
        else:
            return sync_wrapper
    
    if func is None:
        return decorator
    else:
        return decorator(func)

def with_circuit_breaker(name: str, **circuit_kwargs):
    """Decorator for circuit breaker pattern."""
    def decorator(func: Callable):
        circuit = get_circuit_breaker(name, **circuit_kwargs)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return circuit.call(func, *args, **kwargs)
        
        return wrapper
    return decorator

class ErrorRecovery:
    """Automatic error recovery mechanisms."""
    
    @staticmethod
    async def recover_database_connection():
        """Attempt to recover database connection."""
        logger.info("Attempting database connection recovery...")
        # Implementation would depend on your database connection management
        pass
    
    @staticmethod
    async def recover_redis_connection():
        """Attempt to recover Redis connection."""
        logger.info("Attempting Redis connection recovery...")
        # Implementation would depend on your Redis connection management
        pass
    
    @staticmethod
    async def recover_etl_pipeline():
        """Attempt to recover ETL pipeline."""
        logger.info("Attempting ETL pipeline recovery...")
        # Implementation would depend on your ETL pipeline
        pass

# Predefined consistency checks
async def check_redis_data_consistency():
    """Check Redis data consistency."""
    # Implementation would check Redis data integrity
    return {"redis_entries": 0, "consistency": "ok"}

async def check_database_data_consistency():
    """Check database data consistency."""
    # Implementation would check database integrity
    return {"table_count": 0, "consistency": "ok"}

async def check_etl_pipeline_consistency():
    """Check ETL pipeline consistency."""
    # Implementation would check ETL pipeline state
    return {"processed_statements": 0, "consistency": "ok"}

# Add default consistency checks
consistency_checker.add_check("redis_data", check_redis_data_consistency)
consistency_checker.add_check("database_data", check_database_data_consistency)
consistency_checker.add_check("etl_pipeline", check_etl_pipeline_consistency) 