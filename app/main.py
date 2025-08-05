from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(
    title="7taps Analytics ETL",
    description="Streaming ETL for xAPI analytics using MCP servers",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "7taps-analytics-etl"}

# Import and include routers
from app.api.etl import router as etl_router
from app.api.orchestrator import router as orchestrator_router
from app.api.nlp import router as nlp_router
from app.api.xapi import router as xapi_router
from app.api.seventaps import router as seventaps_router
from app.ui.admin import router as admin_router
from app.ui.dashboard import router as dashboard_router

app.include_router(etl_router, prefix="/ui", tags=["ETL"])
app.include_router(orchestrator_router, prefix="/api", tags=["Orchestrator"])
app.include_router(nlp_router, prefix="/api", tags=["NLP"])
app.include_router(xapi_router, tags=["xAPI"])
app.include_router(seventaps_router, tags=["7taps"])
app.include_router(admin_router, tags=["Admin"])
app.include_router(dashboard_router, tags=["Dashboard"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 