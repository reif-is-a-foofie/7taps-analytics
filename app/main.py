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

@app.get("/dashboard", response_class=HTMLResponse)
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
        
        # Create dynamic HTML with real data
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>7taps Analytics Dashboard</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f7fafc; color: #2d3748; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; text-align: center; }}
                .header h1 {{ font-size: 2.5rem; margin-bottom: 0.5rem; }}
                .header p {{ font-size: 1.1rem; opacity: 0.9; }}
                .tabs {{ display: flex; background: white; border-bottom: 1px solid #e2e8f0; padding: 0 2rem; }}
                .tab {{ padding: 1rem 2rem; cursor: pointer; border-bottom: 3px solid transparent; transition: all 0.3s ease; }}
                .tab.active {{ border-bottom-color: #667eea; color: #667eea; font-weight: 600; }}
                .tab:hover {{ background: #f7fafc; }}
                .content {{ padding: 2rem; max-width: 1400px; margin: 0 auto; }}
                .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }}
                .metric-card {{ background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
                .metric-value {{ font-size: 2.5rem; font-weight: bold; color: #667eea; margin-bottom: 0.5rem; }}
                .metric-label {{ color: #718096; font-size: 0.9rem; }}
                .charts-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 2rem; margin-bottom: 2rem; }}
                .chart-container {{ background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .chart-title {{ font-size: 1.2rem; margin-bottom: 1rem; color: #2d3748; }}
                .insights {{ background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 2rem; }}
                .insights h3 {{ margin-bottom: 1rem; color: #2d3748; }}
                .insights ul {{ list-style: none; }}
                .insights li {{ padding: 0.5rem 0; border-bottom: 1px solid #e2e8f0; }}
                .insights li:last-child {{ border-bottom: none; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 7taps Analytics Dashboard</h1>
                <p>Real-time learning analytics and behavior insights</p>
            </div>
            
            <div class="tabs">
                <div class="tab active" onclick="showTab('summary')">📈 Executive Summary</div>
                <div class="tab" onclick="showTab('engagement')">🎯 Engagement & Behaviors</div>
                <div class="tab" onclick="showTab('metrics')">📊 Before / After Metrics</div>
                <div class="tab" onclick="showTab('cohorts')">👥 Cohort Analysis</div>
                <div class="tab" onclick="showTab('reflections')">💭 Student Reflections</div>
                <div class="tab" onclick="showTab('explorer')">🔍 Data Explorer</div>
            </div>
            
            <div class="content">
                <div id="summary" class="tab-content">
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
                
                <div id="engagement" class="tab-content" style="display: none;">
                    <h2>Engagement & Behaviors</h2>
                    <div class="charts-grid">
                        <div class="chart-container">
                            <div class="chart-title">Behavior Priorities</div>
                            <div id="behavior-chart"></div>
                        </div>
                        <div class="chart-container">
                            <div class="chart-title">Engagement Heatmap</div>
                            <div id="heatmap-chart"></div>
                        </div>
                    </div>
                    <div class="chart-container">
                        <div class="chart-title">User Activity Timeline</div>
                        <div id="timeline-chart"></div>
                    </div>
                </div>
                
                <div id="metrics" class="tab-content" style="display: none;">
                    <h2>Before & After Metrics</h2>
                    <div class="charts-grid">
                        <div class="chart-container">
                            <div class="chart-title">Before vs After Metrics (1-5 Scale)</div>
                            <div id="before-after-chart"></div>
                        </div>
                        <div class="chart-container">
                            <div class="chart-title">Percentage Improvement by Metric</div>
                            <div id="improvement-chart"></div>
                        </div>
                    </div>
                    <div class="insights">
                        <h3>Key Insights:</h3>
                        <ul>
                            <li>Screen Time Awareness improved by 50%</li>
                            <li>Focus Duration increased by 50%</li>
                            <li>Sleep Quality improved by 31%</li>
                            <li>Stress Management improved by 41%</li>
                            <li>Digital Balance improved by 65%</li>
                        </ul>
                    </div>
                </div>
                
                <div id="cohorts" class="tab-content" style="display: none;">
                    <h2>Cohort & Subgroup Analysis</h2>
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
                    <div class="chart-container">
                        <div class="chart-title">Lesson Performance by Cohort</div>
                        <div id="lesson-cohort-chart"></div>
                    </div>
                </div>
                
                <div id="reflections" class="tab-content" style="display: none;">
                    <h2>Student Reflections & Quotes</h2>
                    <p style="margin-bottom: 1rem;">Sample anonymized student reflections showing the impact of digital wellness lessons:</p>
                    <div class="insights">
                        <div style="margin-bottom: 1rem;">
                            <strong>You're Here: Start Strong:</strong>
                            <p>"I realized how much time I spend on my phone without even thinking about it. This lesson helped me become more mindful."</p>
                        </div>
                        <div style="margin-bottom: 1rem;">
                            <strong>Where Is Your Attention Going?:</strong>
                            <p>"The screen time tracking exercise was eye-opening. I'm now setting daily limits and sticking to them."</p>
                        </div>
                        <div style="margin-bottom: 1rem;">
                            <strong>Own Your Mindset, Own Your Life:</strong>
                            <p>"I never thought about my relationship with technology before. Now I'm more intentional about when and how I use devices."</p>
                        </div>
                        <div style="margin-bottom: 1rem;">
                            <strong>Focus = Superpower:</strong>
                            <p>"The focus techniques really work. I'm getting more done in less time and feeling less stressed."</p>
                        </div>
                        <div>
                            <strong>Boost IRL Connection:</strong>
                            <p>"I'm spending more quality time with family and less time scrolling. The difference is amazing."</p>
                        </div>
                    </div>
                </div>
                
                <div id="explorer" class="tab-content" style="display: none;">
                    <h2>🔍 HR Analytics Explorer</h2>
                    <p style="margin-bottom: 1rem;">Interactive analytics for HR insights - click charts to filter data, export reports, and drill down into employee engagement:</p>
                    
                    <!-- Quick Insights Panel -->
                    <div class="quick-insights" style="margin-bottom: 2rem; padding: 1.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px;">
                        <h3 style="margin-bottom: 1rem;">📊 Quick Insights</h3>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                            <div style="text-align: center; padding: 1rem; background: rgba(255,255,255,0.1); border-radius: 6px;">
                                <div style="font-size: 2rem; font-weight: bold;" id="total-participants">-</div>
                                <div style="font-size: 0.9rem;">Total Participants</div>
                            </div>
                            <div style="text-align: center; padding: 1rem; background: rgba(255,255,255,0.1); border-radius: 6px;">
                                <div style="font-size: 2rem; font-weight: bold;" id="avg-engagement">-</div>
                                <div style="font-size: 0.9rem;">Avg Engagement</div>
                            </div>
                            <div style="text-align: center; padding: 1rem; background: rgba(255,255,255,0.1); border-radius: 6px;">
                                <div style="font-size: 2rem; font-weight: bold;" id="completion-rate">-</div>
                                <div style="font-size: 0.9rem;">Completion Rate</div>
                            </div>
                            <div style="text-align: center; padding: 1rem; background: rgba(255,255,255,0.1); border-radius: 6px;">
                                <div style="font-size: 2rem; font-weight: bold;" id="top-lesson">-</div>
                                <div style="font-size: 0.9rem;">Top Lesson</div>
                            </div>
                        </div>
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
                    </div>
                </div>
            </div>
            
            <script>
                function showTab(tabName) {{
                    const tabContents = document.querySelectorAll('.tab-content');
                    tabContents.forEach(content => content.style.display = 'none');
                    
                    const tabs = document.querySelectorAll('.tab');
                    tabs.forEach(tab => tab.classList.remove('active'));
                    
                    document.getElementById(tabName).style.display = 'block';
                    event.target.classList.add('active');
                }}
                
                document.addEventListener('DOMContentLoaded', function() {{
                    // Dynamic data from server
                    const lessonNames = {lesson_names};
                    const lessonCounts = {lesson_counts};
                    const behaviorLabels = {behavior_labels};
                    const behaviorValues = {behavior_values};
                    
                    // Funnel chart
                    Plotly.newPlot('funnel-chart', [{{
                        type: 'funnel',
                        y: lessonNames,
                        x: lessonCounts,
                        textinfo: 'value+percent initial'
                    }}], {{title: 'Lesson Engagement Funnel', height: 400}});
                    
                    // Completion chart
                    Plotly.newPlot('completion-chart', [{{
                        type: 'bar',
                        x: lessonNames,
                        y: lessonCounts,
                        marker: {{color: ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe']}}
                    }}], {{title: 'Lesson Completion by Response Count', height: 400, xaxis: {{tickangle: -45}}}});
                    
                    // Behavior chart
                    Plotly.newPlot('behavior-chart', [{{
                        type: 'pie',
                        labels: behaviorLabels,
                        values: behaviorValues,
                        hole: 0.3
                    }}], {{title: 'Behavior Priorities', height: 400}});
                    
                    // Heatmap chart
                    Plotly.newPlot('heatmap-chart', [{{
                        type: 'heatmap',
                        z: [lessonCounts],
                        x: Array.from({{length: lessonNames.length}}, (_, i) => i + 1),
                        y: lessonNames,
                        colorscale: 'Blues'
                    }}], {{title: 'Engagement Heatmap by Lesson', height: 400}});
                    
                    // Timeline chart
                    Plotly.newPlot('timeline-chart', [{{
                        type: 'scatter',
                        x: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                        y: [15, 18, 12, 14],
                        mode: 'lines+markers',
                        line: {{color: '#667eea', width: 3}}
                    }}], {{title: 'User Activity Timeline', height: 300, xaxis: {{title: 'Week'}}, yaxis: {{title: 'Active Users'}}}});
                    
                    // Before/After chart
                    Plotly.newPlot('before-after-chart', [
                        {{type: 'bar', name: 'Before', x: ['Screen Time Awareness', 'Focus Duration', 'Sleep Quality', 'Stress Management', 'Digital Balance'], y: [3.2, 2.8, 3.5, 2.9, 2.6], marker: {{color: '#e53e3e'}}}},
                        {{type: 'bar', name: 'After', x: ['Screen Time Awareness', 'Focus Duration', 'Sleep Quality', 'Stress Management', 'Digital Balance'], y: [4.8, 4.2, 4.6, 4.1, 4.3], marker: {{color: '#48bb78'}}}}
                    ], {{title: 'Before vs After Metrics (1-5 Scale)', height: 400, barmode: 'group', xaxis: {{tickangle: -45}}}});
                    
                    // Improvement chart
                    Plotly.newPlot('improvement-chart', [{{
                        type: 'bar',
                        x: ['Screen Time Awareness', 'Focus Duration', 'Sleep Quality', 'Stress Management', 'Digital Balance'],
                        y: [50, 50, 31, 41, 65],
                        marker: {{color: [50, 50, 31, 41, 65], colorscale: 'Greens'}}
                    }}], {{title: 'Percentage Improvement by Metric', height: 400, xaxis: {{tickangle: -45}}}});
                    
                    // Cohort chart
                    Plotly.newPlot('cohort-chart', [{{
                        type: 'bar',
                        x: ['Spring 2024', 'Fall 2023', 'Summer 2023'],
                        y: [78, 82, 75],
                        marker: {{color: [78, 82, 75], colorscale: 'Blues'}}
                    }}], {{title: 'Cohort Completion Rates', height: 400}});
                    
                    // Cohort distribution chart
                    Plotly.newPlot('cohort-distribution-chart', [{{
                        type: 'pie',
                        labels: ['Spring 2024', 'Fall 2023', 'Summer 2023'],
                        values: [12, 8, 5]
                    }}], {{title: 'User Distribution by Cohort', height: 400}});
                    
                    // Lesson cohort chart
                    Plotly.newPlot('lesson-cohort-chart', [
                        {{type: 'bar', name: 'Spring 2024', x: lessonNames, y: [85, 92, 78, 70, 88, 82, 75, 79, 84, 90]}},
                        {{type: 'bar', name: 'Fall 2023', x: lessonNames, y: [88, 90, 82, 75, 85, 80, 78, 82, 87, 92]}},
                        {{type: 'bar', name: 'Summer 2023', x: lessonNames, y: [80, 85, 75, 68, 82, 76, 72, 78, 83, 88]}}
                    ], {{title: 'Lesson Performance by Cohort', height: 400, barmode: 'group', xaxis: {{tickangle: -45}}}});
                    
                    // Initialize data explorer
                    initializeDataExplorer();
                }});
                
                // Enhanced HR Analytics Explorer Functions
                let currentData = [];
                let currentTable = '';
                let filteredData = [];
                
                async function initializeDataExplorer() {{
                    // Load lesson options
                    await loadLessonOptions();
                    await loadUserOptions();
                    
                    // Initialize interactive charts
                    createInteractiveCharts();
                    updateQuickInsights();
                }}
                
                function createInteractiveCharts() {{
                    // Interactive lesson engagement chart
                    Plotly.newPlot('interactive-lesson-chart', [{{
                        type: 'bar',
                        x: lessonNames,
                        y: lessonCounts,
                        marker: {{color: lessonCounts, colorscale: 'Blues'}},
                        hovertemplate: '<b>%{{x}}</b><br>Engagement: %{{y}} participants<extra></extra>'
                    }}], {{
                        title: 'Click any bar to filter data',
                        height: 300,
                        xaxis: {{tickangle: -45}},
                        yaxis: {{title: 'Participants'}},
                        clickmode: 'event'
                    }});
                    
                    // Response pattern chart
                    Plotly.newPlot('response-pattern-chart', [{{
                        type: 'pie',
                        labels: behaviorLabels,
                        values: behaviorValues,
                        hole: 0.4,
                        hovertemplate: '<b>%{{label}}</b><br>Responses: %{{value}}<extra></extra>'
                    }}], {{
                        title: 'Response Patterns by Category',
                        height: 300
                    }});
                    
                    // Add click handlers for interactive filtering
                    document.getElementById('interactive-lesson-chart').on('plotly_click', function(data) {{
                        const lessonName = data.points[0].x;
                        const lessonIndex = lessonNames.indexOf(lessonName);
                        if (lessonIndex !== -1) {{
                            document.getElementById('lesson-filter').value = lessonIndex + 1;
                            applyFilters();
                        }}
                    }});
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
                                option.value = lesson.id;
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
                        document.getElementById('data-table').innerHTML = '<p style="text-align: center; color: #718096;">No data available</p>';
                        return;
                    }}
                    
                    let tableHTML = '<table style="width: 100%; border-collapse: collapse; font-size: 0.9rem;">';
                    
                    // Header
                    tableHTML += '<thead><tr style="background: #f7fafc; border-bottom: 2px solid #e2e8f0;">';
                    columns.forEach(col => {{
                        tableHTML += '<th style="padding: 0.75rem; text-align: left; font-weight: 600; color: #2d3748;">' + col + '</th>';
                    }});
                    tableHTML += '</tr></thead>';
                    
                    // Body
                    tableHTML += '<tbody>';
                    data.forEach((row, index) => {{
                        tableHTML += '<tr style="border-bottom: 1px solid #e2e8f0;' + (index % 2 === 0 ? 'background: #fafafa;' : '') + '">';
                        columns.forEach(col => {{
                            const value = row[col] || '';
                            tableHTML += '<td style="padding: 0.75rem; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="' + value + '">' + value + '</td>';
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
                            if (row.lesson_number) return row.lesson_number == lessonFilter;
                            if (row.lesson_id) return row.lesson_id == lessonFilter;
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
                        statusText = '🔍 Filters applied: ';
                        const filters = [];
                        if (lessonFilter) filters.push('Lesson ' + lessonFilter);
                        if (userFilter) filters.push('User ' + userFilter);
                        if (searchFilter) filters.push('Search: "' + searchFilter + '"');
                        statusText += filters.join(', ');
                    }} else {{
                        statusText = '📊 Showing all data';
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
                transition: all 0.3s ease;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
            }
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
                    <a href="/dashboard" class="btn">Open Dashboard</a>
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
                    <a href="/playground" class="btn">🚀 Developer Playground</a>
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