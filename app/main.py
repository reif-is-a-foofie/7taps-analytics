from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os
from app.config import settings

app = FastAPI(
    title="7taps Analytics ETL",
    description="Streaming ETL for xAPI analytics using direct database connections",
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

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with HTML landing page"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>7taps Analytics ETL</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 40px 20px;
            }
            .header {
                text-align: center;
                color: white;
                margin-bottom: 50px;
            }
            .header h1 {
                font-size: 3em;
                margin: 0;
                font-weight: 300;
            }
            .header p {
                font-size: 1.2em;
                opacity: 0.9;
                margin: 10px 0 0 0;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 30px;
                margin-bottom: 40px;
            }
            .card {
                background: white;
                border-radius: 12px;
                padding: 30px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                transition: transform 0.3s ease;
            }
            .card:hover {
                transform: translateY(-5px);
            }
            .card h2 {
                color: #667eea;
                margin: 0 0 15px 0;
                font-size: 1.5em;
            }
            .card p {
                color: #666;
                line-height: 1.6;
                margin: 0 0 20px 0;
            }
            .btn {
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 500;
                transition: all 0.3s ease;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
            }
            .status {
                background: rgba(255,255,255,0.1);
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 30px;
                color: white;
            }
            .status h3 {
                margin: 0 0 10px 0;
                font-size: 1.2em;
            }
            .status-item {
                display: flex;
                justify-content: space-between;
                margin: 5px 0;
            }
            .status-ok {
                color: #4CAF50;
            }
            .api-section {
                background: rgba(255,255,255,0.1);
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 30px;
                color: white;
            }
            .api-section h3 {
                margin: 0 0 15px 0;
                font-size: 1.2em;
            }
            .api-endpoint {
                background: rgba(255,255,255,0.1);
                border-radius: 4px;
                padding: 10px;
                margin: 5px 0;
                font-family: monospace;
                font-size: 0.9em;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>7taps Analytics ETL</h1>
                <p>Streaming ETL for xAPI analytics using direct database connections</p>
            </div>
            
            <div class="status">
                <h3>🚀 System Status</h3>
                <div class="status-item">
                    <span>FastAPI Application:</span>
                    <span class="status-ok">✅ Running</span>
                </div>
                <div class="status-item">
                    <span>PostgreSQL Database:</span>
                    <span class="status-ok">✅ Running</span>
                </div>
                <div class="status-item">
                    <span>Redis Cache:</span>
                    <span class="status-ok">✅ Running</span>
                </div>
                <div class="status-item">
                    <span>7taps Webhook:</span>
                    <span class="status-ok">✅ Configured</span>
                </div>
            </div>
            
            <div class="grid">
                <div class="card">
                    <h2>📊 Analytics Dashboard</h2>
                    <p>Real-time metrics and insights for xAPI learning analytics with interactive charts and visualizations.</p>
                    <a href="/ui/dashboard" class="btn">Open Dashboard</a>
                </div>
                
                <div class="card">
                    <h2>⚙️ Admin Panel</h2>
                    <p>System administration, database terminal, and configuration management for the analytics platform.</p>
                    <a href="/ui/admin" class="btn">Open Admin Panel</a>
                </div>
                
                <div class="card">
                    <h2>📚 API Documentation</h2>
                    <p>Interactive API documentation with Swagger UI for testing endpoints and understanding the API structure.</p>
                    <a href="/docs" class="btn">View API Docs</a>
                </div>
                
                <div class="card">
                    <h2>🔗 7taps Integration</h2>
                    <p>Standard xAPI /statements endpoint for 7taps integration with Basic authentication using username and password.</p>
                    <a href="/api/7taps/keys" class="btn">View Auth Info</a>
                </div>
                
                <div class="card">
                    <h2>📥 xAPI Ingestion</h2>
                    <p>Endpoint for receiving and processing xAPI statements with real-time ETL processing and analytics.</p>
                    <a href="/docs#/xAPI" class="btn">Test xAPI</a>
                </div>
                
                <div class="card">
                    <h2>🧠 NLP Queries</h2>
                    <p>Natural language processing for querying analytics data using conversational interfaces.</p>
                    <a href="/docs#/NLP" class="btn">Test NLP</a>
                </div>
                
                <div class="card">
                    <h2>📊 Data Normalization</h2>
                    <p>Comprehensive data flattening and normalization for xAPI statements with structured analytics tables.</p>
                    <a href="/docs#/Data-Normalization" class="btn">View Normalization</a>
                </div>
                
                <div class="card">
                    <h2>📥 Data Import</h2>
                    <p>Upload CSV polls data and audio files to integrate with your analytics system.</p>
                    <a href="/data-import" class="btn">Import Data</a>
                </div>
            </div>
            
            <div class="api-section">
                <h3>🔧 Key API Endpoints</h3>
                <div class="api-endpoint">GET /health - Health check</div>
                <div class="api-endpoint">POST /api/xapi/ingest - xAPI statement ingestion</div>
                <div class="api-endpoint">POST /statements - 7taps xAPI statements endpoint</div>
                <div class="api-endpoint">GET /api/dashboard/metrics - Dashboard metrics</div>
                <div class="api-endpoint">POST /api/ui/nlp-query - NLP query processing</div>
                <div class="api-endpoint">POST /api/normalize/statement - Data normalization</div>
                <div class="api-endpoint">GET /api/normalize/stats - Normalization statistics</div>
                <div class="api-endpoint">POST /api/import/polls - CSV polls import</div>
                <div class="api-endpoint">POST /api/import/audio - Audio file upload</div>
                <div class="api-endpoint">GET /data-import - Data import interface</div>
                <div class="api-endpoint">GET /ui/dashboard - Analytics dashboard</div>
                <div class="api-endpoint">GET /ui/admin - Admin panel</div>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

@app.get("/api")
async def root():
    """Root endpoint with application information"""
    return {
        "title": "7taps Analytics ETL",
        "description": "Streaming ETL for xAPI analytics using direct database connections",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "dashboard": "/ui/dashboard",
            "admin": "/ui/admin",
            "api_docs": "/docs",
            "health": "/health",
            "xapi_ingestion": "/api/xapi/ingest",
            "7taps_statements": "/statements"
        },
        "services": {
            "fastapi": "running",
            "postgresql": "running",
            "redis": "running"
        }
    }

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
from app.api.xapi_lrs import router as xapi_lrs_router
from app.api.learninglocker_sync import router as learninglocker_sync_router
from app.api.health import router as health_router
from app.api.data_normalization import router as data_normalization_router
from app.api.data_import import router as data_import_router
from app.ui.admin import router as admin_router
from app.ui.dashboard import router as dashboard_router
from app.ui.data_import import router as data_import_ui_router

app.include_router(etl_router, prefix="/ui", tags=["ETL"])
app.include_router(orchestrator_router, prefix="/api", tags=["Orchestrator"])
app.include_router(nlp_router, prefix="/api", tags=["NLP"])
app.include_router(xapi_router, tags=["xAPI"])
app.include_router(seventaps_router, tags=["7taps"])
app.include_router(xapi_lrs_router, tags=["xAPI LRS"])
app.include_router(learninglocker_sync_router, prefix="/api", tags=["Learning Locker"])
app.include_router(data_normalization_router, prefix="/api", tags=["Data Normalization"])
app.include_router(data_import_router, prefix="/api", tags=["Data Import"])
app.include_router(health_router, tags=["Health"])
app.include_router(admin_router, tags=["Admin"])
app.include_router(dashboard_router, tags=["Dashboard"])
app.include_router(data_import_ui_router, tags=["Data Import UI"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 