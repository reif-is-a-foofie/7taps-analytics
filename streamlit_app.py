import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import json
from datetime import datetime
import sqlite3
import os

# Page config
st.set_page_config(
    page_title="7taps Analytics - Seven",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for the chat interface
st.markdown("""
<style>
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    .bot-message {
        background-color: #f3e5f5;
        border-left: 4px solid #9c27b0;
    }
    .stButton > button {
        width: 100%;
        border-radius: 20px;
        height: 3rem;
        border: 1px solid #ddd;
    }
    .main-header {
        text-align: center;
        color: #1f1f1f;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 2rem;
    }
    .seven-bot {
        color: #9c27b0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'current_viz' not in st.session_state:
    st.session_state.current_viz = None
if 'viz_history' not in st.session_state:
    st.session_state.viz_history = []
if 'current_query' not in st.session_state:
    st.session_state.current_query = ""

# Database connection function
def get_db_connection():
    """Get connection to the analytics database"""
    try:
        # For now, we'll use the API endpoint to query data
        # In production, you'd connect directly to the database
        return None
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

# API functions
def query_database(sql_query):
    """Execute SQL query via the API"""
    try:
        response = requests.post(
            "https://seventaps-analytics-5135b3a0701a.herokuapp.com/ui/db-query",
            json={"query": sql_query},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API error: {response.status_code}"}
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}

def get_data_overview():
    """Get overview of available data"""
    try:
        response = requests.get(
            "https://seventaps-analytics-5135b3a0701a.herokuapp.com/api/ui/nlp-status",
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except:
        return None

# Visualization functions
def create_visualization(data, chart_type="bar", title="", x_col=None, y_col=None):
    """Create Plotly visualization based on data and type"""
    if not data or len(data) == 0:
        return None
    
    df = pd.DataFrame(data)
    
    if chart_type == "bar":
        if x_col and y_col and x_col in df.columns and y_col in df.columns:
            fig = px.bar(df, x=x_col, y=y_col, title=title)
        else:
            # Auto-detect columns
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0 and len(df.columns) > 1:
                fig = px.bar(df, x=df.columns[0], y=numeric_cols[0], title=title)
            else:
                fig = px.bar(df, title=title)
    
    elif chart_type == "line":
        if x_col and y_col and x_col in df.columns and y_col in df.columns:
            fig = px.line(df, x=x_col, y=y_col, title=title)
        else:
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0 and len(df.columns) > 1:
                fig = px.line(df, x=df.columns[0], y=numeric_cols[0], title=title)
            else:
                fig = px.line(df, title=title)
    
    elif chart_type == "pie":
        if len(df.columns) >= 2:
            fig = px.pie(df, values=df.columns[1], names=df.columns[0], title=title)
        else:
            fig = px.pie(df, title=title)
    
    elif chart_type == "scatter":
        if len(df.columns) >= 2:
            fig = px.scatter(df, x=df.columns[0], y=df.columns[1], title=title)
        else:
            fig = px.scatter(df, title=title)
    
    else:
        fig = px.bar(df, title=title)
    
    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig

# Preloaded system context for the bot
SYSTEM_CONTEXT = """
You are Seven, a digital wellness data analyst for the 7taps learning platform. You have access to a unified analytics database with the following structure:

DATABASE SCHEMA:
- statements_new: Core learning statements (statement_id, actor_id, activity_id, verb_id, timestamp, source, raw_json)
- results_new: Learning results and scores (statement_id, score, success, duration, response)
- context_extensions_new: Extended context data (statement_id, extension_key, extension_value)

DATA SOURCES:
- 373 CSV focus group responses (source='csv')
- 260 xAPI real-time activities (source='xapi')
- Total: 633 unified statements

COMMON QUERIES:
- "Show total statements by source" → SELECT source, COUNT(*) FROM statements_new GROUP BY source
- "Focus group responses by lesson" → SELECT ce.extension_value as lesson, COUNT(*) FROM statements_new s JOIN context_extensions_new ce ON s.statement_id = ce.statement_id WHERE s.source = 'csv' AND ce.extension_key = 'lesson_number' GROUP BY ce.extension_value
- "Recent activity timeline" → SELECT DATE(timestamp) as date, COUNT(*) FROM statements_new GROUP BY DATE(timestamp) ORDER BY date DESC LIMIT 10
- "Learner engagement by source" → SELECT source, COUNT(DISTINCT actor_id) as unique_learners FROM statements_new GROUP BY source

RESPONSE FORMAT:
Always respond with:
1. SQL_QUERY: <executable SQL>
2. INSIGHT: <human-readable interpretation focusing on wellness impact and behavior change>

STYLE:
- Emphasize behavior change and wellness impact
- Use encouraging, supportive language
- Focus on actionable insights
- Reference the unified data approach
"""

# Main app layout
def main():
    # Header
    st.markdown('<h1 class="main-header">🧠 <span class="seven-bot">Seven</span> Analytics</h1>', unsafe_allow_html=True)
    
    # Two-column layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 💬 Chat with Seven")
        
        # Chat input
        user_input = st.text_input(
            "Ask Seven about your learning analytics...",
            key="user_input",
            placeholder="e.g., 'Show me focus group responses by lesson' or 'What are the engagement trends?'"
        )
        
        if st.button("Send", key="send_button"):
            if user_input:
                # Add user message
                st.session_state.messages.append({"role": "user", "content": user_input})
                st.session_state.current_query = user_input
                
                # Generate bot response
                bot_response = generate_bot_response(user_input)
                st.session_state.messages.append({"role": "assistant", "content": bot_response})
                
                # Clear input
                st.session_state.user_input = ""
                st.rerun()
        
        # Display chat messages
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f"""
                <div class="chat-message user-message">
                    <strong>You:</strong> {message["content"]}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-message bot-message">
                    <strong>Seven:</strong> {message["content"]}
                </div>
                """, unsafe_allow_html=True)
        
        # Clear chat button
        if st.button("Clear Chat", key="clear_chat"):
            st.session_state.messages = []
            st.session_state.current_viz = None
            st.rerun()
    
    with col2:
        st.markdown("### 📊 Visualization")
        
        if st.session_state.current_viz:
            st.plotly_chart(st.session_state.current_viz, use_container_width=True)
            
            # Save visualization
            if st.button("Save Visualization", key="save_viz"):
                save_visualization(st.session_state.current_viz, st.session_state.current_query)
                st.success("Visualization saved!")
        else:
            st.info("Ask Seven a question to see visualizations here!")
        
        # Show visualization history
        if st.session_state.viz_history:
            st.markdown("### 📚 Saved Visualizations")
            for i, (title, viz) in enumerate(st.session_state.viz_history):
                if st.button(f"Load: {title}", key=f"load_viz_{i}"):
                    st.session_state.current_viz = viz
                    st.session_state.current_query = title
                    st.rerun()

def generate_bot_response(user_query):
    """Generate bot response based on user query"""
    # This is where you'd integrate with OpenAI/ChatGPT
    # For now, we'll use a simple rule-based system
    
    query_lower = user_query.lower()
    
    # Predefined responses based on common patterns
    if "total" in query_lower and ("statement" in query_lower or "data" in query_lower):
        sql_query = """
        SELECT 
            source,
            COUNT(*) as total_statements,
            COUNT(DISTINCT actor_id) as unique_learners
        FROM statements_new
        GROUP BY source
        ORDER BY total_statements DESC
        """
        insight = "Your learning platform has collected 633 total statements across both focus group surveys and real-time xAPI activities. This unified approach gives you comprehensive insights into both structured feedback and natural learning behaviors."
        
    elif "focus group" in query_lower or "csv" in query_lower:
        sql_query = """
        SELECT 
            ce.extension_value as lesson_number,
            COUNT(*) as responses
        FROM statements_new s
        JOIN context_extensions_new ce ON s.statement_id = ce.statement_id
        WHERE s.source = 'csv' AND ce.extension_key = 'lesson_number'
        GROUP BY ce.extension_value
        ORDER BY lesson_number
        """
        insight = "The focus group data shows engagement across different lessons, helping identify which content resonates most with learners and where additional support might be needed."
        
    elif "trend" in query_lower or "timeline" in query_lower:
        sql_query = """
        SELECT 
            DATE(timestamp) as date,
            COUNT(*) as daily_activity
        FROM statements_new
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
        LIMIT 10
        """
        insight = "This timeline shows learning activity patterns over time, helping identify peak engagement periods and potential drop-off points in the learning journey."
        
    elif "engagement" in query_lower:
        sql_query = """
        SELECT 
            source,
            COUNT(DISTINCT actor_id) as unique_learners,
            COUNT(*) as total_activities
        FROM statements_new
        GROUP BY source
        """
        insight = "Comparing engagement across data sources reveals how different types of learning activities contribute to overall platform usage and learner satisfaction."
        
    else:
        # Default response
        sql_query = """
        SELECT 
            source,
            COUNT(*) as count
        FROM statements_new
        GROUP BY source
        """
        insight = "Here's an overview of your learning data. Feel free to ask more specific questions about focus group responses, engagement trends, or specific lessons!"
    
    # Execute the query and create visualization
    result = query_database(sql_query)
    
    if result and "results" in result:
        # Create visualization
        viz = create_visualization(
            result["results"], 
            chart_type="bar",
            title=f"Results for: {user_query}"
        )
        if viz:
            st.session_state.current_viz = viz
    
    return f"""
**SQL Query:**
```sql
{sql_query}
```

**Insight:**
{insight}

*Ask me to save this visualization or explore other aspects of your data!*
"""

def save_visualization(viz, title):
    """Save visualization to history"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    saved_title = f"{title} ({timestamp})"
    st.session_state.viz_history.append((saved_title, viz))

if __name__ == "__main__":
    main()
