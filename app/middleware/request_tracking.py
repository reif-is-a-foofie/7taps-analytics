"""
Request Tracking Middleware - Global request monitoring for FastAPI
Tracks all incoming requests and integrates with endpoint analytics.
"""

import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.api.endpoint_tracking import track_request

logger = logging.getLogger(__name__)

class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware to track all incoming requests."""
    
    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/docs",
            # Removed: API docs endpoints (not needed for production)
            "/favicon.ico"
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Only track the /statements endpoint
        if request.url.path != "/statements":
            return await call_next(request)
        
        # Record start time
        start_time = time.time()
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Track the request
            track_request(request, response, process_time)
            
            return response
            
        except Exception as e:
            # Calculate processing time even for errors
            process_time = time.time() - start_time
            
            # Create a mock response for tracking
            error_response = Response(
                content=f"Internal Server Error: {str(e)}",
                status_code=500,
                media_type="text/plain"
            )
            
            # Track the failed request
            track_request(request, error_response, process_time)
            
            # Re-raise the exception
            raise e
