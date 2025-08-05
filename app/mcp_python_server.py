#!/usr/bin/env python3
"""
Custom MCP Python Server for executing Python code
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import sys
import tempfile
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Python Server", version="1.0.0")

class ExecuteRequest(BaseModel):
    code: str
    timeout: Optional[int] = 30

class ExecuteResponse(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None
    execution_time: float

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "mcp-python-server",
        "version": "1.0.0"
    }

@app.post("/execute", response_model=ExecuteResponse)
async def execute_python_code(request: ExecuteRequest):
    """Execute Python code and return results"""
    import time
    start_time = time.time()
    
    try:
        # Create a temporary file for the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(request.code)
            temp_file = f.name
        
        # Execute the code with timeout
        result = subprocess.run(
            [sys.executable, temp_file],
            capture_output=True,
            text=True,
            timeout=request.timeout
        )
        
        execution_time = time.time() - start_time
        
        # Clean up temp file
        os.unlink(temp_file)
        
        if result.returncode == 0:
            return ExecuteResponse(
                success=True,
                output=result.stdout,
                error=None,
                execution_time=execution_time
            )
        else:
            return ExecuteResponse(
                success=False,
                output=result.stdout,
                error=result.stderr,
                execution_time=execution_time
            )
            
    except subprocess.TimeoutExpired:
        execution_time = time.time() - start_time
        return ExecuteResponse(
            success=False,
            output="",
            error=f"Execution timed out after {request.timeout} seconds",
            execution_time=execution_time
        )
    except Exception as e:
        execution_time = time.time() - start_time
        return ExecuteResponse(
            success=False,
            output="",
            error=str(e),
            execution_time=execution_time
        )

@app.get("/")
async def root():
    """Root endpoint with server info"""
    return {
        "service": "MCP Python Server",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "execute": "/execute"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002) 