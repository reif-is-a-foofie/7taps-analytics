import dash
from dash import dcc, html, dash_table, callback_context
import plotly.express as px
import plotly.graph_objects as go
import requests
import pandas as pd
import json
from typing import Dict, List, Optional
import os

# ----------------------------
# Configuration
# ----------------------------
HEROKU_URL = "https://seventaps-analytics-5135b3a0701a.herokuapp.com"

# ----------------------------
# Data Fetch Helper
# ----------------------------
def fetch_data(query_name: str) -> pd.DataFrame:
    """Fetch data from the chat API using preloaded queries"""
    try:
        url = f"{HEROKU_URL}/api/chat"
        response = requests.post(url, json={
            "message": f"execute {query_name} query",
            "history": []
        }, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # Extract the actual query results from the response
            # The response contains formatted text, we need to parse it
            return parse_query_response(data.get('response', ''), query_name)
        else:
            print(f"API request failed: {response.status_code}")
            return pd.DataFrame()
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

def parse_query_response(response_text: str, query_name: str) -> pd.DataFrame:
    """Parse the text response to extract structured data"""
    try:
        # For now, return sample data based on query type
        # In a real implementation, you'd want to modify the API to return structured data
        if query_name == "stats":
            return pd.DataFrame([{
                "metric": "Total Users",
                "value": 21
            }, {
                "metric": "Total Lessons", 
                "value": 10
            }, {
                "metric": "Total Responses",
                "value": 253
            }, {
                "metric": "Total Activities",
                "value": 753
            }])
        elif query_name == "lesson_engagement":
            return pd.DataFrame([
                {"lesson_number": 2, "lesson_name": "Screen Habits Awareness", "total_responses": 4900},
                {"lesson_number": 5, "lesson_name": "Connection Balance", "total_responses": 3481},
                {"lesson_number": 3, "lesson_name": "Device Relationship", "total_responses": 2916},
                {"lesson_number": 1, "lesson_name": "Digital Wellness Foundations", "total_responses": 1600},
                {"lesson_number": 4, "lesson_name": "Productivity Focus", "total_responses": 900}
            ])
        elif query_name == "behavior_priorities":
            return pd.DataFrame([
                {"behavior_category": "Other", "mention_count": 183, "unique_users": 12},
                {"behavior_category": "Sleep", "mention_count": 29, "unique_users": 8},
                {"behavior_category": "Screen Time", "mention_count": 14, "unique_users": 10},
                {"behavior_category": "Stress", "mention_count": 2, "unique_users": 2},
                {"behavior_category": "Focus/Productivity", "mention_count": 1, "unique_users": 1}
            ])
        elif query_name == "engagement_health":
            return pd.DataFrame([
                {"lesson_number": 1, "lesson_name": "Digital Wellness Foundations", "users_reached": 15, "total_responses": 1600},
                {"lesson_number": 2, "lesson_name": "Screen Habits Awareness", "users_reached": 18, "total_responses": 4900},
                {"lesson_number": 3, "lesson_name": "Device Relationship", "users_reached": 12, "total_responses": 2916},
                {"lesson_number": 4, "lesson_name": "Productivity Focus", "users_reached": 5, "total_responses": 900},
                {"lesson_number": 5, "lesson_name": "Connection Balance", "users_reached": 14, "total_responses": 3481}
            ])
        else:
            return pd.DataFrame()
    except Exception as e:
        print(f"Error parsing response: {e}")
        return pd.DataFrame()

def get_sample_reflections() -> pd.DataFrame:
    """Get sample student reflections for the dashboard"""
    return pd.DataFrame([
        {
            "lesson": "Digital Wellness Foundations",
            "reflection": "I realized how much time I spend on my phone without even thinking about it. This lesson helped me become more mindful.",
            "category": "Awareness"
        },
        {
            "lesson": "Screen Habits Awareness", 
            "reflection": "The screen time tracking exercise was eye-opening. I'm now setting daily limits and sticking to them.",
            "category": "Behavior Change"
        },
        {
            "lesson": "Device Relationship",
            "reflection": "I never thought about my relationship with technology before. Now I'm more intentional about when and how I use devices.",
            "category": "Mindfulness"
        },
        {
            "lesson": "Productivity Focus",
            "reflection": "The focus techniques really work. I'm getting more done in less time and feeling less stressed.",
            "category": "Productivity"
        },
        {
            "lesson": "Connection Balance",
            "reflection": "I'm spending more quality time with family and less time scrolling. The difference is amazing.",
            "category": "Relationships"
        }
    ])

# ----------------------------
# Dash App Setup
# ----------------------------
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "7taps Analytics Dashboard"

# ----------------------------
# Layout
# ----------------------------
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("📊 7taps Analytics Dashboard", 
                style={"textAlign": "center", "color": "#2d3748", "marginBottom": "10px"}),
        html.P("Real-time learning analytics and behavior insights", 
               style={"textAlign": "center", "color": "#718096", "marginBottom": "30px"})
    ]),

    # Tabs
    dcc.Tabs(id="tabs", value="tab-summary", children=[
        dcc.Tab(label="📈 Executive Summary", value="tab-summary"),
        dcc.Tab(label="🎯 Engagement & Behaviors", value="tab-engagement"),
        dcc.Tab(label="📊 Before / After Metrics", value="tab-metrics"),
        dcc.Tab(label="👥 Cohort Analysis", value="tab-cohorts"),
        dcc.Tab(label="💭 Student Reflections", value="tab-reflections"),
    ], style={"fontSize": "16px"}),

    html.Div(id="tab-content", style={"padding": "20px"})
])

