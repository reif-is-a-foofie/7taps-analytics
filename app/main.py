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

@app.get("/explorer", response_class=HTMLResponse)
async def data_explorer():
    """Serve the data explorer interface"""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Data Explorer - 7taps Analytics</title>
        <style>
            :root {
                --primary-color: #6366f1;
                --bg-color: #ffffff;
                --card-bg: #f8fafc;
                --text-primary: #1e293b;
                --text-secondary: #64748b;
                --border-color: #e2e8f0;
                --card-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
                --success-color: #10b981;
                --danger-color: #ef4444;
            }
            
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                background: var(--bg-color);
                color: var(--text-primary);
                line-height: 1.6;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 2rem;
            }
            
            .header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 2rem;
                padding-bottom: 1rem;
                border-bottom: 1px solid var(--border-color);
            }
            
            .header h1 {
                color: var(--primary-color);
                font-size: 2rem;
                font-weight: 600;
            }
            
            .back-link {
                color: var(--primary-color);
                text-decoration: none;
                font-weight: 500;
                padding: 0.5rem 1rem;
                border: 1px solid var(--primary-color);
                border-radius: 8px;
                transition: all 0.2s;
            }
            
            .back-link:hover {
                background: var(--primary-color);
                color: white;
            }
            
            .controls {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1rem;
                margin-bottom: 2rem;
            }
            
            .control-group {
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
            }
            
            .control-group label {
                font-weight: 500;
                color: var(--text-primary);
            }
            
            .control-group select,
            .control-group input {
                padding: 0.75rem;
                border: 1px solid var(--border-color);
                border-radius: 8px;
                font-size: 0.9rem;
                background: var(--bg-color);
            }
            
            .btn {
                padding: 0.75rem 1.5rem;
                border: none;
                border-radius: 8px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s;
                font-size: 0.9rem;
            }
            
            .btn-primary {
                background: var(--primary-color);
                color: white;
            }
            
            .btn-primary:hover {
                background: #5855eb;
            }
            
            .btn-secondary {
                background: var(--card-bg);
                color: var(--text-primary);
                border: 1px solid var(--border-color);
            }
            
            .btn-secondary:hover {
                background: #e2e8f0;
            }
            
            .data-table {
                background: var(--bg-color);
                border-radius: 12px;
                box-shadow: var(--card-shadow);
                overflow: hidden;
                margin-bottom: 2rem;
            }
            
            .table-header {
                background: var(--card-bg);
                padding: 1rem;
                border-bottom: 1px solid var(--border-color);
            }
            
            .table-header h3 {
                color: var(--text-primary);
                font-size: 1.1rem;
                font-weight: 600;
            }
            
            .table-container {
                overflow-x: auto;
            }
            
            table {
                width: 100%;
                border-collapse: collapse;
            }
            
            th, td {
                padding: 0.75rem 1rem;
                text-align: left;
                border-bottom: 1px solid var(--border-color);
            }
            
            th {
                background: var(--card-bg);
                font-weight: 600;
                color: var(--text-primary);
                font-size: 0.9rem;
            }
            
            td {
                color: var(--text-secondary);
                font-size: 0.9rem;
            }
            
            tr:hover {
                background: #f1f5f9;
            }
            
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1rem;
                margin-bottom: 2rem;
            }
            
            .stat-card {
                background: var(--bg-color);
                padding: 1.5rem;
                border-radius: 12px;
                box-shadow: var(--card-shadow);
                text-align: center;
            }
            
            .stat-number {
                font-size: 2rem;
                font-weight: 700;
                color: var(--primary-color);
                margin-bottom: 0.5rem;
            }
            
            .stat-label {
                color: var(--text-secondary);
                font-size: 0.9rem;
                font-weight: 500;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Data Explorer</h1>
                <a href="/" class="back-link">← Back to Dashboard</a>
            </div>
            
            <div class="controls">
                <div class="control-group">
                    <label for="table-select">Select Table</label>
                    <select id="table-select">
                        <option value="users">Users</option>
                        <option value="lessons">Lessons</option>
                        <option value="user_responses">User Responses</option>
                        <option value="user_activities">User Activities</option>
                        <option value="statements_new">xAPI Statements</option>
                    </select>
                </div>
                
                <div class="control-group">
                    <label for="lesson-filter">Filter by Lesson</label>
                    <select id="lesson-filter">
                        <option value="">All Lessons</option>
                    </select>
                </div>
                
                <div class="control-group">
                    <label for="user-filter">Filter by User</label>
                    <select id="user-filter">
                        <option value="">All Users</option>
                    </select>
                </div>
                
                <div class="control-group">
                    <label for="limit-input">Limit</label>
                    <input type="number" id="limit-input" value="50" min="1" max="1000">
                </div>
                
                <div class="control-group">
                    <button class="btn btn-primary" onclick="loadData()">Load Data</button>
                    <button class="btn btn-secondary" onclick="clearFilters()">Clear Filters</button>
                </div>
            </div>
            
            <div class="stats" id="stats">
                <!-- Stats will be loaded here -->
            </div>
            
            <div class="data-table">
                <div class="table-header">
                    <h3 id="table-title">Select a table to view data</h3>
                </div>
                <div class="table-container">
                    <div id="data-table">
                        <p style="text-align: center; color: var(--text-secondary); padding: 2rem;">
                            Select a table and click "Load Data" to view records
                        </p>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            async function loadData() {
                const selectedTable = document.getElementById('table-select').value;
                const lessonFilter = document.getElementById('lesson-filter').value;
                const userFilter = document.getElementById('user-filter').value;
                const limit = document.getElementById('limit-input').value;
                
                if (!selectedTable) {
                    alert('Please select a table');
                    return;
                }
                
                try {
                    let url = `/api/data-explorer/table/${selectedTable}?limit=${limit}`;
                    if (lessonFilter) url += `&lesson_number=${lessonFilter}`;
                    if (userFilter) url += `&user_id=${userFilter}`;
                    
                    const response = await fetch(url);
                    const data = await response.json();
                    
                    if (data.success) {
                        renderDataTable(data.data, data.columns);
                        updateTableStats(data.data);
                        document.getElementById('table-title').textContent = `${selectedTable.replace('_', ' ').toUpperCase()} (${data.data.length} records)`;
                    } else {
                        document.getElementById('data-table').innerHTML = `<p style="text-align: center; color: var(--danger-color); padding: 2rem;">Error loading data: ${data.error}</p>`;
                    }
                } catch (error) {
                    document.getElementById('data-table').innerHTML = `<p style="text-align: center; color: var(--danger-color); padding: 2rem;">Error loading data: ${error.message}</p>`;
                }
            }
            
            async function loadLessonOptions() {
                try {
                    const response = await fetch('/api/data-explorer/lessons');
                    const data = await response.json();
                    
                    const lessonFilter = document.getElementById('lesson-filter');
                    lessonFilter.innerHTML = '<option value="">All Lessons</option>';
                    
                    if (data.success && data.lessons) {
                        data.lessons.forEach(lesson => {
                            const option = document.createElement('option');
                            option.value = lesson.lesson_number || lesson.id;
                            option.textContent = lesson.name;
                            lessonFilter.appendChild(option);
                        });
                    }
                } catch (error) {
                    console.error('Error loading lesson options:', error);
                }
            }
            
            async function loadUserOptions() {
                try {
                    const response = await fetch('/api/data-explorer/users');
                    const data = await response.json();
                    
                    const userFilter = document.getElementById('user-filter');
                    userFilter.innerHTML = '<option value="">All Users</option>';
                    
                    if (data.success && data.users) {
                        data.users.forEach(user => {
                            const option = document.createElement('option');
                            option.value = user.id;
                            option.textContent = user.email || user.id;
                            userFilter.appendChild(option);
                        });
                    }
                } catch (error) {
                    console.error('Error loading user options:', error);
                }
            }
            
            function renderDataTable(data, columns) {
                if (!data || data.length === 0) {
                    document.getElementById('data-table').innerHTML = '<p style="text-align: center; color: var(--text-secondary); padding: 2rem;">No data available</p>';
                    return;
                }
                
                let tableHTML = '<table><thead><tr>';
                columns.forEach(column => {
                    tableHTML += `<th>${column}</th>`;
                });
                tableHTML += '</tr></thead><tbody>';
                
                data.forEach(row => {
                    tableHTML += '<tr>';
                    columns.forEach(column => {
                        const value = row[column] !== null ? row[column] : '';
                        tableHTML += `<td>${value}</td>`;
                    });
                    tableHTML += '</tr>';
                });
                
                tableHTML += '</tbody></table>';
                document.getElementById('data-table').innerHTML = tableHTML;
            }
            
            function updateTableStats(data) {
                const statsContainer = document.getElementById('stats');
                if (!data || data.length === 0) {
                    statsContainer.innerHTML = '';
                    return;
                }
                
                const columns = Object.keys(data[0]);
                const statsHTML = columns.map(column => {
                    const values = data.map(row => row[column]).filter(val => val !== null && val !== '');
                    const uniqueCount = new Set(values).size;
                    return `
                        <div class="stat-card">
                            <div class="stat-number">${uniqueCount}</div>
                            <div class="stat-label">Unique ${column}</div>
                        </div>
                    `;
                }).join('');
                
                statsContainer.innerHTML = statsHTML;
            }
            
            function clearFilters() {
                document.getElementById('lesson-filter').value = '';
                document.getElementById('user-filter').value = '';
                document.getElementById('limit-input').value = '50';
            }
            
            // Load options on page load
            document.addEventListener('DOMContentLoaded', function() {
                loadLessonOptions();
                loadUserOptions();
            });
        </script>
    </body>
    </html>
    """)

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the analytics dashboard with dynamic data"""
    try:
        import psycopg2
        import os
        
        # Database connection
        DATABASE_URL = os.getenv('DATABASE_URL')
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is not set")
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        
        conn = psycopg2.connect(DATABASE_URL, sslmode=os.getenv('PGSSLMODE', 'require'))
        cursor = conn.cursor()
        
        # Get metrics
        cursor.execute("SELECT COUNT(DISTINCT id) FROM users")
        total_users = cursor.fetchone()[0]
        
        # Get lesson data
        cursor.execute("""
            SELECT l.lesson_name, COUNT(DISTINCT ua.user_id) as response_count
            FROM lessons l
            LEFT JOIN user_activities ua ON l.id = ua.lesson_id
            GROUP BY l.id, l.lesson_name, l.lesson_number
            ORDER BY l.lesson_number
        """)
        lesson_data = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        lesson_names = [row[0] for row in lesson_data] if lesson_data else ['No Data']
        lesson_counts = [row[1] for row in lesson_data] if lesson_data else [0]
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>7taps Analytics Dashboard</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{ 
                    font-family: 'Inter', sans-serif; 
                    background: #f8f9fa; 
                    margin: 0; 
                    padding: 20px; 
                }}
                .header {{ 
                    background: linear-gradient(135deg, #6A1B9A 0%, #8E24AA 100%); 
                    color: white; 
                    padding: 2rem; 
                    text-align: center; 
                    border-radius: 12px; 
                    margin-bottom: 2rem; 
                }}
                .metrics-grid {{ 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                    gap: 1rem; 
                    margin-bottom: 2rem; 
                }}
                .metric-card {{ 
                    background: white; 
                    padding: 1.5rem; 
                    border-radius: 8px; 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
                    text-align: center; 
                    position: relative;
                    cursor: help;
                }}
                .metric-card:hover {{
                    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
                    transform: translateY(-2px);
                }}
                .metric-tooltip {{
                    position: absolute;
                    bottom: -40px;
                    left: 50%;
                    transform: translateX(-50%);
                    background: #2D3748;
                    color: white;
                    padding: 0.5rem 0.75rem;
                    border-radius: 6px;
                    font-size: 0.8rem;
                    white-space: nowrap;
                    opacity: 0;
                    visibility: hidden;
                    transition: all 0.2s ease;
                    z-index: 1000;
                }}
                .metric-card:hover .metric-tooltip {{
                    opacity: 1;
                    visibility: visible;
                }}
                .metric-value {{ 
                    font-size: 2rem; 
                    font-weight: bold; 
                    color: #6A1B9A; 
                }}
                .metric-label {{ 
                    color: #666; 
                    margin-top: 0.5rem; 
                }}
                .charts-grid {{ 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); 
                    gap: 1rem; 
                }}
                .chart-container {{ 
                    background: white; 
                    padding: 1.5rem; 
                    border-radius: 8px; 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
                }}
                .sidebar {{ 
                    position: fixed; 
                    left: 0; 
                    top: 0; 
                    width: 250px; 
                    height: 100vh; 
                    background: white; 
                    border-right: 1px solid #eee; 
                    padding: 1rem; 
                }}
                .main-content {{ 
                    margin-left: 250px; 
                    padding: 1rem; 
                }}
                .sidebar a {{ 
                    display: block; 
                    padding: 0.75rem; 
                    color: #333; 
                    text-decoration: none; 
                    border-radius: 6px; 
                    margin-bottom: 0.5rem; 
                }}
                .sidebar a:hover {{ 
                    background: #f0f0f0; 
                }}
                
                /* Data Explorer Styles */
                .explorer-controls {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 1rem;
                    margin-bottom: 1rem;
                }}
                .control-group {{
                    display: flex;
                    flex-direction: column;
                    gap: 0.5rem;
                }}
                .control-group label {{
                    font-weight: 500;
                    color: #333;
                    font-size: 0.9rem;
                }}
                .control-group select,
                .control-group input {{
                    padding: 0.75rem;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    font-size: 0.9rem;
                }}
                
                /* Multi-select styles */
                .multiselect-container {{
                    position: relative;
                    display: inline-block;
                    width: 100%;
                }}
                .multiselect-dropdown {{
                    position: absolute;
                    top: 100%;
                    left: 0;
                    right: 0;
                    background: white;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    max-height: 200px;
                    overflow-y: auto;
                    z-index: 1000;
                    display: none;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
                .multiselect-dropdown.show {{
                    display: block;
                }}
                .multiselect-option {{
                    padding: 0.5rem 0.75rem;
                    cursor: pointer;
                    border-bottom: 1px solid #f0f0f0;
                }}
                .multiselect-option:hover {{
                    background: #f8f9fa;
                }}
                .multiselect-option.selected {{
                    background: #6A1B9A;
                    color: white;
                }}
                .multiselect-display {{
                    padding: 0.75rem;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    background: white;
                    cursor: pointer;
                    min-height: 42px;
                    display: flex;
                    flex-wrap: wrap;
                    gap: 0.25rem;
                    align-items: center;
                }}
                .multiselect-tag {{
                    background: #6A1B9A;
                    color: white;
                    padding: 0.25rem 0.5rem;
                    border-radius: 4px;
                    font-size: 0.8rem;
                    display: flex;
                    align-items: center;
                    gap: 0.25rem;
                }}
                .multiselect-tag .remove {{
                    cursor: pointer;
                    font-weight: bold;
                }}
                .multiselect-placeholder {{
                    color: #999;
                }}
            </style>
        </head>
        <body>
                            <div class="sidebar">
                    <h3>Navigation</h3>
                    <a href="/">Dashboard</a>
                    <a href="/explorer">Data Explorer</a>
                    <a href="/chat">Chat with 7</a>
                    <a href="/docs" target="_blank">API Docs</a>
                </div>
            
            <div class="main-content">
                <div class="header">
                    <h1>7taps Analytics Dashboard</h1>
                    <p>Learning Analytics and Insights</p>
                </div>
                
                <div class="metrics-grid">
                    <div class="metric-card" title="Total unique users who have interacted with any lesson content">
                        <div class="metric-value" id="total-participants">{total_users}</div>
                        <div class="metric-label">Total Learners</div>
                        <div class="metric-tooltip">📊 Calculated from unique user IDs in user_activities table</div>
                    </div>
                    <div class="metric-card" title="Percentage of learners who completed the final question of at least one lesson">
                        <div class="metric-value" id="completion-rate">{round((sum(lesson_counts) / (len(lesson_names) * total_users)) * 100, 1) if total_users and lesson_counts and lesson_names else 0}%</div>
                        <div class="metric-label">Completion Rate</div>
                        <div class="metric-tooltip">✅ Based on completion of last question in each lesson</div>
                    </div>
                    <div class="metric-card" title="Average number of unique users engaged per lesson">
                        <div class="metric-value" id="avg-score">{round(sum(lesson_counts) / len(lesson_counts), 1) if lesson_counts and len(lesson_counts) > 0 else 0}</div>
                        <div class="metric-label">Avg Engagement</div>
                        <div class="metric-tooltip">📈 Average unique users per lesson across all {len(lesson_names)} lessons</div>
                    </div>
                    <div class="metric-card" title="Total number of lessons available in the course">
                        <div class="metric-value" id="nps-score">{len(lesson_names)}</div>
                        <div class="metric-label">Total Lessons</div>
                        <div class="metric-tooltip">📚 Total lessons in the course curriculum</div>
                    </div>
                </div>
                
                <div class="charts-grid">
                    <div class="chart-container">
                        <h3>Lesson Completion Funnel</h3>
                        <div id="completion-funnel-chart"></div>
                    </div>
                    <div class="chart-container">
                        <h3>Engagement Analysis</h3>
                        <div id="knowledge-lift-chart"></div>
                    </div>
                </div>
                
                <!-- Data Explorer Section -->
                <div class="chart-container" style="margin-top: 2rem;">
                    <h3>Data Explorer</h3>
                    <div class="explorer-controls">
                        <div class="control-group">
                            <label for="table-select">Select Table:</label>
                            <select id="table-select">
                                <option value="users">Users</option>
                                <option value="lessons">Lessons</option>
                                <option value="user_responses">User Responses</option>
                                <option value="user_activities">User Activities</option>
                                <option value="statements_new">xAPI Statements</option>
                            </select>
                        </div>
                        
                        <div class="control-group">
                            <label>Filter by Lesson:</label>
                            <div class="multiselect-container">
                                <div class="multiselect-display" onclick="toggleDropdown('lesson')" id="lesson-display">
                                    <span class="multiselect-placeholder">Select lessons...</span>
                                </div>
                                <div class="multiselect-dropdown" id="lesson-dropdown">
                                    <!-- Options will be loaded dynamically -->
                                </div>
                            </div>
                        </div>
                        
                        <div class="control-group">
                            <label>Filter by User:</label>
                            <div class="multiselect-container">
                                <div class="multiselect-display" onclick="toggleDropdown('user')" id="user-display">
                                    <span class="multiselect-placeholder">Select users...</span>
                                </div>
                                <div class="multiselect-dropdown" id="user-dropdown">
                                    <!-- Options will be loaded dynamically -->
                                </div>
                            </div>
                        </div>
                        
                        <div class="control-group">
                            <label for="limit-input">Limit:</label>
                            <input type="number" id="limit-input" value="50" min="1" max="1000">
                        </div>
                        
                        <div class="control-group">
                            <button onclick="loadData()" style="margin-top: 1.5rem; padding: 0.75rem 1.5rem; background: #6A1B9A; color: white; border: none; border-radius: 8px; cursor: pointer;">Load Data</button>
                            <button onclick="clearFilters()" style="margin-top: 0.5rem; padding: 0.75rem 1.5rem; background: #666; color: white; border: none; border-radius: 8px; cursor: pointer;">Clear Filters</button>
                        </div>
                    </div>
                    
                    <div class="stats" id="stats" style="margin: 1rem 0; padding: 1rem; background: #f8f9fa; border-radius: 6px; display: none;">
                        <!-- Stats will be loaded here -->
                    </div>
                    
                    <div id="data-table" style="margin-top: 1rem; overflow-x: auto;"></div>
                </div>
            </div>
            
            <script>
                const lessonNames = {lesson_names};
                const lessonCounts = {lesson_counts};
                
                // Multi-select state
                let selectedLessons = [];
                let selectedUsers = [];
                
                // Completion funnel chart
                Plotly.newPlot('completion-funnel-chart', [{{
                    type: 'funnel',
                    y: lessonNames,
                    x: lessonCounts,
                    textinfo: 'value+percent initial',
                    marker: {{color: '#6A1B9A'}}
                }}], {{
                    title: 'Lesson Completion Funnel',
                    height: 300
                }});
                
                // Engagement analysis chart
                const avgEngagement = Math.round(lessonCounts.reduce((a, b) => a + b, 0) / lessonCounts.length);
                const maxEngagement = Math.max(...lessonCounts);
                
                Plotly.newPlot('knowledge-lift-chart', [{{
                    type: 'bar',
                    x: ['Average Engagement', 'Peak Engagement'],
                    y: [avgEngagement, maxEngagement],
                    marker: {{color: ['#ED8936', '#48BB78']}}
                }}], {{
                    title: 'Engagement Analysis',
                    height: 300,
                    yaxis: {{title: 'Number of Participants'}}
                }});
                
                // Initialize Data Explorer
                document.addEventListener('DOMContentLoaded', function() {{
                    loadLessonOptions();
                    loadUserOptions();
                }});
                
                // Multi-select functions
                function toggleDropdown(type) {{
                    const dropdown = document.getElementById(type + '-dropdown');
                    const isVisible = dropdown.classList.contains('show');
                    
                    // Close all dropdowns
                    document.querySelectorAll('.multiselect-dropdown').forEach(d => d.classList.remove('show'));
                    
                    // Toggle current dropdown
                    if (!isVisible) {{
                        dropdown.classList.add('show');
                    }}
                }}
                
                function selectOption(type, value, label) {{
                    const selected = type === 'lesson' ? selectedLessons : selectedUsers;
                    const display = document.getElementById(type + '-display');
                    
                    if (!selected.find(item => item.value === value)) {{
                        selected.push({{value, label}});
                        updateDisplay(type);
                    }}
                    
                    // Don't close dropdown for multi-select
                }}
                
                function removeSelection(type, value) {{
                    const selected = type === 'lesson' ? selectedLessons : selectedUsers;
                    const index = selected.findIndex(item => item.value === value);
                    
                    if (index > -1) {{
                        selected.splice(index, 1);
                        updateDisplay(type);
                    }}
                }}
                
                function updateDisplay(type) {{
                    const selected = type === 'lesson' ? selectedLessons : selectedUsers;
                    const display = document.getElementById(type + '-display');
                    
                    if (selected.length === 0) {{
                        display.innerHTML = '<span class="multiselect-placeholder">Select ' + type + 's...</span>';
                    }} else {{
                        display.innerHTML = selected.map(item => 
                            '<span class="multiselect-tag">' + item.label + 
                            '<span class="remove" onclick="removeSelection(\'' + type + '\', \'' + item.value + '\')">&times;</span></span>'
                        ).join('');
                    }}
                }}
                
                // Close dropdowns when clicking outside
                document.addEventListener('click', function(e) {{
                    if (!e.target.closest('.multiselect-container')) {{
                        document.querySelectorAll('.multiselect-dropdown').forEach(d => d.classList.remove('show'));
                    }}
                }});
                
                // Data loading functions
                async function loadData() {{
                    const selectedTable = document.getElementById('table-select').value;
                    const limit = document.getElementById('limit-input').value;
                    
                    if (!selectedTable) {{
                        alert('Please select a table');
                        return;
                    }}
                    
                    try {{
                        let url = `/api/data-explorer/table/${{selectedTable}}?limit=${{limit}}`;
                        
                        // Add filters
                        if (selectedLessons.length > 0) {{
                            const lessonIds = selectedLessons.map(l => l.value).join(',');
                            url += `&lesson_id=${{lessonIds}}`;
                        }}
                        
                        if (selectedUsers.length > 0) {{
                            const userIds = selectedUsers.map(u => u.value).join(',');
                            url += `&user_id=${{userIds}}`;
                        }}
                        
                        const response = await fetch(url);
                        const data = await response.json();
                        
                        if (data.success) {{
                            renderDataTable(data.data, data.columns);
                            updateTableStats(data.data);
                            document.getElementById('stats').style.display = 'block';
                        }} else {{
                            alert('Error loading data: ' + (data.error || 'Unknown error'));
                        }}
                    }} catch (error) {{
                        console.error('Error:', error);
                        alert('Error loading data');
                    }}
                }}
                
                async function loadLessonOptions() {{
                    try {{
                        const response = await fetch('/api/data-explorer/lessons');
                        const data = await response.json();
                        
                        const dropdown = document.getElementById('lesson-dropdown');
                        dropdown.innerHTML = '';
                        
                        if (data.success && data.lessons) {{
                            data.lessons.forEach(lesson => {{
                                const option = document.createElement('div');
                                option.className = 'multiselect-option';
                                option.textContent = lesson.name;
                                option.onclick = () => selectOption('lesson', lesson.lesson_number || lesson.id, lesson.name);
                                dropdown.appendChild(option);
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
                        
                        const dropdown = document.getElementById('user-dropdown');
                        dropdown.innerHTML = '';
                        
                        if (data.success && data.users) {{
                            data.users.forEach(user => {{
                                const option = document.createElement('div');
                                option.className = 'multiselect-option';
                                option.textContent = user.email || user.id;
                                option.onclick = () => selectOption('user', user.id, user.email || user.id);
                                dropdown.appendChild(option);
                            }});
                        }}
                    }} catch (error) {{
                        console.error('Error loading user options:', error);
                    }}
                }}
                
                function renderDataTable(data, columns) {{
                    const container = document.getElementById('data-table');
                    
                    if (!data || data.length === 0) {{
                        container.innerHTML = '<p style="text-align: center; color: #666; padding: 2rem;">No data available</p>';
                        return;
                    }}
                    
                    let tableHTML = '<table style="width: 100%; border-collapse: collapse; margin-top: 1rem;">';
                    tableHTML += '<thead><tr>';
                    
                    columns.forEach(column => {{
                        tableHTML += `<th style="border: 1px solid #ddd; padding: 0.75rem; background: #f8f9fa; text-align: left;">${{column}}</th>`;
                    }});
                    tableHTML += '</tr></thead><tbody>';
                    
                    data.forEach(row => {{
                        tableHTML += '<tr>';
                        columns.forEach(column => {{
                            const value = row[column];
                            const displayValue = typeof value === 'object' ? JSON.stringify(value) : (value || '');
                            tableHTML += `<td style="border: 1px solid #ddd; padding: 0.5rem; font-size: 0.9rem;">${{displayValue}}</td>`;
                        }});
                        tableHTML += '</tr>';
                    }});
                    
                    tableHTML += '</tbody></table>';
                    container.innerHTML = tableHTML;
                }}
                
                function updateTableStats(data) {{
                    const statsContainer = document.getElementById('stats');
                    
                    if (!data || data.length === 0) {{
                        statsContainer.innerHTML = '';
                        return;
                    }}
                    
                    const stats = {{
                        totalRecords: data.length,
                        columns: Object.keys(data[0] || {{}}).length
                    }};
                    
                    statsContainer.innerHTML = `
                        <strong>Stats:</strong> ${{stats.totalRecords}} records, ${{stats.columns}} columns
                    `;
                }}
                
                function clearFilters() {{
                    selectedLessons = [];
                    selectedUsers = [];
                    updateDisplay('lesson');
                    updateDisplay('user');
                    document.getElementById('limit-input').value = '50';
                    document.getElementById('stats').style.display = 'none';
                    document.getElementById('data-table').innerHTML = '<p style="text-align: center; color: #666; padding: 2rem;">Select a table and click "Load Data" to view records</p>';
                }}
            </script>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head><title>Error</title></head>
        <body>
            <h1>Dashboard Error</h1>
            <p>Error: {str(e)}</p>
        </body>
        </html>
        """)

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

# Internal/Admin routers - hidden from public API
# app.include_router(etl_router, prefix="/ui", tags=["ETL"])
# app.include_router(orchestrator_router, prefix="/api", tags=["Orchestrator"])
# app.include_router(nlp_router, prefix="/api", tags=["NLP"])
# app.include_router(xapi_router, tags=["xAPI"])
# app.include_router(seventaps_router, tags=["7taps"])
# app.include_router(xapi_lrs_router, tags=["xAPI LRS"])
# app.include_router(learninglocker_sync_router, prefix="/api", tags=["Learning Locker"])
# app.include_router(data_normalization_router, prefix="/api", tags=["Data Normalization"])
# app.include_router(data_import_router, prefix="/api", tags=["Data Import"])
# app.include_router(migration_router, prefix="/api", tags=["Migration"])
# app.include_router(focus_group_import_router, prefix="/api", tags=["Focus Group Import"])
# app.include_router(csv_to_xapi_router, prefix="/api", tags=["CSV to xAPI"])
app.include_router(data_access_router, prefix="/api", tags=["Data Access"])
app.include_router(chat_router, prefix="/api", tags=["Chat"])
# app.include_router(public_router, tags=["Public"])
# app.include_router(data_import_ui_router, tags=["Data Import UI"])
# app.include_router(admin_router, tags=["Admin"])
# app.include_router(dashboard_router, tags=["Dashboard"])
# app.include_router(monitoring_router, prefix="/api", tags=["Monitoring"])
# app.include_router(production_dashboard_router, tags=["Production Dashboard"])

# Public API - only essential data extraction endpoints
app.include_router(data_explorer_router, tags=["Data Explorer"])
app.include_router(health_router, tags=["Health"])

if __name__ == "__main__":
    import uvicorn
    from app.config import settings
    uvicorn.run(app, host="0.0.0.0", port=settings.APP_PORT) 