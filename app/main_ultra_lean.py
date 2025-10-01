"""
Ultra-Lean Production FastAPI App - Guaranteed to Work
Minimal endpoints with maximum reliability.
"""

import os
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse

# Initialize FastAPI app
app = FastAPI(
    title="7taps Analytics - Ultra Lean",
    description="Ultra-lean production API",
    version="1.0.0"
)

# ============================================================================
# ESSENTIAL HEALTH ENDPOINTS (Always Work)
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "7taps Analytics - Ultra Lean Production",
        "status": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/health")
async def api_health_check():
    """API health check."""
    return {
        "status": "operational",
        "service": "7taps-analytics-ultra-lean",
        "version": "1.0.0",
        "environment": "production",
        "deployment_mode": "cloud_run",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ============================================================================
# ESSENTIAL UI ENDPOINTS (Graceful Degradation)
# ============================================================================

@app.get("/ui/data-explorer", response_class=HTMLResponse)
async def data_explorer_ultra_lean(request: Request):
    """Ultra-lean data explorer."""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Data Explorer - Ultra Lean</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .status { background: #f0f8ff; padding: 20px; border-radius: 5px; }
            .endpoints { margin-top: 20px; }
            .endpoint { margin: 10px 0; }
            a { color: #007bff; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Data Explorer - Ultra Lean Mode</h1>
            
            <div class="status">
                <h2>✅ Service Status</h2>
                <p><strong>Status:</strong> Operational</p>
                <p><strong>Mode:</strong> Ultra Lean Production</p>
                <p><strong>Timestamp:</strong> <span id="timestamp">Loading...</span></p>
            </div>
            
            <div class="endpoints">
                <h2>🔗 Available Endpoints</h2>
                <div class="endpoint">
                    <strong>Health Check:</strong> 
                    <a href="/api/health" target="_blank">/api/health</a>
                </div>
                <div class="endpoint">
                    <strong>Safety Dashboard:</strong> 
                    <a href="/ui/safety" target="_blank">/ui/safety</a>
                </div>
                <div class="endpoint">
                    <strong>xAPI Recent:</strong> 
                    <a href="/api/xapi/recent" target="_blank">/api/xapi/recent</a>
                </div>
            </div>
            
            <div style="margin-top: 30px; padding: 20px; background: #fff3cd; border-radius: 5px;">
                <h3>🚀 Ultra Lean Mode Active</h3>
                <p>This is the ultra-lean deployment optimized for maximum speed and reliability. 
                Full features are available via the AI service at 30-second deploy times.</p>
            </div>
        </div>
        
        <script>
            document.getElementById('timestamp').textContent = new Date().toISOString();
        </script>
    </body>
    </html>
    """)

@app.get("/ui/safety", response_class=HTMLResponse)
async def safety_dashboard_ultra_lean(request: Request):
    """Ultra-lean safety dashboard."""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Safety Dashboard - Ultra Lean</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .status { background: #f8f9fa; padding: 20px; border-radius: 5px; }
            .ai-service { background: #e8f5e8; padding: 20px; border-radius: 5px; margin-top: 20px; }
            a { color: #007bff; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛡️ Safety Dashboard - Ultra Lean</h1>
            
            <div class="status">
                <h2>✅ Safety System Status</h2>
                <p><strong>AI Service:</strong> <a href="https://us-central1-taps-data.cloudfunctions.net/ai-analysis-service" target="_blank">Active</a></p>
                <p><strong>Deploy Time:</strong> ~30 seconds for algorithm updates</p>
                <p><strong>Mode:</strong> Ultra Lean Production</p>
            </div>
            
            <div class="ai-service">
                <h3>🤖 AI Analysis Service</h3>
                <p>The AI safety analysis is handled by a separate Cloud Function for ultra-fast algorithm updates:</p>
                <ul>
                    <li><strong>URL:</strong> <a href="https://us-central1-taps-data.cloudfunctions.net/ai-analysis-service" target="_blank">AI Analysis Service</a></li>
                    <li><strong>Deploy Time:</strong> ~30 seconds</li>
                    <li><strong>Features:</strong> Content analysis, batch processing, safety flagging</li>
                </ul>
            </div>
            
            <div style="margin-top: 20px;">
                <p><a href="/ui/data-explorer">← Back to Data Explorer</a></p>
            </div>
        </div>
    </body>
    </html>
    """)

# ============================================================================
# ESSENTIAL API ENDPOINTS (Graceful Degradation)
# ============================================================================

@app.get("/api/xapi/recent")
async def recent_statements_ultra_lean():
    """Ultra-lean recent statements endpoint."""
    return {
        "status": "ultra_lean_mode",
        "message": "Recent statements endpoint in ultra-lean mode",
        "ai_service": "https://us-central1-taps-data.cloudfunctions.net/ai-analysis-service",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "note": "Full functionality available via AI service"
    }

@app.post("/api/ai-content/analyze")
async def analyze_content_ultra_lean(request: Request):
    """Ultra-lean AI content analysis - redirects to AI service."""
    try:
        data = await request.json()
        return {
            "status": "redirect_to_ai_service",
            "ai_service_url": "https://us-central1-taps-data.cloudfunctions.net/ai-analysis-service",
            "message": "Please use the AI service directly for content analysis",
            "received_content": data.get("content", "")[:100] + "..." if len(data.get("content", "")) > 100 else data.get("content", ""),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "error": "AI analysis temporarily unavailable",
            "fallback": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
