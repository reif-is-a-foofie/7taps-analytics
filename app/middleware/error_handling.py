"""
Comprehensive error handling middleware for 7taps Analytics.
Provides graceful error handling, logging, and monitoring.
"""

import logging
import traceback
from typing import Callable, Dict, Any
from datetime import datetime, timezone
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.logging_config import get_logger
from app.utils.timestamp_utils import get_current_central_time_str

logger = get_logger("error_handling")

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for comprehensive error handling and monitoring."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.error_counts = {}
        self.error_history = []
        self.max_history = 1000  # Keep last 1000 errors
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle requests with comprehensive error handling."""
        start_time = datetime.now(timezone.utc)
        
        try:
            response = await call_next(request)
            
            # Log successful requests for monitoring
            if response.status_code >= 400:
                await self._log_error_response(request, response, start_time)
            
            return response
            
        except HTTPException as e:
            # Handle FastAPI HTTP exceptions
            return await self._handle_http_exception(request, e, start_time)
            
        except Exception as e:
            # Handle unexpected exceptions
            return await self._handle_unexpected_error(request, e, start_time)
    
    async def _log_error_response(self, request: Request, response: Response, start_time: datetime):
        """Log error responses for monitoring."""
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        error_info = {
            "timestamp": get_current_central_time_str(),
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "duration_seconds": duration,
            "user_agent": request.headers.get("user-agent", "unknown"),
            "client_ip": request.client.host if request.client else "unknown"
        }
        
        logger.warning(f"Error response: {error_info}")
        self._update_error_counts(response.status_code)
    
    async def _handle_http_exception(self, request: Request, exc: HTTPException, start_time: datetime) -> JSONResponse:
        """Handle FastAPI HTTP exceptions."""
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        error_info = {
            "timestamp": get_current_central_time_str(),
            "method": request.method,
            "url": str(request.url),
            "status_code": exc.status_code,
            "detail": exc.detail,
            "duration_seconds": duration,
            "error_type": "HTTPException"
        }
        
        logger.warning(f"HTTP exception: {error_info}")
        self._update_error_counts(exc.status_code)
        self._add_to_error_history(error_info)
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP Error",
                "status_code": exc.status_code,
                "detail": exc.detail,
                "timestamp": get_current_central_time_str(),
                "request_id": getattr(request.state, "request_id", "unknown")
            }
        )
    
    async def _handle_unexpected_error(self, request: Request, exc: Exception, start_time: datetime) -> JSONResponse:
        """Handle unexpected exceptions with full error details."""
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        error_info = {
            "timestamp": get_current_central_time_str(),
            "method": request.method,
            "url": str(request.url),
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "duration_seconds": duration,
            "traceback": traceback.format_exc(),
            "user_agent": request.headers.get("user-agent", "unknown"),
            "client_ip": request.client.host if request.client else "unknown"
        }
        
        logger.error(f"Unexpected error: {error_info}")
        self._update_error_counts(500)
        self._add_to_error_history(error_info)
        
        # Return sanitized error response
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "status_code": 500,
                "detail": "An unexpected error occurred. Please try again later.",
                "timestamp": get_current_central_time_str(),
                "request_id": getattr(request.state, "request_id", "unknown")
            }
        )
    
    def _update_error_counts(self, status_code: int):
        """Update error count statistics."""
        if status_code not in self.error_counts:
            self.error_counts[status_code] = 0
        self.error_counts[status_code] += 1
    
    def _add_to_error_history(self, error_info: Dict[str, Any]):
        """Add error to history for analysis."""
        self.error_history.append(error_info)
        
        # Keep only the most recent errors
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics for monitoring."""
        return {
            "error_counts": self.error_counts,
            "total_errors": sum(self.error_counts.values()),
            "recent_errors": self.error_history[-10:] if self.error_history else [],
            "error_rate": self._calculate_error_rate()
        }
    
    def _calculate_error_rate(self) -> float:
        """Calculate error rate percentage."""
        total_errors = sum(self.error_counts.values())
        if total_errors == 0:
            return 0.0
        
        # Assume 4xx and 5xx are errors
        error_codes = [code for code in self.error_counts.keys() if code >= 400]
        error_count = sum(self.error_counts[code] for code in error_codes)
        
        return (error_count / total_errors) * 100 if total_errors > 0 else 0.0


class CircuitBreaker:
    """Circuit breaker pattern for external service calls."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit breaker."""
        if self.last_failure_time is None:
            return True
        
        time_since_failure = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
        return time_since_failure >= self.timeout
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "failure_threshold": self.failure_threshold,
            "timeout": self.timeout
        }


# Global circuit breakers for external services
bigquery_circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=30)
pubsub_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)
storage_circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=30)
