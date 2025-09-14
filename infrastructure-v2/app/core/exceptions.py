"""
Custom exceptions for the application.
"""


class AppException(Exception):
    """Base application exception."""
    
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ValidationError(AppException):
    """Validation error exception."""
    
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class NotFoundError(AppException):
    """Not found error exception."""
    
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class AuthenticationError(AppException):
    """Authentication error exception."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class AuthorizationError(AppException):
    """Authorization error exception."""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, status_code=403)


class ExternalServiceError(AppException):
    """External service error exception."""
    
    def __init__(self, message: str, service: str = None):
        self.service = service
        super().__init__(message, status_code=502)


class DatabaseError(AppException):
    """Database error exception."""
    
    def __init__(self, message: str):
        super().__init__(message, status_code=503)

