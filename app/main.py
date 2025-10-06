from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

# Static files for UI (if serving frontend from same server)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return {"message": "7taps Analytics Safety API", "docs": "/docs"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "safety-api"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