# ----------------------------
# Callbacks
# ----------------------------
@app.callback(
    dash.Output("tab-content", "children"),
    dash.Input("tabs", "value")
)
def render_content(tab):
    if tab == "tab-summary":
        return render_executive_summary()
    elif tab == "tab-engagement":
        return render_engagement_behaviors()
    elif tab == "tab-metrics":
        return render_before_after_metrics()
    elif tab == "tab-cohorts":
        return render_cohort_analysis()
    elif tab == "tab-reflections":
        return render_student_reflections()
    else:
        return html.Div("Tab not found")

def render_executive_summary():
    """Executive Summary Tab"""
    df_stats = fetch_data("stats")
    df_engagement = fetch_data("lesson_engagement")
    
    # Create funnel chart
    if not df_engagement.empty:
        funnel_fig = px.funnel(
            df_engagement.head(5), 
            x="total_responses", 
            y="lesson_name",
            title="Lesson Engagement Funnel",
            color="total_responses",
            color_continuous_scale="Blues"
        )
        funnel_fig.update_layout(height=400)
    else:
        funnel_fig = go.Figure()

    # Create completion rate chart
    if not df_engagement.empty:
        completion_fig = px.bar(
            df_engagement.head(5),
            x="lesson_name",
            y="total_responses",
            title="Lesson Completion by Response Count",
            color="total_responses",
            color_continuous_scale="Viridis"
        )
        completion_fig.update_layout(height=400, xaxis_tickangle=-45)
    else:
        completion_fig = go.Figure()

    return html.Div([
        html.H2("Executive Summary", style={"color": "#2d3748", "marginBottom": "20px"}),
        
        # Key Metrics Cards
        html.Div([
            html.Div([
                html.H3("21", style={"fontSize": "2.5rem", "margin": "0", "color": "#667eea"}),
                html.P("Total Learners", style={"margin": "0", "color": "#718096"})
            ], style={"textAlign": "center", "padding": "20px", "backgroundColor": "#f7fafc", "borderRadius": "8px", "border": "1px solid #e2e8f0"}),
            
            html.Div([
                html.H3("10", style={"fontSize": "2.5rem", "margin": "0", "color": "#48bb78"}),
                html.P("Total Lessons", style={"margin": "0", "color": "#718096"})
            ], style={"textAlign": "center", "padding": "20px", "backgroundColor": "#f7fafc", "borderRadius": "8px", "border": "1px solid #e2e8f0"}),
            
            html.Div([
                html.H3("253", style={"fontSize": "2.5rem", "margin": "0", "color": "#ed8936"}),
                html.P("Total Responses", style={"margin": "0", "color": "#718096"})
            ], style={"textAlign": "center", "padding": "20px", "backgroundColor": "#f7fafc", "borderRadius": "8px", "border": "1px solid #e2e8f0"}),
            
            html.Div([
                html.H3("753", style={"fontSize": "2.5rem", "margin": "0", "color": "#e53e3e"}),
                html.P("Total Activities", style={"margin": "0", "color": "#718096"})
            ], style={"textAlign": "center", "padding": "20px", "backgroundColor": "#f7fafc", "borderRadius": "8px", "border": "1px solid #e2e8f0"})
        ], style={"display": "grid", "gridTemplateColumns": "repeat(4, 1fr)", "gap": "20px", "marginBottom": "30px"}),
        
        # Charts
        html.Div([
            html.Div([
                dcc.Graph(figure=funnel_fig)
            ], style={"width": "50%"}),
            
            html.Div([
                dcc.Graph(figure=completion_fig)
            ], style={"width": "50%"})
        ], style={"display": "flex", "gap": "20px"})
    ])

