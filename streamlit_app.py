import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
import sqlite3
import os
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.7taps')

# Configure OpenAI
openai.api_key = os.getenv('OPEN-AI_KEY')

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
    .sql-block {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 0.375rem;
        padding: 1rem;
        margin: 1rem 0;
        font-family: 'Courier New', monospace;
        font-size: 0.875rem;
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
    """Create Streamlit visualization based on data and type"""
    if not data or len(data) == 0:
        return None
    
    df = pd.DataFrame(data)
    
    # For Streamlit native charts, we return the dataframe and chart type
    # The actual chart rendering happens in the main UI
    return {
        "dataframe": df,
        "chart_type": chart_type,
        "title": title,
        "x_col": x_col,
        "y_col": y_col
    }

def render_streamlit_chart(viz_data):
    """Render chart using Streamlit's native charting"""
    if not viz_data:
        return
    
    df = viz_data["dataframe"]
    chart_type = viz_data["chart_type"]
    title = viz_data["title"]
    
    # Display title
    if title:
        st.subheader(title)
    
    # Render appropriate chart based on type
    if chart_type == "bar":
        st.bar_chart(df)
    elif chart_type == "line":
        st.line_chart(df)
    elif chart_type == "area":
        st.area_chart(df)
    elif chart_type == "scatter":
        # For scatter, we need to specify columns
        if len(df.columns) >= 2:
            st.scatter_chart(df, x=df.columns[0], y=df.columns[1])
        else:
            st.write("Need at least 2 columns for scatter chart")
    else:
        # Default to bar chart
        st.bar_chart(df)
    
    # Show the raw data below
    with st.expander("View Raw Data"):
        st.dataframe(df)

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
- Be conversational and helpful
"""

def generate_bot_response_with_openai(user_query):
    """Generate bot response using OpenAI"""
    try:
        # Prepare the conversation
        messages = [
            {"role": "system", "content": SYSTEM_CONTEXT},
            {"role": "user", "content": f"User asks: {user_query}\n\nPlease provide a SQL query and insight in the format specified."}
        ]
        
        # Call OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        
        bot_response = response.choices[0].message.content
        
        # Extract SQL query from response
        sql_query = extract_sql_from_response(bot_response)
        
        if sql_query:
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
        
        return bot_response
        
    except Exception as e:
        st.error(f"OpenAI API error: {str(e)}")
        return f"I'm having trouble connecting to my AI brain right now. Error: {str(e)}"

def extract_sql_from_response(response):
    """Extract SQL query from OpenAI response"""
    try:
        # Look for SQL_QUERY: pattern
        if "SQL_QUERY:" in response:
            sql_start = response.find("SQL_QUERY:") + len("SQL_QUERY:")
            sql_end = response.find("INSIGHT:") if "INSIGHT:" in response else len(response)
            sql_query = response[sql_start:sql_end].strip()
            
            # Clean up the SQL
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
            return sql_query
        
        # Fallback: look for code blocks
        if "```" in response:
            lines = response.split("```")
            for i, line in enumerate(lines):
                if "SELECT" in line.upper() and "FROM" in line.upper():
                    return line.strip()
        
        return None
    except:
        return None

# Main app layout
def main():
    # Header
    st.markdown('<h1 class="main-header">🧠 <span class="seven-bot">Seven</span> Analytics</h1>', unsafe_allow_html=True)
    
    # Show OpenAI status
    if openai.api_key:
        st.sidebar.success("✅ OpenAI Connected")
    else:
        st.sidebar.error("❌ OpenAI Not Connected")
    
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
                
                # Show loading message
                with st.spinner("Seven is thinking..."):
                    # Generate bot response with OpenAI
                    bot_response = generate_bot_response_with_openai(user_input)
                    st.session_state.messages.append({"role": "assistant", "content": bot_response})
                
                # Clear input - use rerun instead of direct assignment
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
                # Format the bot response nicely
                formatted_response = format_bot_response(message["content"])
                st.markdown(f"""
                <div class="chat-message bot-message">
                    <strong>Seven:</strong> {formatted_response}
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
            render_streamlit_chart(st.session_state.current_viz)
            
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

def format_bot_response(response):
    """Format bot response with proper styling"""
    # Replace SQL_QUERY: with styled block
    if "SQL_QUERY:" in response:
        response = response.replace("SQL_QUERY:", "<strong>SQL Query:</strong>")
        response = response.replace("INSIGHT:", "<br><strong>Insight:</strong>")
    
    return response

def save_visualization(viz, title):
    """Save visualization to history"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    saved_title = f"{title} ({timestamp})"
    st.session_state.viz_history.append((saved_title, viz))

if __name__ == "__main__":
    main()
