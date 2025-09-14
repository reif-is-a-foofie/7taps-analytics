"""
Standardized error handling decorators and utilities for infrastructure-v2.
"""
from functools import wraps
from typing import Any, Callable, Dict, Optional
import structlog
from fastapi import HTTPException

from app.core.exceptions import AppException, ValidationError, ExternalServiceError
from app.logging_config import get_logger

logger = get_logger("error_handlers")


def handle_errors(
    default_message: str = "An error occurred",
    log_errors: bool = True,
    reraise: bool = True
):
    """
    Decorator for standardized error handling across all API endpoints.
    
    Args:
        default_message: Default error message if no specific message is available
        log_errors: Whether to log errors
        reraise: Whether to reraise the exception
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except ValidationError as e:
                if log_errors:
                    logger.warning("Validation error", error=str(e), function=func.__name__)
                if reraise:
                    raise HTTPException(status_code=400, detail=str(e))
                return {"error": str(e), "type": "ValidationError"}
                
            except ExternalServiceError as e:
                if log_errors:
                    logger.error("External service error", error=str(e), function=func.__name__)
                if reraise:
                    raise HTTPException(status_code=502, detail=str(e))
                return {"error": str(e), "type": "ExternalServiceError"}
                
            except AppException as e:
                if log_errors:
                    logger.error("Application error", error=str(e), function=func.__name__)
                if reraise:
                    raise HTTPException(status_code=e.status_code, detail=e.message)
                return {"error": e.message, "type": e.__class__.__name__}
                
            except Exception as e:
                if log_errors:
                    logger.error("Unexpected error", error=str(e), function=func.__name__)
                if reraise:
                    raise HTTPException(status_code=500, detail=default_message)
                return {"error": default_message, "type": "InternalError"}
        
        return wrapper
    return decorator


def handle_service_errors(
    service_name: str,
    default_message: str = "Service temporarily unavailable"
):
    """
    Decorator for service-level error handling.
    
    Args:
        service_name: Name of the service for logging
        default_message: Default error message
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except ValidationError as e:
                logger.warning(
                    "Service validation error",
                    service=service_name,
                    error=str(e),
                    function=func.__name__
                )
                raise ExternalServiceError(f"{service_name} validation failed: {str(e)}")
                
            except Exception as e:
                logger.error(
                    "Service error",
                    service=service_name,
                    error=str(e),
                    function=func.__name__
                )
                raise ExternalServiceError(f"{service_name} error: {str(e)}")
        
        return wrapper
    return decorator


def log_operation(operation_name: str, include_args: bool = False):
    """
    Decorator for logging operation execution.
    
    Args:
        operation_name: Name of the operation for logging
        include_args: Whether to include function arguments in logs
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            log_data = {
                "operation": operation_name,
                "function": func.__name__
            }
            
            if include_args:
                log_data["args"] = str(args)[:200]  # Limit length
                log_data["kwargs"] = str(kwargs)[:200]
            
            logger.info("Operation started", **log_data)
            
            try:
                result = await func(*args, **kwargs)
                logger.info("Operation completed", operation=operation_name, function=func.__name__)
                return result
            except Exception as e:
                logger.error(
                    "Operation failed",
                    operation=operation_name,
                    function=func.__name__,
                    error=str(e)
                )
                raise
        
        return wrapper
    return decorator


class ErrorContext:
    """Context manager for error handling with additional context."""
    
    def __init__(self, context: Dict[str, Any], operation: str):
        self.context = context
        self.operation = operation
        self.logger = logger.bind(operation=operation, **context)
    
    def __enter__(self):
        self.logger.info("Operation started")
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.logger.info("Operation completed successfully")
        else:
            self.logger.error(
                "Operation failed",
                error=str(exc_val),
                error_type=exc_type.__name__
            )
        return False  # Don't suppress exceptions


def create_error_response(
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Args:
        error: The exception that occurred
        context: Additional context for the error
    
    Returns:
        Standardized error response dictionary
    """
    response = {
        "error": str(error),
        "type": error.__class__.__name__,
        "timestamp": structlog.processors.TimeStamper()._make_stamper()()
    }
    
    if context:
        response["context"] = context
    
    if isinstance(error, AppException):
        response["status_code"] = error.status_code
    elif isinstance(error, ValidationError):
        response["status_code"] = 400
    elif isinstance(error, ExternalServiceError):
        response["status_code"] = 502
    else:
        response["status_code"] = 500
    
    return response

