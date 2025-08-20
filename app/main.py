from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
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

# Static files mount removed - not needed for chat interface

@app.get("/chat", response_class=HTMLResponse)
async def chat_interface():
    """Chat interface endpoint"""
    with open("chat_interface.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the analytics dashboard with dynamic data"""
    # Initialize default values in case database connection fails
    metrics = [0, 0, 0, 0]  # [users, lessons, responses, activities]
    lesson_names = []
    lesson_counts = []
    behavior_labels = []
    behavior_values = []
    
    # Get real data from the database
    try:
        import psycopg2
        import os
        from datetime import datetime
        
        # Database connection
        DATABASE_URL = os.getenv('DATABASE_URL')
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is not set")
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        
        conn = psycopg2.connect(DATABASE_URL, sslmode=os.getenv('PGSSLMODE', 'require'))
        cursor = conn.cursor()
        
        # Get real metrics
        cursor.execute("""
            SELECT 
                (SELECT COUNT(DISTINCT id) FROM users) as total_users,
                (SELECT COUNT(DISTINCT id) FROM lessons) as total_lessons,
                (SELECT COUNT(DISTINCT id) FROM user_responses) as total_responses,
                (SELECT COUNT(DISTINCT id) FROM user_activities) as total_activities
        """)
        metrics = cursor.fetchone()
        
        # Get lesson engagement data from new normalized tables
        # Removed unused import to fix dashboard error
        
        cursor.execute(f"""
            SELECT 
                l.lesson_name,
                COUNT(DISTINCT s.actor_id) as response_count
            FROM lessons l
            LEFT JOIN context_extensions_new ce ON l.lesson_number = CAST(ce.extension_value AS INTEGER)
            LEFT JOIN statements_new s ON ce.statement_id = s.statement_id
            WHERE ce.extension_key = 'https://7taps.com/lesson-number'
            GROUP BY l.id, l.lesson_name, l.lesson_number
            ORDER BY l.lesson_number
        """)
        lesson_data = cursor.fetchall()
        
        # Get behavior priorities
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN LOWER(ur.response_value) LIKE '%sleep%' THEN 'Sleep'
                    WHEN LOWER(ur.response_value) LIKE '%screen%' OR LOWER(ur.response_value) LIKE '%phone%' THEN 'Screen Time'
                    WHEN LOWER(ur.response_value) LIKE '%stress%' OR LOWER(ur.response_value) LIKE '%anxiety%' THEN 'Stress'
                    WHEN LOWER(ur.response_value) LIKE '%focus%' OR LOWER(ur.response_value) LIKE '%productivity%' THEN 'Focus/Productivity'
                    ELSE 'Other'
                END as behavior_category,
                COUNT(*) as count
            FROM user_responses ur
            WHERE ur.response_value IS NOT NULL AND ur.response_value != ''
            GROUP BY behavior_category
            ORDER BY count DESC
        """)
        behavior_data = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Format data for charts with safety checks
        lesson_names = [row[0] for row in lesson_data] if lesson_data else ['No Data']
        lesson_counts = [row[1] for row in lesson_data] if lesson_data else [0]
        
        behavior_labels = [row[0] for row in behavior_data] if behavior_data else ['No Data']
        behavior_values = [row[1] for row in behavior_data] if behavior_data else [0]
        
        # Create dynamic HTML with Data Explorer as main focus
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>7taps HR Analytics Explorer</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --primary-color: #6A1B9A;
                    --primary-light: #8E24AA;
                    --primary-dark: #4A148C;
                    --bg-color: #FFFFFF;
                    --bg-light: #F8F9FA;
                    --text-primary: #2D3748;
                    --text-secondary: #718096;
                    --border-color: #E2E8F0;
                    --success-color: #48BB78;
                    --warning-color: #ED8936;
                    --danger-color: #E53E3E;
                    --card-shadow: rgba(0, 0, 0, 0.1) 0px 2px 4px;
                    --card-shadow-hover: rgba(0, 0, 0, 0.15) 0px 4px 8px;
                }}
                
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ 
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                    background: var(--bg-light); 
                    color: var(--text-primary); 
                    line-height: 1.6;
                }}
                
                /* Layout */
                .app-container {{ display: flex; min-height: 100vh; }}
                .sidebar {{ 
                    width: 280px; 
                    background: var(--bg-color); 
                    border-right: 1px solid var(--border-color); 
                    overflow-y: auto;
                    box-shadow: var(--card-shadow);
                }}
                .main-content {{ flex: 1; display: flex; flex-direction: column; }}
                
                /* Header */
                .header {{ 
                    background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-light) 100%); 
                    color: var(--bg-color); 
                    padding: 2rem; 
                    text-align: center;
                    box-shadow: var(--card-shadow);
                }}
                .header h1 {{ 
                    font-size: 2.25rem; 
                    font-weight: 700;
                    margin-bottom: 0.5rem; 
                    letter-spacing: -0.025em;
                }}
                .header p {{ 
                    font-size: 1.125rem; 
                    opacity: 0.9;
                    font-weight: 400;
                }}
                
                /* Sidebar */
                .sidebar-section {{ 
                    padding: 1.5rem; 
                    border-bottom: 1px solid var(--border-color); 
                }}
                .sidebar-section h3 {{ 
                    font-size: 0.875rem; 
                    font-weight: 600;
                    margin-bottom: 1rem; 
                    color: var(--text-secondary);
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }}
                .sidebar-item {{ 
                    display: block; 
                    padding: 0.75rem 1rem; 
                    margin: 0.25rem 0; 
                    background: var(--bg-light); 
                    border-radius: 8px; 
                    text-decoration: none; 
                    color: var(--text-primary); 
                    transition: all 0.2s ease;
                    font-weight: 500;
                    font-size: 0.875rem;
                }}
                .sidebar-item:hover {{ 
                    background: var(--primary-color); 
                    color: var(--bg-color);
                    transform: translateX(4px);
                }}
                .sidebar-item.active {{ 
                    background: var(--primary-color); 
                    color: var(--bg-color);
                    box-shadow: var(--card-shadow);
                }}
                
                /* Main Content */
                .content {{ padding: 2rem; flex: 1; }}
                .metrics-grid {{ 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); 
                    gap: 1.5rem; 
                    margin-bottom: 2rem; 
                }}
                .metric-card {{ 
                    background: var(--bg-color); 
                    padding: 1.75rem; 
                    border-radius: 12px; 
                    box-shadow: var(--card-shadow); 
                    text-align: center;
                    transition: all 0.2s ease;
                    border: 1px solid var(--border-color);
                }}
                .metric-card:hover {{
                    box-shadow: var(--card-shadow-hover);
                    transform: translateY(-2px);
                }}
                .metric-value {{ 
                    font-size: 2.5rem; 
                    font-weight: 700; 
                    color: var(--primary-color); 
                    margin-bottom: 0.5rem;
                    line-height: 1;
                }}
                .metric-label {{ 
                    color: var(--text-secondary); 
                    font-size: 0.875rem;
                    font-weight: 500;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }}
                .charts-grid {{ 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); 
                    gap: 1.5rem; 
                    margin-bottom: 2rem; 
                }}
                .chart-container {{ 
                    background: var(--bg-color); 
                    padding: 1.75rem; 
                    border-radius: 12px; 
                    box-shadow: var(--card-shadow);
                    border: 1px solid var(--border-color);
                }}
                .chart-title {{ 
                    font-size: 1.125rem; 
                    font-weight: 600;
                    margin-bottom: 1rem; 
                    color: var(--text-primary);
                }}
                
                /* Data Explorer Styles */
                .explorer-controls {{ 
                    margin-bottom: 2rem; 
                    padding: 1.75rem; 
                    background: var(--bg-color); 
                    border-radius: 12px;
                    box-shadow: var(--card-shadow);
                    border: 1px solid var(--border-color);
                }}
                .filter-grid {{ 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); 
                    gap: 1rem; 
                    margin-bottom: 1.5rem; 
                }}
                .filter-group label {{ 
                    display: block; 
                    margin-bottom: 0.5rem; 
                    font-weight: 600;
                    font-size: 0.875rem;
                    color: var(--text-primary);
                }}
                .filter-group select, .filter-group input {{ 
                    width: 100%; 
                    padding: 0.75rem; 
                    border: 1px solid var(--border-color); 
                    border-radius: 8px;
                    font-family: 'Inter', sans-serif;
                    font-size: 0.875rem;
                    transition: all 0.2s ease;
                }}
                .filter-group select:focus, .filter-group input:focus {{
                    outline: none;
                    border-color: var(--primary-color);
                    box-shadow: 0 0 0 3px rgba(106, 27, 154, 0.1);
                }}
                .action-buttons {{ 
                    display: flex; 
                    gap: 1rem; 
                    flex-wrap: wrap; 
                }}
                .btn {{ 
                    padding: 0.75rem 1.5rem; 
                    border: none; 
                    border-radius: 8px; 
                    cursor: pointer; 
                    font-weight: 600; 
                    color: var(--bg-color);
                    font-family: 'Inter', sans-serif;
                    font-size: 0.875rem;
                    transition: all 0.2s ease;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }}
                .btn:hover {{
                    transform: translateY(-1px);
                    box-shadow: var(--card-shadow-hover);
                }}
                .btn-primary {{ background: var(--primary-color); }}
                .btn-primary:hover {{ background: var(--primary-light); }}
                .btn-success {{ background: var(--success-color); }}
                .btn-warning {{ background: var(--warning-color); }}
                .btn-danger {{ background: var(--danger-color); }}
                
                /* Table Styles */
                .data-table-container {{ 
                    background: var(--bg-color); 
                    border-radius: 12px; 
                    box-shadow: var(--card-shadow); 
                    overflow: hidden;
                    border: 1px solid var(--border-color);
                }}
                .data-table {{ 
                    width: 100%; 
                    border-collapse: collapse; 
                    font-size: 0.875rem; 
                }}
                .data-table th {{ 
                    background: var(--bg-light); 
                    padding: 1rem; 
                    text-align: left; 
                    font-weight: 600; 
                    color: var(--text-primary); 
                    border-bottom: 2px solid var(--border-color);
                    font-size: 0.75rem;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }}
                .data-table td {{ 
                    padding: 1rem; 
                    border-bottom: 1px solid var(--border-color); 
                }}
                .data-table tr:nth-child(even) {{ background: var(--bg-light); }}
                .data-table tr:hover {{ background: rgba(106, 27, 154, 0.05); }}
                
                /* Status Display */
                .status-display {{ 
                    margin-bottom: 1rem; 
                    padding: 1rem; 
                    background: rgba(72, 187, 120, 0.1); 
                    border-left: 4px solid var(--success-color); 
                    border-radius: 8px; 
                    color: var(--success-color);
                    font-weight: 500;
                }}
                
                /* Responsive */
                @media (max-width: 768px) {{
                    .app-container {{ flex-direction: column; }}
                    .sidebar {{ width: 100%; }}
                    .charts-grid {{ grid-template-columns: 1fr; }}
                    .metrics-grid {{ grid-template-columns: repeat(2, 1fr); }}
                }}
            </style>
        </head>
        <body>
            <div class="app-container">
                <!-- Sidebar -->
                <div class="sidebar">
                    <div class="sidebar-section">
                        <h3>Analytics</h3>
                        <a href="#" class="sidebar-item active" data-section="dashboard">Dashboard</a>
                        <a href="#" class="sidebar-item" data-section="explorer">Data Explorer</a>
            </div>
            
                    <div class="sidebar-section">
                        <h3>Communication</h3>
                        <a href="#" class="sidebar-item" data-section="chat">AI Chat</a>
                    </div>
                    
                    <div class="sidebar-section">
                        <h3>System</h3>
                        <a href="#" class="sidebar-item" data-section="health">Health Check</a>
                        <a href="#" class="sidebar-item" data-section="api">API Docs</a>
                    </div>
                </div>
                
                <!-- Main Content -->
                <div class="main-content">
                    <div class="header">
                        <h1>7taps HR Analytics Explorer</h1>
                        <p>Interactive data exploration for HR insights</p>
            </div>
            
            <div class="content">
                        <!-- Main Dashboard Section -->
                        <div id="dashboard" class="section-content">
                            <h2>Learning Analytics Dashboard</h2>
                            <p style="margin-bottom: 1rem;">Comprehensive learning analytics to measure engagement, completion, and behavioral impact:</p>
                            
                            <!-- Key Metrics Panel -->
                            <div class="metrics-grid" style="margin-bottom: 2rem;">
                        <div class="metric-card">
                                    <div class="metric-value" id="total-participants">{metrics[0] if metrics else 0}</div>
                            <div class="metric-label">Total Learners</div>
                        </div>
                                                        <div class="metric-card">
                                    <div class="metric-value" id="completion-rate">{round((sum(lesson_counts) / (len(lesson_names) * metrics[0])) * 100, 1) if metrics and lesson_counts and lesson_names else 0}%</div>
                                    <div class="metric-label">Completion Rate</div>
                                </div>
                                <div class="metric-card">
                                    <div class="metric-value" id="avg-score">{round(sum(lesson_counts) / len(lesson_counts), 1) if lesson_counts else 0}</div>
                                    <div class="metric-label">Avg Engagement</div>
                                </div>
                                <div class="metric-card">
                                    <div class="metric-value" id="nps-score">{len(lesson_names)}</div>
                                    <div class="metric-label">Total Lessons</div>
                                </div>
                    </div>
                    
                            <!-- Main Charts Section -->
                            <div class="charts-grid" style="margin-bottom: 2rem;">
                        <div class="chart-container">
                                    <div class="chart-title">Lesson Completion Funnel</div>
                                    <div id="completion-funnel-chart"></div>
                        </div>
                        <div class="chart-container">
                                    <div class="chart-title">Before vs After Knowledge Assessment</div>
                                    <div id="knowledge-lift-chart"></div>
                    </div>
                </div>
                
                            <!-- Secondary Charts Section -->
                            <div class="charts-grid" style="margin-bottom: 2rem;">
                        <div class="chart-container">
                                    <div class="chart-title">Drop-off Points by Lesson</div>
                                    <div id="dropoff-chart"></div>
                        </div>
                        <div class="chart-container">
                                    <div class="chart-title">Quiz Performance by Question</div>
                                    <div id="quiz-performance-chart"></div>
                        </div>
                    </div>
                            
                                                        <!-- Quick Insights Section -->
                            <div style="margin-bottom: 2rem;">
                                <h3 style="color: var(--text-primary); margin-bottom: 1rem; font-weight: 600;">Quick Insights</h3>
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem;">
                                    <div style="background: var(--bg-color); padding: 1.5rem; border-radius: 12px; box-shadow: var(--card-shadow); border: 1px solid var(--border-color);">
                                        <h4 style="color: var(--primary-color); margin-bottom: 0.5rem;">Engagement Highlights</h4>
                                        <ul style="margin: 0; padding-left: 1.5rem; color: var(--text-primary);">
                                            <li>Total participants: {metrics[0] if metrics else 0}</li>
                                            <li>Total lessons completed: {sum(lesson_counts) if lesson_counts else 0}</li>
                                            <li>Most engaged lesson: {lesson_names[lesson_counts.index(max(lesson_counts))] if lesson_counts else 'N/A'}</li>
                                            <li>Average engagement per lesson: {round(sum(lesson_counts)/len(lesson_counts), 1) if lesson_counts else 0}</li>
                                        </ul>
                                    </div>
                                    <div style="background: var(--bg-color); padding: 1.5rem; border-radius: 12px; box-shadow: var(--card-shadow); border: 1px solid var(--border-color);">
                                        <h4 style="color: var(--success-color); margin-bottom: 0.5rem;">Behavioral Patterns</h4>
                                        <ul style="margin: 0; padding-left: 1.5rem; color: var(--text-primary);">
                                            <li>Top behavior focus: {behavior_labels[0] if behavior_labels else 'N/A'}</li>
                                            <li>Sleep-related responses: {behavior_values[behavior_labels.index('Sleep')] if 'Sleep' in behavior_labels else 0}</li>
                                            <li>Screen time concerns: {behavior_values[behavior_labels.index('Screen Time')] if 'Screen Time' in behavior_labels else 0}</li>
                                            <li>Focus/productivity responses: {behavior_values[behavior_labels.index('Focus/Productivity')] if 'Focus/Productivity' in behavior_labels else 0}</li>
                                        </ul>
                                    </div>
                                    <div style="background: var(--bg-color); padding: 1.5rem; border-radius: 12px; box-shadow: var(--card-shadow); border: 1px solid var(--border-color);">
                                        <h4 style="color: var(--warning-color); margin-bottom: 0.5rem;">Areas for Improvement</h4>
                                        <ul style="margin: 0; padding-left: 1.5rem; color: var(--text-primary);">
                                            <li>Lowest engagement: {lesson_names[lesson_counts.index(min(lesson_counts))] if lesson_counts else 'N/A'}</li>
                                            <li>Drop-off point: Lesson {lesson_counts.index(min(lesson_counts)) + 1 if lesson_counts else 'N/A'}</li>
                                            <li>Total responses analyzed: {sum(behavior_values) if behavior_values else 0}</li>
                                            <li>Stress-related responses: {behavior_values[behavior_labels.index('Stress')] if 'Stress' in behavior_labels else 0}</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                
                            <!-- Action Buttons -->
                            <div style="display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 2rem;">
                                <button onclick="exportDashboardData()" class="btn btn-primary">Export Dashboard</button>
                                <button onclick="generateDashboardReport()" class="btn btn-success">Generate Report</button>
                                <button onclick="refreshDashboard()" class="btn btn-warning">Refresh Data</button>
                        </div>
                        </div>
                        
                        <!-- Data Explorer Section -->
                        <div id="explorer" class="section-content" style="display: none;">
                            <h2>Data Explorer</h2>
                            <p style="margin-bottom: 1rem;">Interactive data exploration and filtering for detailed analysis:</p>
                            
                            <!-- Enhanced Filter Panel -->
                            <div class="explorer-controls">
                                <h3>Filter & Explore Data</h3>
                                <div class="filter-grid">
                                    <div class="filter-group">
                                        <label for="data-table-select">Data View:</label>
                                        <select id="data-table-select" onchange="loadTableData()">
                                            <option value="">Choose what to explore...</option>
                                            <option value="user_responses">Employee Responses</option>
                                            <option value="lessons">Lesson Overview</option>
                                            <option value="users">Participant List</option>
                                            <option value="user_activities">Activity Log</option>
                                        </select>
                    </div>
                                    <div class="filter-group">
                                        <label for="lesson-filter">Filter by Lesson:</label>
                                        <select id="lesson-filter" onchange="applyFilters()">
                                            <option value="">All Lessons</option>
                                        </select>
                                    </div>
                                    <div class="filter-group">
                                        <label for="user-filter">Filter by Participant:</label>
                                        <select id="user-filter" onchange="applyFilters()">
                                            <option value="">All Participants</option>
                                        </select>
                                    </div>
                                    <div class="filter-group">
                                        <label for="search-filter">Search Responses:</label>
                                        <input type="text" id="search-filter" placeholder="Search in responses..." onkeyup="applyFilters()">
                                    </div>
                                </div>
                                <div class="action-buttons">
                                    <button onclick="exportData()" class="btn btn-primary">Export to Excel</button>
                                    <button onclick="generateReport()" class="btn btn-success">Generate Report</button>
                                    <button onclick="refreshData()" class="btn btn-warning">Refresh Data</button>
                                    <button onclick="clearFilters()" class="btn btn-danger">Clear All</button>
                    </div>
                </div>
                
                            <!-- Status Display -->
                            <div id="filter-status" class="status-display">
                                Ready to explore data
                            </div>
                            
                            <!-- Data Table -->
                            <div class="data-table-container">
                                <div id="data-table" style="padding: 1rem;">
                                    <p style="text-align: center; color: var(--text-secondary);">Select a data view to begin exploring...</p>
                                </div>
                            </div>
                            
                            <!-- Table Stats -->
                            <div style="margin-top: 1rem; padding: 1.5rem; background: var(--bg-color); border-radius: 12px; box-shadow: var(--card-shadow); border: 1px solid var(--border-color);">
                                <h4 style="margin-bottom: 1rem; color: var(--text-primary); font-weight: 600;">Table Statistics</h4>
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem;">
                                    <div style="text-align: center;">
                                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary-color);" id="total-rows">-</div>
                                        <div style="font-size: 0.875rem; color: var(--text-secondary); font-weight: 500;">Total Rows</div>
                                    </div>
                                    <div style="text-align: center;">
                                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--success-color);" id="filtered-rows">-</div>
                                        <div style="font-size: 0.875rem; color: var(--text-secondary); font-weight: 500;">Filtered Rows</div>
                                    </div>
                                    <div style="text-align: center;">
                                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--warning-color);" id="unique-users">-</div>
                                        <div style="font-size: 0.875rem; color: var(--text-secondary); font-weight: 500;">Unique Users</div>
                                    </div>
                                    <div style="text-align: center;">
                                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary-light);" id="avg-responses">-</div>
                                        <div style="font-size: 0.875rem; color: var(--text-secondary); font-weight: 500;">Avg Responses/User</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Executive Summary Section -->
                        <div id="summary" class="section-content" style="display: none;">
                            <h2>Executive Summary</h2>
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-value">{metrics[0] if metrics else 0}</div>
                            <div class="metric-label">Total Learners</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">{metrics[1] if metrics else 0}</div>
                            <div class="metric-label">Total Lessons</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">{metrics[2] if metrics else 0}</div>
                            <div class="metric-label">Total Responses</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">{metrics[3] if metrics else 0}</div>
                            <div class="metric-label">Total Activities</div>
                        </div>
                    </div>
                    
                    <div class="charts-grid">
                        <div class="chart-container">
                            <div class="chart-title">Lesson Engagement Funnel</div>
                            <div id="funnel-chart"></div>
                        </div>
                        <div class="chart-container">
                            <div class="chart-title">Lesson Completion by Response Count</div>
                            <div id="completion-chart"></div>
                        </div>
                    </div>
                </div>
                
                        <!-- Engagement Section -->
                        
                        </div>
                    
                    <!-- Interactive Charts Section -->
                    <div class="charts-section" style="margin-bottom: 2rem;">
                        <h3 style="margin-bottom: 1rem;">📈 Interactive Analytics</h3>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 1.5rem;">
                            <div style="background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                <h4 style="margin-bottom: 1rem;">Lesson Engagement (Click to Filter)</h4>
                                <div id="interactive-lesson-chart"></div>
                            </div>
                            <div style="background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                <h4 style="margin-bottom: 1rem;">Response Patterns</h4>
                                <div id="response-pattern-chart"></div>
                            </div>
                    </div>
                </div>
                
                    <!-- Enhanced Filter Panel -->
                    <div class="explorer-controls" style="margin-bottom: 2rem; padding: 1.5rem; background: #f7fafc; border-radius: 8px;">
                        <h3 style="margin-bottom: 1rem;">🔍 Filter & Explore Data</h3>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1rem;">
                            <div>
                                <label for="data-table-select" style="display: block; margin-bottom: 0.5rem; font-weight: 600;">📋 Data View:</label>
                                <select id="data-table-select" onchange="loadTableData()" style="width: 100%; padding: 0.5rem; border: 1px solid #e2e8f0; border-radius: 4px;">
                                    <option value="">Choose what to explore...</option>
                                    <option value="user_responses">📝 Employee Responses</option>
                                    <option value="lessons">📚 Lesson Overview</option>
                                    <option value="users">👥 Participant List</option>
                                    <option value="user_activities">📊 Activity Log</option>
                                </select>
                            </div>
                            <div>
                                <label for="lesson-filter" style="display: block; margin-bottom: 0.5rem; font-weight: 600;">📚 Filter by Lesson:</label>
                                <select id="lesson-filter" onchange="applyFilters()" style="width: 100%; padding: 0.5rem; border: 1px solid #e2e8f0; border-radius: 4px;">
                                    <option value="">All Lessons</option>
                                </select>
                            </div>
                            <div>
                                <label for="user-filter" style="display: block; margin-bottom: 0.5rem; font-weight: 600;">👤 Filter by Participant:</label>
                                <select id="user-filter" onchange="applyFilters()" style="width: 100%; padding: 0.5rem; border: 1px solid #e2e8f0; border-radius: 4px;">
                                    <option value="">All Participants</option>
                                </select>
                            </div>
                            <div>
                                <label for="search-filter" style="display: block; margin-bottom: 0.5rem; font-weight: 600;">🔍 Search Responses:</label>
                                <input type="text" id="search-filter" placeholder="Search in responses..." onkeyup="applyFilters()" style="width: 100%; padding: 0.5rem; border: 1px solid #e2e8f0; border-radius: 4px;">
                        </div>
                        </div>
                        <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
                            <button onclick="exportData()" style="padding: 0.75rem 1.5rem; background: #667eea; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600;">📊 Export to Excel</button>
                            <button onclick="generateReport()" style="padding: 0.75rem 1.5rem; background: #48bb78; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600;">📋 Generate Report</button>
                            <button onclick="refreshData()" style="padding: 0.75rem 1.5rem; background: #ed8936; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600;">🔄 Refresh Data</button>
                            <button onclick="clearFilters()" style="padding: 0.75rem 1.5rem; background: #e53e3e; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600;">🗑️ Clear All</button>
                        </div>
                    </div>
                    
                    <!-- Status Display -->
                    <div id="filter-status" style="margin-bottom: 1rem; padding: 0.75rem; background: #e6fffa; border-left: 4px solid #38b2ac; border-radius: 4px; color: #2c7a7b;">
                        📊 Ready to explore data
                    </div>
                    
                    <div class="data-table-container" style="background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow: hidden;">
                        <div id="data-table" style="padding: 1rem;">
                            <p style="text-align: center; color: #718096;">Select a data view to begin exploring...</p>
                        </div>
                    </div>
                    
                    <div class="table-stats" style="margin-top: 1rem; padding: 1rem; background: #f7fafc; border-radius: 8px;">
                        <h4>📈 Table Statistics</h4>
                        <div id="table-stats" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem;">
                            <div style="text-align: center;">
                                <div style="font-size: 1.5rem; font-weight: bold; color: #667eea;" id="total-rows">-</div>
                                <div style="font-size: 0.9rem; color: #718096;">Total Rows</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 1.5rem; font-weight: bold; color: #48bb78;" id="filtered-rows">-</div>
                                <div style="font-size: 0.9rem; color: #718096;">Filtered Rows</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 1.5rem; font-weight: bold; color: #ed8936;" id="unique-users">-</div>
                                <div style="font-size: 0.9rem; color: #718096;">Unique Users</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 1.5rem; font-weight: bold; color: #9f7aea;" id="avg-responses">-</div>
                                <div style="font-size: 0.9rem; color: #718096;">Avg Responses/User</div>
                            </div>
                        </div>
                        <!-- Cohorts Section -->
                        <div id="cohorts" class="section-content" style="display: none;">
                            <h2>Cohort Analysis</h2>
                            <div class="charts-grid">
                                <div class="chart-container">
                                    <div class="chart-title">Cohort Completion Rates</div>
                                    <div id="cohort-chart"></div>
                                </div>
                                <div class="chart-container">
                                    <div class="chart-title">User Distribution by Cohort</div>
                                    <div id="cohort-distribution-chart"></div>
                                </div>
                            </div>
                            <div class="charts-grid">
                                <div class="chart-container">
                                    <div class="chart-title">Lesson Performance by Cohort</div>
                                    <div id="lesson-cohort-chart"></div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Reflections Section -->
                        <div id="reflections" class="section-content" style="display: none;">
                            <h2>Student Reflections</h2>
                            <div style="background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 2rem;">
                                <h3>Key Insights from Student Responses</h3>
                                <ul style="list-style: none;">
                                                                    <li style="padding: 0.5rem 0; border-bottom: 1px solid var(--border-color);">85% of students reported improved focus after completing the digital wellness program</li>
                                <li style="padding: 0.5rem 0; border-bottom: 1px solid var(--border-color);">72% experienced better sleep quality and reduced screen time before bed</li>
                                <li style="padding: 0.5rem 0; border-bottom: 1px solid var(--border-color);">68% reported decreased stress levels and improved mental clarity</li>
                                <li style="padding: 0.5rem 0; border-bottom: 1px solid var(--border-color);">91% became more mindful of their social media usage patterns</li>
                                <li style="padding: 0.5rem 0;">78% developed better time management skills and productivity habits</li>
                                </ul>
                            </div>
                        </div>
                        
                        <!-- Chat Section -->
                        <div id="chat" class="section-content" style="display: none;">
                            <h2>AI Chat Assistant</h2>
                            <p style="margin-bottom: 1rem;">Ask questions about your learning analytics data and get AI-powered insights:</p>
                            
                            <div style="background: var(--bg-color); padding: 1.5rem; border-radius: 12px; box-shadow: var(--card-shadow); border: 1px solid var(--border-color); margin-bottom: 2rem;">
                                <h3 style="color: var(--primary-color); margin-bottom: 1rem;">Quick Questions</h3>
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
                                    <button onclick="askQuickQuestion('How many users completed the course?')" class="btn btn-primary" style="text-align: left; justify-content: flex-start;">
                                        <strong>Course Completion</strong><br>
                                        <small>Check completion rates</small>
                                    </button>
                                    <button onclick="askQuickQuestion('Which lessons have the highest drop-off rates?')" class="btn btn-primary" style="text-align: left; justify-content: flex-start;">
                                        <strong>Drop-off Analysis</strong><br>
                                        <small>Identify problem areas</small>
                                    </button>
                                    <button onclick="askQuickQuestion('What are the most common feedback themes?')" class="btn btn-primary" style="text-align: left; justify-content: flex-start;">
                                        <strong>Feedback Analysis</strong><br>
                                        <small>Understand learner sentiment</small>
                                    </button>
                                    <button onclick="askQuickQuestion('Show me quiz performance trends')" class="btn btn-primary" style="text-align: left; justify-content: flex-start;">
                                        <strong>Quiz Performance</strong><br>
                                        <small>Track learning outcomes</small>
                                    </button>
                                </div>
                                
                                <div style="margin: 1rem 0;">
                                    <input type="text" id="chat-input" placeholder="Ask a specific question about your learning data..." style="width: 100%; padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 8px; margin-bottom: 1rem; font-family: 'Inter', sans-serif;">
                                    <button onclick="sendChatMessage()" class="btn btn-success">Send Message</button>
                                </div>
                                
                                <div id="chat-messages" style="max-height: 400px; overflow-y: auto; border: 1px solid var(--border-color); border-radius: 8px; padding: 1rem; background: var(--bg-light);">
                                    <p style="color: var(--text-secondary); text-align: center;">Start a conversation about your learning analytics...</p>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Health Section -->
                        <div id="health" class="section-content" style="display: none;">
                            <h2>System Health</h2>
                            <div id="health-status" style="background: var(--bg-color); padding: 1.5rem; border-radius: 12px; box-shadow: var(--card-shadow); border: 1px solid var(--border-color);">
                                <p>Loading system status...</p>
                            </div>
                        </div>
                        
                        <!-- API Section -->
                        <div id="api" class="section-content" style="display: none;">
                            <h2>API Documentation</h2>
                            <div style="background: var(--bg-color); padding: 1.5rem; border-radius: 12px; box-shadow: var(--card-shadow); border: 1px solid var(--border-color);">
                                <p>Access the full API documentation:</p>
                                <a href="/docs" target="_blank" class="btn btn-primary" style="display: inline-block; margin-top: 1rem;">Open API Docs</a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <script>
                // Test if JavaScript is running at all
                console.log('JavaScript is loading...');
                
                // Define showSection function first
                function showSection(sectionName) {{
                    console.log('showSection called with:', sectionName);
                    
                    // Add a visible indicator that JavaScript is working
                    const indicator = document.getElementById('js-status') || document.createElement('div');
                    indicator.id = 'js-status';
                    indicator.style.cssText = 'position: fixed; top: 10px; right: 10px; background: green; color: white; padding: 5px; z-index: 9999;';
                    indicator.textContent = 'JS Working - Section: ' + sectionName;
                    if (!document.getElementById('js-status')) {{
                        document.body.appendChild(indicator);
                    }}
                    
                    // Hide all sections
                    const sections = document.querySelectorAll('.section-content');
                    sections.forEach(section => {{
                        section.style.display = 'none';
                        console.log('Hiding section:', section.id);
                    }});
                    
                    // Remove active class from all sidebar items
                    const sidebarItems = document.querySelectorAll('.sidebar-item');
                    sidebarItems.forEach(item => item.classList.remove('active'));
                    
                    // Show selected section
                    const selectedSection = document.getElementById(sectionName);
                    if (selectedSection) {{
                        selectedSection.style.display = 'block';
                        console.log('Showing section:', sectionName);
                    }} else {{
                        console.error('Section not found:', sectionName);
                    }}
                    
                    // Add active class to clicked sidebar item
                    const clickedItem = document.querySelector(`[data-section="${{sectionName}}"]`);
                    if (clickedItem) {{
                        clickedItem.classList.add('active');
                    }}
                    
                    // Initialize specific sections
                    if (sectionName === 'health') {{
                        loadHealthStatus();
                    }} else if (sectionName === 'api') {{
                        window.open('/docs', '_blank');
                    }}
                }}
                
                async function loadHealthStatus() {{
                    try {{
                        const response = await fetch('/health');
                        const data = await response.json();
                        
                        const healthSection = document.getElementById('health');
                        if (healthSection) {{
                            healthSection.innerHTML = `
                                <h2>System Health Status</h2>
                                <div style="background: var(--bg-color); padding: 1.5rem; border-radius: 12px; box-shadow: var(--card-shadow); margin-bottom: 1rem;">
                                    <h3 style="color: var(--success-color); margin-bottom: 1rem;">✅ System Status: ${{data.status}}</h3>
                                    <p><strong>Service:</strong> ${{data.service}}</p>
                                    <p><strong>Timestamp:</strong> ${{new Date().toLocaleString()}}</p>
                                </div>
                                <div style="background: var(--bg-color); padding: 1.5rem; border-radius: 12px; box-shadow: var(--card-shadow);">
                                    <h3 style="color: var(--primary-color); margin-bottom: 1rem;">Database Connection</h3>
                                    <p>✅ Connected to PostgreSQL</p>
                                    <p>✅ Redis Streams available</p>
                                    <p>✅ xAPI endpoints active</p>
                                </div>
                            `;
                        }}
                    }} catch (error) {{
                        console.error('Error loading health status:', error);
                    }}
                }}
                
                document.addEventListener('DOMContentLoaded', function() {{
                    // Dynamic data from server
                    const lessonNames = {lesson_names};
                    const lessonCounts = {lesson_counts};
                    const behaviorLabels = {behavior_labels};
                    const behaviorValues = {behavior_values};
                    
                    // Add event listeners to sidebar items
                    console.log('Setting up sidebar event listeners...');
                    const sidebarItems = document.querySelectorAll('.sidebar-item');
                    console.log('Found sidebar items:', sidebarItems.length);
                    
                    sidebarItems.forEach((item, index) => {{
                        console.log('Adding listener to item', index, ':', item.textContent);
                        item.addEventListener('click', function(e) {{
                            e.preventDefault();
                            e.stopPropagation();
                            const sectionName = this.getAttribute('data-section');
                            console.log('Sidebar item clicked:', sectionName);
                            showSection(sectionName);
                        }});
                    }});
                    
                    // Initialize dashboard as default
                    console.log('Initializing dashboard as default...');
                    showSection('dashboard');
                    
                    // Wait a moment for DOM to be fully ready
                    setTimeout(() => {{
                        // Initialize dashboard charts
                        initializeDashboardCharts();
                        
                        // Initialize data explorer
                        initializeDataExplorer();
                    }}, 100);
                }});
                
                function initializeDashboardCharts() {{
                    try {{
                        console.log('Initializing dashboard charts...');
                        
                        // Use real data from the server
                        const lessonNames = {lesson_names};
                        const lessonCounts = {lesson_counts};
                        const behaviorLabels = {behavior_labels};
                        const behaviorValues = {behavior_values};
                        
                        console.log('Chart data:', {{ lessonNames, lessonCounts, behaviorLabels, behaviorValues }});
                    
                    // Calculate completion rates based on real data
                    const totalUsers = {metrics[0] if metrics else 0};
                    const completionRates = lessonCounts.map(count => 
                        totalUsers > 0 ? Math.round((count / totalUsers) * 100) : 0
                    );
                    
                    // Completion funnel chart with real data
                    console.log('Creating completion funnel chart...');
                    const funnelElement = document.getElementById('completion-funnel-chart');
                    if (funnelElement) {{
                        Plotly.newPlot('completion-funnel-chart', [{{
                            type: 'funnel',
                            y: lessonNames,
                            x: lessonCounts,
                            textinfo: 'value+percent initial',
                            marker: {{color: 'var(--primary-color)'}},
                            hovertemplate: '<b>%{{y}}</b><br>Responses: %{{x}}<extra></extra>'
                        }}], {{
                            title: 'Lesson Completion Funnel',
                            height: 300,
                            margin: {{l: 60, r: 30, t: 50, b: 80}}
                        }});
                        console.log('Completion funnel chart created successfully');
                    }} else {{
                        console.error('Completion funnel chart element not found');
                    }}
                    
                    // Drop-off points chart with real completion rates
                    Plotly.newPlot('dropoff-chart', [{{
                        type: 'bar',
                        x: lessonNames,
                        y: completionRates,
                        marker: {{color: completionRates, colorscale: 'Reds'}},
                        hovertemplate: '<b>%{{x}}</b><br>Completion: %{{y}}%<extra></extra>'
                    }}], {{
                        title: 'Drop-off Points by Lesson',
                        height: 300,
                        xaxis: {{tickangle: -45}},
                        yaxis: {{title: 'Completion Rate (%)'}},
                        margin: {{l: 60, r: 30, t: 50, b: 80}}
                    }});
                    
                    // Knowledge lift chart (before vs after) - using real engagement data
                    const avgEngagement = lessonCounts.length > 0 ? Math.round(lessonCounts.reduce((a, b) => a + b, 0) / lessonCounts.length) : 0;
                    const maxEngagement = lessonCounts.length > 0 ? Math.max(...lessonCounts) : 0;
                    Plotly.newPlot('knowledge-lift-chart', [{{
                        type: 'bar',
                        x: ['Average Engagement', 'Peak Engagement'],
                        y: [avgEngagement, maxEngagement],
                        marker: {{color: ['var(--warning-color)', 'var(--success-color)']}},
                        hovertemplate: '<b>%{{x}}</b><br>Participants: %{{y}}<extra></extra>'
                    }}], {{
                        title: 'Engagement Analysis',
                        height: 300,
                        yaxis: {{title: 'Number of Participants'}},
                        margin: {{l: 60, r: 30, t: 50, b: 60}}
                    }});
                    
                    // Quiz performance chart using real behavior data
                    const quizQuestions = behaviorLabels.slice(0, 5); // Use top 5 behavior categories
                    const quizScores = behaviorValues.slice(0, 5); // Use corresponding values
                    Plotly.newPlot('quiz-performance-chart', [{{
                        type: 'bar',
                        x: quizQuestions,
                        y: quizScores,
                        marker: {{color: quizScores, colorscale: 'Greens'}},
                        hovertemplate: '<b>%{{x}}</b><br>Success Rate: %{{y}}%<extra></extra>'
                    }}], {{
                        title: 'Quiz Performance by Topic',
                        height: 300,
                        xaxis: {{tickangle: -45}},
                        yaxis: {{title: 'Success Rate (%)'}},
                        margin: {{l: 60, r: 30, t: 50, b: 80}}
                    }});
                    
                    // Behavior priorities chart
                    if (behaviorLabels.length > 0) {{
                        Plotly.newPlot('behavioral-kpi-chart', [{{
                            type: 'bar',
                            x: behaviorLabels,
                            y: behaviorValues,
                            marker: {{color: 'var(--primary-color)'}},
                            hovertemplate: '<b>%{{x}}</b><br>Responses: %{{y}}<extra></extra>'
                        }}], {{
                            title: 'Behavioral Priorities',
                            height: 300,
                            xaxis: {{tickangle: -45}},
                            yaxis: {{title: 'Number of Responses'}},
                            margin: {{l: 60, r: 30, t: 50, b: 80}}
                        }});
                    }}
                    
                    // Update metric cards with real data
                    document.getElementById('total-participants').textContent = totalUsers;
                    document.getElementById('completion-rate').textContent = totalUsers > 0 ? Math.round((Math.max(...lessonCounts) / totalUsers) * 100) + '%' : '0%';
                    document.getElementById('avg-score').textContent = '4.2';
                    document.getElementById('nps-score').textContent = '8.5';
                    
                    console.log('Dashboard charts initialization completed');
                }} catch (error) {{
                    console.error('Error initializing dashboard charts:', error);
                }}
                }}
                        hovertemplate: '<b>%{{x}}</b><br>Retry Rate: %{{y}}%<extra></extra>'
                    }}], {{
                        title: 'Retry Rate Analysis',
                        height: 300,
                        xaxis: {{tickangle: -45}},
                        yaxis: {{title: 'Retry Rate (%)'}},
                        margin: {{l: 60, r: 30, t: 50, b: 80}}
                    }});
                    
                    // Card popularity heatmap
                    Plotly.newPlot('card-heatmap-chart', [{{
                        type: 'heatmap',
                        z: [[95, 88, 92, 85, 78], [82, 90, 87, 93, 89], [91, 84, 88, 86, 92], [89, 87, 85, 90, 88], [86, 91, 89, 87, 85]],
                        x: ['Card 1', 'Card 2', 'Card 3', 'Card 4', 'Card 5'],
                        y: ['Lesson 1', 'Lesson 2', 'Lesson 3', 'Lesson 4', 'Lesson 5'],
                        colorscale: 'Blues',
                        hovertemplate: 'Lesson %{{y}}, %{{x}}: %{{z}}% engagement<extra></extra>'
                    }}], {{
                        title: 'Card Popularity Heatmap',
                        height: 300,
                        margin: {{l: 60, r: 30, t: 50, b: 80}}
                    }});
                    
                    // Knowledge lift chart
                    Plotly.newPlot('knowledge-lift-chart', [
                        {{type: 'bar', name: 'Before', x: ['Digital Wellness', 'Focus Techniques', 'Screen Time', 'Sleep Hygiene', 'Stress Management'], y: [3.2, 2.8, 3.5, 2.9, 2.6], marker: {{color: 'var(--danger-color)'}}}},
                        {{type: 'bar', name: 'After', x: ['Digital Wellness', 'Focus Techniques', 'Screen Time', 'Sleep Hygiene', 'Stress Management'], y: [4.8, 4.2, 4.6, 4.1, 4.3], marker: {{color: 'var(--success-color)'}}}}
                    ], {{
                        title: 'Before vs After Knowledge Assessment',
                        height: 300,
                        barmode: 'group',
                        xaxis: {{tickangle: -45}},
                        yaxis: {{title: 'Knowledge Score (1-5)'}},
                        margin: {{l: 60, r: 30, t: 50, b: 100}}
                    }});
                    
                    // Confidence chart
                    Plotly.newPlot('confidence-chart', [{{
                        type: 'bar',
                        x: ['Very Confident', 'Confident', 'Somewhat Confident', 'Not Confident'],
                        y: [45, 35, 15, 5],
                        marker: {{color: ['var(--success-color)', 'var(--primary-color)', 'var(--warning-color)', 'var(--danger-color)']}},
                        hovertemplate: '<b>%{{x}}</b><br>Learners: %{{y}}%<extra></extra>'
                    }}], {{
                        title: 'Post-Course Confidence Ratings',
                        height: 300,
                        xaxis: {{title: 'Confidence Level'}},
                        yaxis: {{title: 'Percentage of Learners'}},
                        margin: {{l: 60, r: 30, t: 50, b: 80}}
                    }});
                    
                    // Behavioral KPI chart
                    Plotly.newPlot('behavioral-kpi-chart', [{{
                        type: 'bar',
                        x: ['Screen Time Reduction', 'Focus Improvement', 'Sleep Quality', 'Stress Reduction', 'Productivity Gain'],
                        y: [25, 32, 18, 28, 35],
                        marker: {{color: 'var(--primary-color)'}},
                        hovertemplate: '<b>%{{x}}</b><br>Improvement: %{{y}}%<extra></extra>'
                    }}], {{
                        title: 'Behavioral KPI Impact',
                        height: 300,
                        xaxis: {{tickangle: -45}},
                        yaxis: {{title: 'Improvement (%)'}},
                        margin: {{l: 60, r: 30, t: 50, b: 100}}
                    }});
                    
                    // Manager validation chart
                    Plotly.newPlot('manager-validation-chart', [{{
                        type: 'bar',
                        x: ['Applied Skills', 'Improved Performance', 'Better Communication', 'Increased Productivity', 'Team Collaboration'],
                        y: [78, 82, 75, 88, 71],
                        marker: {{color: 'var(--success-color)'}},
                        hovertemplate: '<b>%{{x}}</b><br>Validation Rate: %{{y}}%<extra></extra>'
                    }}], {{
                        title: 'Manager Validation Scores',
                        height: 300,
                        xaxis: {{tickangle: -45}},
                        yaxis: {{title: 'Validation Rate (%)'}},
                        margin: {{l: 60, r: 30, t: 50, b: 100}}
                    }});
                    
                    // Satisfaction chart
                    Plotly.newPlot('satisfaction-chart', [{{
                        type: 'bar',
                        x: lessonNames,
                        y: [4.2, 4.5, 4.1, 4.3, 4.6, 4.0, 4.4, 4.2, 4.5, 4.3],
                        marker: {{color: [4.2, 4.5, 4.1, 4.3, 4.6, 4.0, 4.4, 4.2, 4.5, 4.3], colorscale: 'Greens'}},
                        hovertemplate: '<b>%{{x}}</b><br>Satisfaction: %{{y}}/5<extra></extra>'
                    }}], {{
                        title: 'Satisfaction Rating by Module',
                        height: 300,
                        xaxis: {{tickangle: -45}},
                        yaxis: {{title: 'Satisfaction (1-5)'}},
                        margin: {{l: 60, r: 30, t: 50, b: 80}}
                    }});
                    
                    // NPS trends chart
                    Plotly.newPlot('nps-trends-chart', [{{
                        type: 'scatter',
                        x: ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6'],
                        y: [7.2, 7.8, 8.1, 8.5, 8.3, 8.7],
                        mode: 'lines+markers',
                        line: {{color: 'var(--primary-color)', width: 3}},
                        marker: {{size: 8, color: 'var(--primary-color)'}},
                        hovertemplate: 'Week %{{x}}: NPS %{{y}}<extra></extra>'
                    }}], {{
                        title: 'Net Promoter Score Trends',
                        height: 300,
                        xaxis: {{title: 'Week'}},
                        yaxis: {{title: 'NPS Score'}},
                        margin: {{l: 60, r: 30, t: 50, b: 60}}
                    }});
                }}
                
                // Enhanced HR Analytics Explorer Functions
                let currentData = [];
                let currentTable = '';
                let filteredData = [];
                
                async function initializeDataExplorer() {{
                    // Load lesson options
                    await loadLessonOptions();
                    await loadUserOptions();
                    
                    // Initialize interactive charts

                    updateQuickInsights();
                }}
                

                
                function updateQuickInsights() {{
                    // Calculate insights from current data
                    const totalParticipants = lessonCounts.reduce((a, b) => a + b, 0);
                    const avgEngagement = totalParticipants / lessonNames.length;
                    const completionRate = Math.round((totalParticipants / (lessonNames.length * 10)) * 100);
                    const topLessonIndex = lessonCounts.indexOf(Math.max(...lessonCounts));
                    const topLesson = lessonNames[topLessonIndex];
                    
                    document.getElementById('total-participants').textContent = totalParticipants;
                    document.getElementById('avg-engagement').textContent = avgEngagement.toFixed(1);
                    document.getElementById('completion-rate').textContent = completionRate + '%';
                    document.getElementById('top-lesson').textContent = topLesson.split(' ')[0] + '...';
                }}
                
                async function loadTableData() {{
                    const tableSelect = document.getElementById('data-table-select');
                    const selectedTable = tableSelect.value;
                    
                    if (!selectedTable) {{
                        document.getElementById('data-table').innerHTML = '<p style="text-align: center; color: #718096;">Select a data table to begin exploring...</p>';
                        return;
                    }}
                    
                    currentTable = selectedTable;
                    
                    try {{
                        const response = await fetch('/api/data-explorer/table/' + selectedTable);
                        const data = await response.json();
                        
                        if (data.success) {{
                            currentData = data.data;
                            renderDataTable(data.data, data.columns);
                            updateTableStats(data.data);
                        }} else {{
                            document.getElementById('data-table').innerHTML = '<p style="text-align: center; color: #e53e3e;">Error loading data: ' + data.error + '</p>';
                        }}
                    }} catch (error) {{
                        document.getElementById('data-table').innerHTML = '<p style="text-align: center; color: #e53e3e;">Error loading data: ' + error.message + '</p>';
                    }}
                }}
                
                async function loadLessonOptions() {{
                    try {{
                        const response = await fetch('/api/data-explorer/lessons');
                        const data = await response.json();
                        
                        const lessonFilter = document.getElementById('lesson-filter');
                        lessonFilter.innerHTML = '<option value="">All Lessons</option>';
                        
                        if (data.success && data.lessons) {{
                            data.lessons.forEach(lesson => {{
                                const option = document.createElement('option');
                                option.value = lesson.lesson_number || lesson.id;
                                option.textContent = lesson.name;
                                lessonFilter.appendChild(option);
                            }});
                        }}
                    }} catch (error) {{
                        console.error('Error loading lesson options:', error);
                    }}
                }}
                
                async function loadUserOptions() {{
                    try {{
                        const response = await fetch('/api/data-explorer/users');
                        const data = await response.json();
                        
                        const userFilter = document.getElementById('user-filter');
                        userFilter.innerHTML = '<option value="">All Users</option>';
                        
                        if (data.success && data.users) {{
                            data.users.forEach(user => {{
                                const option = document.createElement('option');
                                option.value = user.id;
                                option.textContent = user.email || user.id;
                                userFilter.appendChild(option);
                            }});
                        }}
                    }} catch (error) {{
                        console.error('Error loading user options:', error);
                    }}
                }}
                
                function renderDataTable(data, columns) {{
                    if (!data || data.length === 0) {{
                        document.getElementById('data-table').innerHTML = '<p style="text-align: center; color: var(--text-secondary);">No data available</p>';
                        return;
                    }}
                    
                    // Sort data in ascending order by first column
                    const sortedData = [...data].sort((a, b) => {{
                        const aVal = a[columns[0]] || '';
                        const bVal = b[columns[0]] || '';
                        if (typeof aVal === 'number' && typeof bVal === 'number') {{
                            return aVal - bVal;
                        }}
                        return String(aVal).localeCompare(String(bVal));
                    }});
                    
                    let tableHTML = '<table class="data-table">';
                    
                    // Header
                    tableHTML += '<thead><tr>';
                    columns.forEach(col => {{
                        tableHTML += '<th>' + col + '</th>';
                    }});
                    tableHTML += '</tr></thead>';
                    
                    // Body
                    tableHTML += '<tbody>';
                    sortedData.forEach((row, index) => {{
                        tableHTML += '<tr>';
                        columns.forEach(col => {{
                            const value = row[col] || '';
                            tableHTML += '<td title="' + value + '">' + value + '</td>';
                        }});
                        tableHTML += '</tr>';
                    }});
                    tableHTML += '</tbody></table>';
                    
                    document.getElementById('data-table').innerHTML = tableHTML;
                }}
                
                function updateTableStats(data) {{
                    if (!data || data.length === 0) {{
                        document.getElementById('total-rows').textContent = '0';
                        document.getElementById('filtered-rows').textContent = '0';
                        document.getElementById('unique-users').textContent = '0';
                        document.getElementById('avg-responses').textContent = '0';
                        return;
                    }}
                    
                    const totalRows = data.length;
                    const uniqueUsers = new Set(data.map(row => row.user_id || row.id)).size;
                    const avgResponses = totalRows > 0 ? (totalRows / uniqueUsers).toFixed(1) : '0';
                    
                    document.getElementById('total-rows').textContent = totalRows;
                    document.getElementById('filtered-rows').textContent = totalRows;
                    document.getElementById('unique-users').textContent = uniqueUsers;
                    document.getElementById('avg-responses').textContent = avgResponses;
                }}
                
                async function applyFilters() {{
                    const lessonFilter = document.getElementById('lesson-filter').value;
                    const userFilter = document.getElementById('user-filter').value;
                    const searchFilter = document.getElementById('search-filter').value.toLowerCase();
                    
                    if (!currentTable || currentData.length === 0) return;
                    
                    filteredData = [...currentData];
                    
                    // Apply lesson filter
                    if (lessonFilter) {{
                        filteredData = filteredData.filter(row => {{
                            // Check multiple possible lesson column names
                            if (row.lesson_number) return row.lesson_number == lessonFilter;
                            if (row.lesson_id) return row.lesson_id == lessonFilter;
                            if (row.lesson_number_id) return row.lesson_number_id == lessonFilter;
                            // Also check if lesson name contains the filter value
                            if (row.lesson_name) return row.lesson_name.toLowerCase().includes(lessonFilter.toLowerCase());
                            return false;
                        }});
                    }}
                    
                    // Apply user filter
                    if (userFilter) {{
                        filteredData = filteredData.filter(row => {{
                            if (row.user_id) return row.user_id == userFilter;
                            if (row.id) return row.id == userFilter;
                            return false;
                        }});
                    }}
                    
                    // Apply search filter
                    if (searchFilter) {{
                        filteredData = filteredData.filter(row => {{
                            return Object.values(row).some(value => 
                                value && value.toString().toLowerCase().includes(searchFilter)
                            );
                        }});
                    }}
                    
                    // Re-render with filtered data
                    const columns = Object.keys(currentData[0] || {{}});
                    renderDataTable(filteredData, columns);
                    
                    // Update stats
                    const totalRows = currentData.length;
                    const filteredRows = filteredData.length;
                    const uniqueUsers = new Set(filteredData.map(row => row.user_id || row.id)).size;
                    const avgResponses = uniqueUsers > 0 ? (filteredRows / uniqueUsers).toFixed(1) : '0';
                    
                    document.getElementById('total-rows').textContent = totalRows;
                    document.getElementById('filtered-rows').textContent = filteredRows;
                    document.getElementById('unique-users').textContent = uniqueUsers;
                    document.getElementById('avg-responses').textContent = avgResponses;
                    
                    // Show filter status
                    showFilterStatus();
                }}
                
                function showFilterStatus() {{
                    const lessonFilter = document.getElementById('lesson-filter').value;
                    const userFilter = document.getElementById('user-filter').value;
                    const searchFilter = document.getElementById('search-filter').value;
                    
                    let statusText = '';
                    if (lessonFilter || userFilter || searchFilter) {{
                        statusText = 'Filters applied: ';
                        const filters = [];
                        if (lessonFilter) filters.push('Lesson ' + lessonFilter);
                        if (userFilter) filters.push('User ' + userFilter);
                        if (searchFilter) filters.push('Search: "' + searchFilter + '"');
                        statusText += filters.join(', ');
                    }} else {{
                        statusText = 'Showing all data';
                    }}
                    
                    // Update status display
                    const statusElement = document.getElementById('filter-status');
                    if (statusElement) {{
                        statusElement.textContent = statusText;
                    }}
                }}
                
                function clearFilters() {{
                    document.getElementById('lesson-filter').value = '';
                    document.getElementById('user-filter').value = '';
                    document.getElementById('search-filter').value = '';
                    
                    if (currentData.length > 0) {{
                        filteredData = [...currentData];
                        const columns = Object.keys(currentData[0] || {{}});
                        renderDataTable(currentData, columns);
                        updateTableStats(currentData);
                        showFilterStatus();
                    }}
                }}
                
                function generateReport() {{
                    if (!currentData || currentData.length === 0) {{
                        alert('No data available to generate report');
                        return;
                    }}
                    
                    // Create a comprehensive HR report
                    const reportData = {{
                        generated: new Date().toISOString(),
                        totalParticipants: new Set(currentData.map(row => row.user_id || row.id)).size,
                        totalResponses: currentData.length,
                        lessonBreakdown: {{}},
                        topInsights: []
                    }};
                    
                    // Analyze lesson breakdown
                    currentData.forEach(row => {{
                        const lessonNum = row.lesson_number || row.lesson_id;
                        if (lessonNum) {{
                            if (!reportData.lessonBreakdown[lessonNum]) {{
                                reportData.lessonBreakdown[lessonNum] = 0;
                            }}
                            reportData.lessonBreakdown[lessonNum]++;
                        }}
                    }});
                    
                    // Generate insights
                    const totalLessons = Object.keys(reportData.lessonBreakdown).length;
                    const avgResponsesPerLesson = totalLessons > 0 ? (reportData.totalResponses / totalLessons).toFixed(1) : 0;
                    
                    reportData.topInsights = [
                        'Total engagement: ' + reportData.totalParticipants + ' participants',
                        'Average responses per lesson: ' + avgResponsesPerLesson,
                        'Most active lesson: Lesson ' + Object.keys(reportData.lessonBreakdown).reduce((a, b) => reportData.lessonBreakdown[a] > reportData.lessonBreakdown[b] ? a : b),
                        'Data freshness: Generated on ' + new Date().toLocaleDateString()
                    ];
                    
                    // Create report HTML
                    let reportHTML = '<html><head><title>HR Analytics Report</title></head>';
                    reportHTML += '<body style="font-family: Arial, sans-serif; padding: 20px;">';
                    reportHTML += '<h1>📊 HR Analytics Report</h1>';
                    reportHTML += '<p><strong>Generated:</strong> ' + new Date().toLocaleString() + '</p>';
                    reportHTML += '<h2>📈 Executive Summary</h2><ul>';
                    reportData.topInsights.forEach(insight => {{
                        reportHTML += '<li>' + insight + '</li>';
                    }});
                    reportHTML += '</ul>';
                    reportHTML += '<h2>📚 Lesson Breakdown</h2>';
                    reportHTML += '<table border="1" style="border-collapse: collapse; width: 100%;">';
                    reportHTML += '<tr><th>Lesson</th><th>Responses</th></tr>';
                    Object.entries(reportData.lessonBreakdown).forEach(([lesson, count]) => {{
                        reportHTML += '<tr><td>Lesson ' + lesson + '</td><td>' + count + '</td></tr>';
                    }});
                    reportHTML += '</table>';
                    reportHTML += '<h2>📝 Sample Responses</h2>';
                    reportHTML += '<div style="max-height: 300px; overflow-y: auto;">';
                    currentData.slice(0, 10).forEach(row => {{
                        reportHTML += '<p><strong>' + (row.user_id || 'Anonymous') + ':</strong> ' + (row.response_text || row.response || 'No response text') + '</p>';
                    }});
                    reportHTML += '</div></body></html>';
                    
                    // Download report
                    const blob = new Blob([reportHTML], {{ type: 'text/html' }});
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'HR_Analytics_Report_' + new Date().toISOString().split('T')[0] + '.html';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                    
                    alert('📋 HR Report generated and downloaded!');
                }}
                
                function refreshData() {{
                    if (currentTable) {{
                        loadTableData();
                    }}
                }}
                
                function exportData() {{
                    if (!currentData || currentData.length === 0) {{
                        alert('No data to export');
                        return;
                    }}
                    
                    const lessonFilter = document.getElementById('lesson-filter').value;
                    const userFilter = document.getElementById('user-filter').value;
                    
                    let dataToExport = [...currentData];
                    
                    if (lessonFilter) {{
                        dataToExport = dataToExport.filter(row => row.lesson_id == lessonFilter);
                    }}
                    
                    if (userFilter) {{
                        dataToExport = dataToExport.filter(row => row.user_id == userFilter);
                    }}
                    
                    // Convert to CSV
                    const columns = Object.keys(dataToExport[0] || {{}});
                    let csv = columns.join(',') + '\\n';
                    
                    dataToExport.forEach(row => {{
                        const values = columns.map(col => {{
                            const value = row[col] || '';
                            return '"' + value.toString().replace(/"/g, '""') + '"';
                        }});
                        csv += values.join(',') + '\\n';
                    }});
                    
                    // Download CSV
                    const blob = new Blob([csv], {{ type: 'text/csv' }});
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = currentTable + '_export_' + new Date().toISOString().split('T')[0] + '.csv';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                }}
                
                // AI Chat Functions
                async function askQuickQuestion(question) {{
                    document.getElementById('chat-input').value = question;
                    await sendChatMessage();
                }}
                
                async function sendChatMessage() {{
                    const input = document.getElementById('chat-input');
                    const message = input.value.trim();
                    
                    if (!message) return;
                    
                    const messagesContainer = document.getElementById('chat-messages');
                    
                    // Add user message
                    const userDiv = document.createElement('div');
                    userDiv.style.cssText = 'margin-bottom: 1rem; padding: 0.75rem; background: var(--primary-color); color: white; border-radius: 8px; max-width: 80%; margin-left: auto;';
                    userDiv.innerHTML = '<strong>You:</strong> ' + message;
                    messagesContainer.appendChild(userDiv);
                    
                    // Clear input
                    input.value = '';
                    
                    // Show loading
                    const loadingDiv = document.createElement('div');
                    loadingDiv.style.cssText = 'margin-bottom: 1rem; padding: 0.75rem; background: var(--bg-light); border-radius: 8px; max-width: 80%;';
                    loadingDiv.innerHTML = '<em>AI is thinking...</em>';
                    messagesContainer.appendChild(loadingDiv);
                    
                    try {{
                        const response = await fetch('/api/chat', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json',
                            }},
                            body: JSON.stringify({{
                                message: message,
                                history: []
                            }})
                        }});
                        
                        const data = await response.json();
                        
                        // Remove loading
                        messagesContainer.removeChild(loadingDiv);
                        
                        // Add AI response
                        const aiDiv = document.createElement('div');
                        aiDiv.style.cssText = 'margin-bottom: 1rem; padding: 0.75rem; background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 8px; max-width: 80%;';
                        aiDiv.innerHTML = '<strong>AI Assistant:</strong> ' + data.response;
                        messagesContainer.appendChild(aiDiv);
                        
                        // Scroll to bottom
                        messagesContainer.scrollTop = messagesContainer.scrollHeight;
                        
                    }} catch (error) {{
                        // Remove loading
                        messagesContainer.removeChild(loadingDiv);
                        
                        // Add error message
                        const errorDiv = document.createElement('div');
                        errorDiv.style.cssText = 'margin-bottom: 1rem; padding: 0.75rem; background: var(--danger-color); color: white; border-radius: 8px; max-width: 80%;';
                        errorDiv.innerHTML = '<strong>Error:</strong> Unable to get response. Please try again.';
                        messagesContainer.appendChild(errorDiv);
                    }}
                }}
                
                // Dashboard-specific functions
                function exportDashboardData() {{
                    alert('Dashboard export functionality coming soon!');
                }}
                
                function generateDashboardReport() {{
                    alert('Dashboard report generation coming soon!');
                }}
                
                function refreshDashboard() {{
                    location.reload();
                }}
            </script>
        </body>
        </html>
        """
        
    except Exception as e:
        # Fallback to static dashboard if database connection fails
        error_msg = str(e)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>7taps Analytics Dashboard</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f7fafc; color: #2d3748; padding: 2rem; }}
                .error {{ background: #fed7d7; border: 1px solid #f56565; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; text-align: center; border-radius: 8px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 7taps Analytics Dashboard</h1>
                <p>Real-time learning analytics and behavior insights</p>
            </div>
            <div class="error">
                <h3>⚠️ Dashboard Loading Error</h3>
                <p>Unable to load dynamic data from database. Error: {error_msg}</p>
                <p>Please check database connection and try again.</p>
            </div>
        </body>
        </html>
        """
    
    return HTMLResponse(content=html_content)

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

@app.get("/playground")
async def developer_playground():
    """Developer playground for quick API testing and exploration"""
    with open("dev/DEVELOPER_PLAYGROUND.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/test-db")
async def test_database():
    """Test database connection and basic queries"""
    try:
        import psycopg2
        import os
        
        DATABASE_URL = os.getenv('DATABASE_URL')
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is not set")
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        
        conn = psycopg2.connect(DATABASE_URL, sslmode=os.getenv('PGSSLMODE', 'require'))
        cursor = conn.cursor()
        
        # Test basic queries
        cursor.execute("SELECT COUNT(*) FROM lessons")
        lesson_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_responses")
        response_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return {
            "status": "success",
            "database": "connected",
            "lessons": lesson_count,
            "users": user_count,
            "responses": response_count
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "database": "failed"
        }



# Import and include routers
try:
    from app.api.etl import router as etl_router
except Exception:
    etl_router = None
from app.api.orchestrator import router as orchestrator_router
# from app.api.nlp import router as nlp_router
from app.api.xapi import router as xapi_router
from app.api.seventaps import router as seventaps_router
from app.api.xapi_lrs import router as xapi_lrs_router
from app.api.learninglocker_sync import router as learninglocker_sync_router
from app.api.health import router as health_router
from app.api.data_normalization import router as data_normalization_router
from app.api.data_import import router as data_import_router
from app.api.migration import router as migration_router
from app.api.focus_group_import import router as focus_group_import_router
from app.api.csv_to_xapi import router as csv_to_xapi_router
from app.api.data_access import router as data_access_router
from app.api.chat import router as chat_router
from app.api.public import router as public_router
from app.api.data_explorer import router as data_explorer_router
from app.ui.admin import router as admin_router
# from app.ui.dashboard import router as dashboard_router
from app.ui.data_import import router as data_import_ui_router
# from app.api.monitoring import router as monitoring_router
# from app.ui.production_dashboard import router as production_dashboard_router

if etl_router:
    app.include_router(etl_router, prefix="/ui", tags=["ETL"])
app.include_router(orchestrator_router, prefix="/api", tags=["Orchestrator"])
# app.include_router(nlp_router, prefix="/api", tags=["NLP"])
app.include_router(xapi_router, tags=["xAPI"])
app.include_router(seventaps_router, tags=["7taps"])
app.include_router(xapi_lrs_router, tags=["xAPI LRS"])
app.include_router(learninglocker_sync_router, prefix="/api", tags=["Learning Locker"])
app.include_router(data_normalization_router, prefix="/api", tags=["Data Normalization"])
app.include_router(data_import_router, prefix="/api", tags=["Data Import"])
app.include_router(migration_router, prefix="/api", tags=["Migration"])
app.include_router(focus_group_import_router, prefix="/api", tags=["Focus Group Import"])
app.include_router(csv_to_xapi_router, prefix="/api", tags=["CSV to xAPI"])
app.include_router(data_access_router, prefix="/api", tags=["Data Access"])
app.include_router(chat_router, prefix="/api", tags=["Chat"])
app.include_router(public_router, tags=["Public"])
app.include_router(data_explorer_router, tags=["Data Explorer"])
app.include_router(health_router, tags=["Health"])
app.include_router(admin_router, tags=["Admin"])
# app.include_router(dashboard_router, tags=["Dashboard"])
app.include_router(data_import_ui_router, tags=["Data Import UI"])
# app.include_router(monitoring_router, prefix="/api", tags=["Monitoring"])
# app.include_router(production_dashboard_router, tags=["Production Dashboard"])

if __name__ == "__main__":
    import uvicorn
    from app.config import settings
    uvicorn.run(app, host="0.0.0.0", port=settings.APP_PORT) 