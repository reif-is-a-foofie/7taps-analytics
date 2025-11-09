#!/usr/bin/env python3
"""
Cloud Run Proxy Service for URL Preservation
Proxies requests from old URL pattern to new backend service.
"""
import os
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

# Backend service URL (set via environment variable)
BACKEND_URL = os.getenv("BACKEND_URL", "")

if not BACKEND_URL:
    raise ValueError("BACKEND_URL environment variable must be set")

app = FastAPI(title="7taps Analytics Proxy")


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_request(path: str, request: Request):
    """Proxy all requests to backend service."""
    try:
        # Build backend URL
        backend_path = f"{BACKEND_URL.rstrip('/')}/{path}"
        
        # Get request body
        body = await request.body()
        
        # Get headers (exclude host and connection headers)
        headers = dict(request.headers)
        headers.pop("host", None)
        headers.pop("connection", None)
        headers.pop("content-length", None)
        
        # Forward request to backend
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.request(
                method=request.method,
                url=backend_path,
                content=body,
                headers=headers,
                params=dict(request.query_params)
            )
            
            # Return response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "Proxy error", "message": str(e)}
        )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "backend": BACKEND_URL}