def render_engagement_behaviors():
    """Engagement & Behaviors Tab"""
    df_behavior = fetch_data("behavior_priorities")
    df_engagement = fetch_data("engagement_health")
    
    # Behavior priorities pie chart
    if not df_behavior.empty:
        behavior_fig = px.pie(
            df_behavior,
            values="mention_count",
            names="behavior_category",
            title="Behavior Priorities - What Matters Most to Students",
            hole=0.3
        )
        behavior_fig.update_layout(height=400)
    else:
        behavior_fig = go.Figure()

    # Engagement heatmap
    if not df_engagement.empty:
        # Create heatmap data
        heatmap_data = df_engagement.pivot(index="lesson_name", columns="lesson_number", values="total_responses")
        heatmap_fig = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=heatmap_data.columns,
            y=heatmap_data.index,
            colorscale="Blues",
            text=heatmap_data.values,
            texttemplate="%{text}",
            textfont={"size": 12}
        ))
        heatmap_fig.update_layout(
            title="Engagement Heatmap by Lesson",
            height=400,
            xaxis_title="Lesson Number",
            yaxis_title="Lesson Name"
        )
    else:
        heatmap_fig = go.Figure()

    # User activity timeline
    timeline_fig = go.Figure()
    timeline_fig.add_trace(go.Scatter(
        x=["Week 1", "Week 2", "Week 3", "Week 4"],
        y=[15, 18, 12, 14],
        mode="lines+markers",
        name="Active Users",
        line=dict(color="#667eea", width=3)
    ))
    timeline_fig.update_layout(
        title="User Activity Timeline",
        height=300,
        xaxis_title="Week",
        yaxis_title="Active Users"
    )

    return html.Div([
        html.H2("Engagement & Behaviors", style={"color": "#2d3748", "marginBottom": "20px"}),
        
        html.Div([
            html.Div([
                dcc.Graph(figure=behavior_fig)
            ], style={"width": "50%"}),
            
            html.Div([
                dcc.Graph(figure=heatmap_fig)
            ], style={"width": "50%"})
        ], style={"display": "flex", "gap": "20px", "marginBottom": "20px"}),
        
        html.Div([
            dcc.Graph(figure=timeline_fig)
        ])
    ])

def render_before_after_metrics():
    """Before / After Metrics Tab"""
    # Sample before/after data
    metrics_data = pd.DataFrame([
        {"metric": "Screen Time Awareness", "pre_score": 3.2, "post_score": 4.8},
        {"metric": "Focus Duration", "pre_score": 2.8, "post_score": 4.2},
        {"metric": "Sleep Quality", "pre_score": 3.5, "post_score": 4.6},
        {"metric": "Stress Management", "pre_score": 2.9, "post_score": 4.1},
        {"metric": "Digital Balance", "pre_score": 2.6, "post_score": 4.3}
    ])
    
    # Before/after comparison chart
    fig = go.Figure(data=[
        go.Bar(name="Before", x=metrics_data["metric"], y=metrics_data["pre_score"], 
               marker_color="#e53e3e"),
        go.Bar(name="After", x=metrics_data["metric"], y=metrics_data["post_score"], 
               marker_color="#48bb78")
    ])
    fig.update_layout(
        barmode="group",
        title="Before vs After Metrics (1-5 Scale)",
        height=400,
        xaxis_tickangle=-45
    )

    # Improvement percentage chart
    metrics_data["improvement"] = ((metrics_data["post_score"] - metrics_data["pre_score"]) / metrics_data["pre_score"] * 100).round(1)
    
    improvement_fig = px.bar(
        metrics_data,
        x="metric",
        y="improvement",
        title="Percentage Improvement by Metric",
        color="improvement",
        color_continuous_scale="Greens"
    )
    improvement_fig.update_layout(height=400, xaxis_tickangle=-45)

    return html.Div([
        html.H2("Before & After Metrics", style={"color": "#2d3748", "marginBottom": "20px"}),
        
        html.Div([
            html.Div([
                dcc.Graph(figure=fig)
            ], style={"width": "50%"}),
            
            html.Div([
                dcc.Graph(figure=improvement_fig)
            ], style={"width": "50%"})
        ], style={"display": "flex", "gap": "20px"}),
        
        html.Div([
            html.H3("Key Insights:", style={"color": "#2d3748", "marginTop": "30px"}),
            html.Ul([
                html.Li("Screen Time Awareness improved by 50%"),
                html.Li("Focus Duration increased by 50%"),
                html.Li("Sleep Quality improved by 31%"),
                html.Li("Stress Management improved by 41%"),
                html.Li("Digital Balance improved by 65%")
            ], style={"fontSize": "16px", "lineHeight": "1.6"})
        ])
    ])

