from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from safety_api import router as safety_router
import os

app = FastAPI(
    title="7taps Analytics Safety API",
    description="Enhanced safety management with intelligent word filtering",
    version="1.0.0"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include safety router
app.include_router(safety_router)

@app.get("/")
async def root():
    return {"message": "7taps Analytics Safety API", "docs": "/docs"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "safety-api"}

@app.get("/api/health")
async def api_health_check():
    return {"status": "healthy", "service": "safety-api", "version": "1.0.0"}

@app.get("/safety-ui", response_class=HTMLResponse)
async def safety_words_ui():
    """Serve the safety words management UI"""
    static_path = os.path.join("app", "static", "safety-words.html")
    if os.path.exists(static_path):
        with open(static_path, "r") as f:
            return f.read()
    else:
        return HTMLResponse("<h1>UI not found</h1>", status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
