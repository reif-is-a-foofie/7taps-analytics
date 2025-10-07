"""
7taps Analytics - Production FastAPI Application
Enhanced safety management with intelligent content analysis
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Import our enhanced safety system
from app.safety_api import router as safety_router

app = FastAPI(
    title="7taps Analytics - Enhanced Safety System",
    description="Intelligent content analysis and safety management for learning platforms",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include enhanced safety router with proper prefix
app.include_router(safety_router, prefix="/api/safety", tags=["Enhanced Safety"])

# Static files for UI
static_path = os.path.join(os.path.dirname(__file__), "app", "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/")
async def root():
    return {
        "message": "7taps Analytics - Enhanced Safety System",
        "version": "2.0.0",
        "docs": "/docs",
        "safety_ui": "/safety-ui"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "enhanced-safety-system",
        "version": "2.0.0"
    }

@app.get("/api/health")
async def api_health_check():
    return {
        "status": "healthy",
        "service": "enhanced-safety-system",
        "version": "2.0.0"
    }

@app.get("/safety-ui", response_class=HTMLResponse)
async def safety_words_ui():
    """Serve the enhanced safety words management UI"""
    static_path = os.path.join(os.path.dirname(__file__), "app", "static", "safety-words.html")
    if os.path.exists(static_path):
        with open(static_path, "r") as f:
            return f.read()
    else:
        return HTMLResponse("<h1>Enhanced Safety UI not found</h1>", status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