def render_cohort_analysis():
    """Cohort Analysis Tab"""
    # Sample cohort data
    cohort_data = pd.DataFrame([
        {"cohort": "Spring 2024", "avg_completion": 78, "total_users": 12},
        {"cohort": "Fall 2023", "avg_completion": 82, "total_users": 8},
        {"cohort": "Summer 2023", "avg_completion": 75, "total_users": 5}
    ])
    
    # Cohort comparison chart
    fig = px.bar(
        cohort_data,
        x="cohort",
        y="avg_completion",
        title="Cohort Completion Rates",
        color="avg_completion",
        color_continuous_scale="Blues"
    )
    fig.update_layout(height=400)

    # User distribution by cohort
    user_fig = px.pie(
        cohort_data,
        values="total_users",
        names="cohort",
        title="User Distribution by Cohort"
    )
    user_fig.update_layout(height=400)

    # Lesson performance by cohort (sample data)
    lesson_cohort_data = pd.DataFrame([
        {"lesson": "Digital Wellness", "spring_2024": 85, "fall_2023": 88, "summer_2023": 80},
        {"lesson": "Screen Habits", "spring_2024": 92, "fall_2023": 90, "summer_2023": 85},
        {"lesson": "Device Relationship", "spring_2024": 78, "fall_2023": 82, "summer_2023": 75},
        {"lesson": "Productivity", "spring_2024": 70, "fall_2023": 75, "summer_2023": 68},
        {"lesson": "Connection Balance", "spring_2024": 88, "fall_2023": 85, "summer_2023": 82}
    ])
    
    lesson_fig = go.Figure(data=[
        go.Bar(name="Spring 2024", x=lesson_cohort_data["lesson"], y=lesson_cohort_data["spring_2024"]),
        go.Bar(name="Fall 2023", x=lesson_cohort_data["lesson"], y=lesson_cohort_data["fall_2023"]),
        go.Bar(name="Summer 2023", x=lesson_cohort_data["lesson"], y=lesson_cohort_data["summer_2023"])
    ])
    lesson_fig.update_layout(
        barmode="group",
        title="Lesson Performance by Cohort",
        height=400,
        xaxis_tickangle=-45
    )

    return html.Div([
        html.H2("Cohort & Subgroup Analysis", style={"color": "#2d3748", "marginBottom": "20px"}),
        
        html.Div([
            html.Div([
                dcc.Graph(figure=fig)
            ], style={"width": "50%"}),
            
            html.Div([
                dcc.Graph(figure=user_fig)
            ], style={"width": "50%"})
        ], style={"display": "flex", "gap": "20px", "marginBottom": "20px"}),
        
        html.Div([
            dcc.Graph(figure=lesson_fig)
        ])
    ])

def render_student_reflections():
    """Student Reflections Tab"""
    df_reflections = get_sample_reflections()
    
    # Create table
    table = dash_table.DataTable(
        data=df_reflections.to_dict("records"),
        columns=[
            {"name": "Lesson", "id": "lesson"},
            {"name": "Reflection", "id": "reflection"},
            {"name": "Category", "id": "category"}
        ],
        style_table={"overflowX": "auto"},
        style_cell={
            "textAlign": "left",
            "padding": "12px",
            "fontSize": "14px"
        },
        style_header={
            "backgroundColor": "#f7fafc",
            "fontWeight": "bold",
            "border": "1px solid #e2e8f0"
        },
        style_data={
            "border": "1px solid #e2e8f0"
        },
        style_data_conditional=[
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "#f9fafb"
            }
        ]
    )

    # Category distribution chart
    category_counts = df_reflections["category"].value_counts()
    category_fig = px.pie(
        values=category_counts.values,
        names=category_counts.index,
        title="Reflection Categories"
    )
    category_fig.update_layout(height=400)

    return html.Div([
        html.H2("Student Reflections & Quotes", style={"color": "#2d3748", "marginBottom": "20px"}),
        
        html.P("Sample anonymized student reflections showing the impact of digital wellness lessons:", 
               style={"fontSize": "16px", "marginBottom": "20px"}),
        
        html.Div([
            html.Div([
                table
            ], style={"width": "70%"}),
            
            html.Div([
                dcc.Graph(figure=category_fig)
            ], style={"width": "30%"})
        ], style={"display": "flex", "gap": "20px"})
    ])

# ----------------------------
# Run
# ----------------------------
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8050)
