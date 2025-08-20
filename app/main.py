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
            
            /* Multiselect Styles */
            .multiselect-container {
                position: relative;
                width: 100%;
            }
            
            .multiselect-header {
                padding: 0.75rem;
                border: 1px solid var(--border-color);
                border-radius: 8px;
                background: var(--bg-color);
                cursor: pointer;
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 0.9rem;
                transition: all 0.2s;
            }
            
            .multiselect-header:hover {
                border-color: var(--primary-color);
            }
            
            .multiselect-arrow {
                font-size: 0.8rem;
                transition: transform 0.2s;
            }
            
            .multiselect-container.open .multiselect-arrow {
                transform: rotate(180deg);
            }
            
            .multiselect-options {
                position: absolute;
                top: 100%;
                left: 0;
                right: 0;
                background: var(--bg-color);
                border: 1px solid var(--border-color);
                border-top: none;
                border-radius: 0 0 8px 8px;
                max-height: 200px;
                overflow-y: auto;
                z-index: 1000;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            }
            
            .multiselect-option {
                padding: 0.5rem 0.75rem;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 0.5rem;
                transition: background-color 0.2s;
            }
            
            .multiselect-option:hover {
                background: var(--card-bg);
            }
            
            .multiselect-option input[type="checkbox"] {
                margin: 0;
            }
            
            .multiselect-option.selected {
                background: var(--primary-color);
                color: white;
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
                    <label for="lesson-filter">Filter by Lessons</label>
                    <div id="lesson-filter" class="multiselect-container">
                        <div class="multiselect-header" onclick="toggleMultiselect('lesson-filter')">
                            <span id="lesson-filter-text">All Lessons</span>
                            <span class="multiselect-arrow">▼</span>
                        </div>
                        <div id="lesson-filter-options" class="multiselect-options" style="display: none;">
                            <!-- Options will be loaded here -->
                        </div>
                    </div>
                </div>
                
                <div class="control-group">
                    <label for="user-filter">Filter by Users</label>
                    <div id="user-filter" class="multiselect-container">
                        <div class="multiselect-header" onclick="toggleMultiselect('user-filter')">
                            <span id="user-filter-text">All Users</span>
                            <span class="multiselect-arrow">▼</span>
                        </div>
                        <div id="user-filter-options" class="multiselect-options" style="display: none;">
                            <!-- Options will be loaded here -->
                        </div>
                    </div>
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
            // Global variables to store selected values
            let selectedLessonIds = [];
            let selectedUserIds = [];
            
            async function loadData() {
                const selectedTable = document.getElementById('table-select').value;
                const limit = document.getElementById('limit-input').value;
                
                if (!selectedTable) {
                    alert('Please select a table');
                    return;
                }
                
                try {
                    let url = `/api/data-explorer/table/${selectedTable}/filtered?limit=${limit}`;
                    if (selectedLessonIds.length > 0) {
                        url += `&lesson_ids=${selectedLessonIds.join(',')}`;
                    }
                    if (selectedUserIds.length > 0) {
                        url += `&user_ids=${selectedUserIds.join(',')}`;
                    }
                    
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
                    
                    const lessonOptions = document.getElementById('lesson-filter-options');
                    lessonOptions.innerHTML = '';
                    
                    if (data.success && data.lessons) {
                        data.lessons.forEach(lesson => {
                            const option = document.createElement('div');
                            option.className = 'multiselect-option';
                            option.innerHTML = `
                                <input type="checkbox" id="lesson-${lesson.id}" value="${lesson.id}" onchange="toggleLessonSelection(${lesson.id}, '${lesson.name}')">
                                <label for="lesson-${lesson.id}">${lesson.name}</label>
                            `;
                            lessonOptions.appendChild(option);
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
                    
                    const userOptions = document.getElementById('user-filter-options');
                    userOptions.innerHTML = '';
                    
                    if (data.success && data.users) {
                        data.users.forEach(user => {
                            const option = document.createElement('div');
                            option.className = 'multiselect-option';
                            option.innerHTML = `
                                <input type="checkbox" id="user-${user.id}" value="${user.id}" onchange="toggleUserSelection(${user.id}, '${user.email || user.user_id}')">
                                <label for="user-${user.id}">${user.email || user.user_id}</label>
                            `;
                            userOptions.appendChild(option);
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
                selectedLessonIds = [];
                selectedUserIds = [];
                document.getElementById('lesson-filter-text').textContent = 'All Lessons';
                document.getElementById('user-filter-text').textContent = 'All Users';
                document.getElementById('limit-input').value = '50';
                
                // Uncheck all checkboxes
                document.querySelectorAll('#lesson-filter-options input[type="checkbox"]').forEach(cb => cb.checked = false);
                document.querySelectorAll('#user-filter-options input[type="checkbox"]').forEach(cb => cb.checked = false);
            }
            
            function toggleMultiselect(containerId) {
                const container = document.getElementById(containerId);
                const options = document.getElementById(containerId + '-options');
                const isOpen = options.style.display !== 'none';
                
                // Close all other multiselects
                document.querySelectorAll('.multiselect-options').forEach(opt => opt.style.display = 'none');
                document.querySelectorAll('.multiselect-container').forEach(cont => cont.classList.remove('open'));
                
                if (!isOpen) {
                    options.style.display = 'block';
                    container.classList.add('open');
                }
            }
            
            function toggleLessonSelection(lessonId, lessonName) {
                const checkbox = document.getElementById(`lesson-${lessonId}`);
                const textElement = document.getElementById('lesson-filter-text');
                
                if (checkbox.checked) {
                    if (!selectedLessonIds.includes(lessonId)) {
                        selectedLessonIds.push(lessonId);
                    }
                } else {
                    selectedLessonIds = selectedLessonIds.filter(id => id !== lessonId);
                }
                
                updateLessonFilterText();
            }
            
            function toggleUserSelection(userId, userName) {
                const checkbox = document.getElementById(`user-${userId}`);
                const textElement = document.getElementById('user-filter-text');
                
                if (checkbox.checked) {
                    if (!selectedUserIds.includes(userId)) {
                        selectedUserIds.push(userId);
                    }
                } else {
                    selectedUserIds = selectedUserIds.filter(id => id !== userId);
                }
                
                updateUserFilterText();
            }
            
            function updateLessonFilterText() {
                const textElement = document.getElementById('lesson-filter-text');
                if (selectedLessonIds.length === 0) {
                    textElement.textContent = 'All Lessons';
                } else if (selectedLessonIds.length === 1) {
                    const lessonName = document.querySelector(`#lesson-${selectedLessonIds[0]} + label`).textContent;
                    textElement.textContent = lessonName;
                } else {
                    textElement.textContent = `${selectedLessonIds.length} Lessons Selected`;
                }
            }
            
            function updateUserFilterText() {
                const textElement = document.getElementById('user-filter-text');
                if (selectedUserIds.length === 0) {
                    textElement.textContent = 'All Users';
                } else if (selectedUserIds.length === 1) {
                    const userName = document.querySelector(`#user-${selectedUserIds[0]} + label`).textContent;
                    textElement.textContent = userName;
                } else {
                    textElement.textContent = `${selectedUserIds.length} Users Selected`;
                }
            }
            
            // Close multiselect when clicking outside
            document.addEventListener('click', function(event) {
                if (!event.target.closest('.multiselect-container')) {
                    document.querySelectorAll('.multiselect-options').forEach(opt => opt.style.display = 'none');
                    document.querySelectorAll('.multiselect-container').forEach(cont => cont.classList.remove('open'));
                }
            });
            
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
        from datetime import datetime, timedelta
        
        # Database connection
        DATABASE_URL = os.getenv('DATABASE_URL')
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is not set")
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        
        conn = psycopg2.connect(DATABASE_URL, sslmode=os.getenv('PGSSLMODE', 'require'))
        cursor = conn.cursor()
        
        # Get comprehensive metrics
        cursor.execute("SELECT COUNT(DISTINCT id) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT id) FROM user_activities")
        total_activities = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT id) FROM user_responses")
        total_responses = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT id) FROM questions")
        total_questions = cursor.fetchone()[0]
        
        # Get lesson completion data
        cursor.execute("""
            SELECT 
                l.lesson_name,
                COUNT(DISTINCT ua.user_id) as users_started,
                COUNT(DISTINCT ur.user_id) as users_completed,
                ROUND(
                    (COUNT(DISTINCT ur.user_id)::float / NULLIF(COUNT(DISTINCT ua.user_id), 0) * 100)::numeric, 1
                ) as completion_rate
            FROM lessons l
            LEFT JOIN user_activities ua ON l.id = ua.lesson_id
            LEFT JOIN user_responses ur ON l.lesson_number = ur.lesson_number
            GROUP BY l.id, l.lesson_name, l.lesson_number
            ORDER BY l.lesson_number
        """)
        lesson_completion_data = cursor.fetchall()
        
        # Get activity trends over time
        cursor.execute("""
            SELECT 
                DATE(ua.created_at) as activity_date,
                COUNT(*) as activities,
                COUNT(DISTINCT ua.user_id) as active_users
            FROM user_activities ua
            WHERE ua.created_at >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(ua.created_at)
            ORDER BY activity_date
        """)
        activity_trends = cursor.fetchall()
        
        # Get response distribution by type
        cursor.execute("""
            SELECT 
                q.question_type,
                COUNT(ur.id) as response_count
            FROM questions q
            LEFT JOIN user_responses ur ON q.id = ur.question_id
            GROUP BY q.question_type
            ORDER BY response_count DESC
        """)
        response_types = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Prepare data for charts
        lesson_names = [row[0] for row in lesson_completion_data] if lesson_completion_data else ['No Data']
        completion_rates = [row[3] for row in lesson_completion_data] if lesson_completion_data else [0]
        users_started = [row[1] for row in lesson_completion_data] if lesson_completion_data else [0]
        users_completed = [row[2] for row in lesson_completion_data] if lesson_completion_data else [0]
        
        activity_dates = [row[0].strftime('%Y-%m-%d') for row in activity_trends] if activity_trends else []
        activity_counts = [row[1] for row in activity_trends] if activity_trends else []
        active_users = [row[2] for row in activity_trends] if activity_trends else []
        
        response_type_labels = [row[0] for row in response_types] if response_types else []
        response_type_counts = [row[1] for row in response_types] if response_types else []
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Analytics Dashboard</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{ 
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; 
                    background: #f8fafc; 
                    margin: 0; 
                    padding: 0;
                    color: #1e293b;
                }}
                .header {{ 
                    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); 
                    color: white; 
                    padding: 2rem; 
                    text-align: center; 
                    margin-bottom: 2rem; 
                }}
                .header h1 {{
                    font-size: 2.5rem;
                    font-weight: 700;
                    margin: 0 0 0.5rem 0;
                }}
                .header p {{
                    font-size: 1.1rem;
                    opacity: 0.9;
                    margin: 0;
                }}
                .container {{
                    max-width: 1400px;
                    margin: 0 auto;
                    padding: 0 2rem 2rem 2rem;
                }}
                .metrics-grid {{ 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
                    gap: 1.5rem; 
                    margin-bottom: 2rem; 
                }}
                .metric-card {{ 
                    background: white; 
                    padding: 2rem; 
                    border-radius: 12px; 
                    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06); 
                    text-align: center; 
                    transition: all 0.2s ease;
                    border: 1px solid #e2e8f0;
                }}
                .metric-card:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                }}
                .metric-value {{ 
                    font-size: 2.5rem; 
                    font-weight: 700; 
                    color: #6366f1; 
                    margin-bottom: 0.5rem;
                    line-height: 1;
                }}
                .metric-label {{ 
                    color: #64748b; 
                    font-size: 0.9rem;
                    font-weight: 500;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }}
                .charts-grid {{ 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); 
                    gap: 2rem; 
                    margin-bottom: 2rem;
                }}
                .chart-container {{ 
                    background: white; 
                    padding: 1.5rem; 
                    border-radius: 12px; 
                    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
                    border: 1px solid #e2e8f0;
                }}
                .chart-title {{
                    font-size: 1.25rem;
                    font-weight: 600;
                    color: #1e293b;
                    margin-bottom: 1rem;
                    text-align: center;
                }}
                .insights {{
                    background: white;
                    padding: 1.5rem;
                    border-radius: 12px;
                    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
                    border: 1px solid #e2e8f0;
                    margin-bottom: 2rem;
                }}
                .insights h3 {{
                    font-size: 1.25rem;
                    font-weight: 600;
                    color: #1e293b;
                    margin-bottom: 1rem;
                }}
                .insights ul {{
                    list-style: none;
                    padding: 0;
                }}
                .insights li {{
                    padding: 0.75rem 0;
                    border-bottom: 1px solid #e2e8f0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .insights li:last-child {{
                    border-bottom: none;
                }}
                .insight-label {{
                    font-weight: 500;
                    color: #374151;
                }}
                .insight-value {{
                    font-weight: 600;
                    color: #6366f1;
                }}
                .nav-links {{
                    display: flex;
                    justify-content: center;
                    gap: 1rem;
                    margin-top: 2rem;
                    flex-wrap: wrap;
                }}
                .nav-link {{
                    background: #6366f1;
                    color: white;
                    padding: 0.75rem 1.5rem;
                    text-decoration: none;
                    border-radius: 8px;
                    font-weight: 500;
                    transition: all 0.2s ease;
                }}
                .nav-link:hover {{
                    background: #5855eb;
                    transform: translateY(-1px);
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Analytics Dashboard</h1>
                <p>Comprehensive learning analytics and insights</p>
            </div>
            
            <div class="container">
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value">{total_users:,}</div>
                        <div class="metric-label">Total Users</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{total_activities:,}</div>
                        <div class="metric-label">User Activities</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{total_responses:,}</div>
                        <div class="metric-label">Total Responses</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{total_questions:,}</div>
                        <div class="metric-label">Questions</div>
                    </div>
                </div>
                
                <div class="charts-grid">
                    <div class="chart-container">
                        <div class="chart-title">Lesson Completion Rates</div>
                        <div id="completion-chart"></div>
                    </div>
                    <div class="chart-container">
                        <div class="chart-title">Activity Trends (Last 30 Days)</div>
                        <div id="trends-chart"></div>
                    </div>
                </div>
                
                <div class="charts-grid">
                    <div class="chart-container">
                        <div class="chart-title">Response Distribution by Type</div>
                        <div id="response-types-chart"></div>
                    </div>
                    <div class="chart-container">
                        <div class="chart-title">User Engagement Overview</div>
                        <div id="engagement-chart"></div>
                    </div>
                </div>
                
                <div class="insights">
                    <h3>📈 Key Insights</h3>
                    <ul>
                        <li>
                            <span class="insight-label">Average Completion Rate:</span>
                            <span class="insight-value">{sum(completion_rates) / len(completion_rates) if completion_rates else 0:.1f}%</span>
                        </li>
                        <li>
                            <span class="insight-label">Most Active Lesson:</span>
                            <span class="insight-value">{lesson_names[completion_rates.index(max(completion_rates))] if completion_rates else 'N/A'}</span>
                        </li>
                        <li>
                            <span class="insight-label">Total Users Started:</span>
                            <span class="insight-value">{sum(users_started):,}</span>
                        </li>
                        <li>
                            <span class="insight-label">Total Users Completed:</span>
                            <span class="insight-value">{sum(users_completed):,}</span>
                        </li>
                        <li>
                            <span class="insight-label">Response Rate:</span>
                            <span class="insight-value">{(total_responses / total_questions * 100) if total_questions > 0 else 0:.1f}%</span>
                        </li>
                    </ul>
                </div>
                
                <div class="nav-links">
                    <a href="/ui/admin" class="nav-link">🔧 Admin Panel</a>
                    <a href="/explorer" class="nav-link">🔍 Data Explorer</a>
                    <a href="/docs" class="nav-link">📚 API Docs</a>
                    <a href="/health" class="nav-link">💚 Health Check</a>
                </div>
            </div>
            
            <script>
                // Completion Rates Chart
                Plotly.newPlot('completion-chart', [
                    {{
                        type: 'bar',
                        x: {lesson_names},
                        y: {completion_rates},
                        marker: {{
                            color: {completion_rates},
                            colorscale: 'Viridis',
                            showscale: true,
                            colorbar: {{title: 'Completion %'}}
                        }},
                        text: {completion_rates}.map(val => val + '%'),
                        textposition: 'auto',
                        hovertemplate: '<b>%{{x}}</b><br>Completion Rate: %{{y:.1f}}%<br>Users Started: {users_started}<br>Users Completed: {users_completed}<extra></extra>'
                    }}
                ], {{
                    title: 'Lesson Completion Rates',
                    xaxis: {{title: 'Lessons', tickangle: -45}},
                    yaxis: {{title: 'Completion Rate (%)', range: [0, 100]}},
                    height: 400,
                    margin: {{l: 60, r: 60, t: 60, b: 80}}
                }});
                
                // Activity Trends Chart
                Plotly.newPlot('trends-chart', [
                    {{
                        type: 'scatter',
                        x: {activity_dates},
                        y: {activity_counts},
                        mode: 'lines+markers',
                        name: 'Activities',
                        line: {{color: '#6366f1', width: 3}},
                        marker: {{size: 8}}
                    }},
                    {{
                        type: 'scatter',
                        x: {activity_dates},
                        y: {active_users},
                        mode: 'lines+markers',
                        name: 'Active Users',
                        line: {{color: '#8b5cf6', width: 3}},
                        marker: {{size: 8}},
                        yaxis: 'y2'
                    }}
                ], {{
                    title: 'Activity Trends (Last 30 Days)',
                    xaxis: {{title: 'Date'}},
                    yaxis: {{title: 'Activities', side: 'left'}},
                    yaxis2: {{
                        title: 'Active Users',
                        side: 'right',
                        overlaying: 'y'
                    }},
                    height: 400,
                    margin: {{l: 60, r: 60, t: 60, b: 60}},
                    legend: {{x: 0.02, y: 0.98}}
                }});
                
                // Response Types Chart
                Plotly.newPlot('response-types-chart', [
                    {{
                        type: 'pie',
                        labels: {response_type_labels},
                        values: {response_type_counts},
                        hole: 0.4,
                        marker: {{
                            colors: ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981']
                        }}
                    }}
                ], {{
                    title: 'Response Distribution by Type',
                    height: 400,
                    margin: {{l: 60, r: 60, t: 60, b: 60}}
                }});
                
                // Engagement Overview Chart
                Plotly.newPlot('engagement-chart', [
                    {{
                        type: 'funnel',
                        y: {lesson_names},
                        x: {users_started},
                        textinfo: 'value+percent initial',
                        marker: {{
                            color: ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#ef4444', '#06b6d4', '#84cc16', '#f97316', '#a855f7']
                        }}
                    }}
                ], {{
                    title: 'User Engagement Funnel',
                    height: 400,
                    margin: {{l: 60, r: 60, t: 60, b: 60}}
                }});
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
            <title>Analytics Dashboard</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: 'Inter', sans-serif; background: #f8fafc; color: #1e293b; padding: 2rem; }}
                .error {{ background: #fef2f2; border: 1px solid #fecaca; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; }}
                .header {{ background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; padding: 2rem; text-align: center; border-radius: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Analytics Dashboard</h1>
                <p>Comprehensive learning analytics and insights</p>
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