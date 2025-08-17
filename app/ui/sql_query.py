"""
MVP SQL Query UI for direct database queries
Simple web interface for querying normalized tables
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/sql-query", response_class=HTMLResponse)
async def sql_query_interface(request: Request):
    """SQL Query Interface"""
    try:
        return templates.TemplateResponse(
            "sql_query.html",
            {
                "request": request,
                "title": "7taps Analytics - SQL Query Interface",
                "timestamp": datetime.now().isoformat(),
            },
        )
    except Exception as e:
        logger.error(f"SQL query interface rendering failed: {e}")
        return HTMLResponse(
            content=f"""
            <html>
                <head><title>SQL Query Error</title></head>
                <body>
                    <h1>SQL Query Interface Error</h1>
                    <p>Failed to load interface: {str(e)}</p>
                    <a href="/api/sql/tables">View Available Tables</a>
                </body>
            </html>
            """,
            status_code=500,
        )
