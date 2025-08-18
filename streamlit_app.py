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
    page_title="Seven Analytics - AI Data Analyst",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for modern chat interface
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f1f1f;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .chat-container {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border: 1px solid #e9ecef;
    }
    
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px 20px;
        border-radius: 18px 18px 4px 18px;
        margin: 10px 0;
        max-width: 80%;
        margin-left: auto;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    
    .bot-message {
        background: white;
        color: #333;
        padding: 15px 20px;
        border-radius: 18px 18px 18px 4px;
        margin: 10px 0;
        max-width: 80%;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    .message-header {
        font-weight: bold;
        margin-bottom: 8px;
        font-size: 0.9rem;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 10px 25px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .input-container {
        background: white;
        border-radius: 25px;
        padding: 5px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        border: 1px solid #e9ecef;
    }
    
    .stTextInput > div > div > input {
        border: none !important;
        box-shadow: none !important;
        border-radius: 20px !important;
        padding: 12px 20px !important;
    }
    
    .viz-container {
        background: white;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    .sidebar-info {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    
    .code-block {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        overflow-x: auto;
    }
    
    .insight-block {
        background: #e8f5e8;
        border-left: 4px solid #28a745;
        padding: 15px;
        margin: 10px 0;
        border-radius: 0 8px 8px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []

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
        
        # Call OpenAI with new API
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        
        bot_response = response.choices[0].message.content
        
        # Extract SQL query from response
        sql_query = extract_sql_from_response(bot_response)
        
        # Initialize message with response
        message_data = {"role": "assistant", "content": bot_response}
        
        if sql_query:
            # Execute the query and create visualization
            result = query_database(sql_query)
            
            if result and "results" in result:
                # Create visualization data
                viz_data = create_visualization(
                    result["results"], 
                    chart_type="bar",
                    title=f"Results for: {user_query}"
                )
                if viz_data:
                    message_data["viz_data"] = viz_data
        
        return message_data
        
    except Exception as e:
        st.error(f"OpenAI API error: {str(e)}")
        return {"role": "assistant", "content": f"I'm having trouble connecting to my AI brain right now. Error: {str(e)}"}

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
    st.markdown('<h1 class="main-header">🧠 Seven Analytics</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #666; margin-bottom: 2rem;">Your AI-powered data analyst for learning analytics</p>', unsafe_allow_html=True)
    
    # Sidebar with info
    with st.sidebar:
        st.markdown('<div class="sidebar-info">', unsafe_allow_html=True)
        st.markdown("### 🤖 AI Status")
        if openai.api_key:
            st.success("✅ OpenAI Connected")
        else:
            st.error("❌ OpenAI Not Connected")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown('<div class="sidebar-info">', unsafe_allow_html=True)
        st.markdown("### 📊 Data Overview")
        st.markdown("- **633** Total Statements")
        st.markdown("- **373** Focus Group Responses")
        st.markdown("- **260** xAPI Activities")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown('<div class="sidebar-info">', unsafe_allow_html=True)
        st.markdown("### 💡 Example Questions")
        st.markdown("- Show me focus group responses by lesson")
        st.markdown("- What are the engagement trends?")
        st.markdown("- Compare CSV vs xAPI data")
        st.markdown("- How many unique learners?")
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Single chat interface
    st.markdown("### 💬 Chat with Seven")
    
    # Chat input with modern styling
    st.markdown('<div class="input-container">', unsafe_allow_html=True)
    user_input = st.text_input(
        "Ask me about your learning analytics...",
        key="user_input",
        placeholder="e.g., 'Show me focus group responses by lesson' or 'What are the engagement trends?'"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    col1a, col1b = st.columns([1, 1])
    with col1a:
        if st.button("🚀 Send", key="send_button", use_container_width=True):
            if user_input:
                # Add user message
                st.session_state.messages.append({"role": "user", "content": user_input})
                
                # Show loading message
                with st.spinner("🧠 Seven is thinking..."):
                    # Generate bot response with OpenAI
                    bot_response_data = generate_bot_response_with_openai(user_input)
                    st.session_state.messages.append(bot_response_data)
                
                # Clear input
                st.rerun()
    
    with col1b:
        if st.button("🗑️ Clear Chat", key="clear_chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    
    # Display chat messages with inline visualizations
    if st.session_state.messages:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f"""
                <div class="user-message">
                    <div class="message-header">You</div>
                    {message["content"]}
                </div>
                """, unsafe_allow_html=True)
            else:
                # Format the bot response nicely
                formatted_response = format_bot_response(message["content"])
                st.markdown(f"""
                <div class="bot-message">
                    <div class="message-header">🧠 Seven</div>
                    {formatted_response}
                </div>
                """, unsafe_allow_html=True)
                
                # Show inline visualization if available
                if "viz_data" in message:
                    st.markdown('<div class="viz-container">', unsafe_allow_html=True)
                    render_streamlit_chart(message["viz_data"])
                    st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("👋 Hi! I'm Seven, your AI data analyst. Ask me anything about your learning analytics data!")

def format_bot_response(response):
    """Format bot response with proper styling"""
    # Replace SQL_QUERY: with styled block
    if "SQL_QUERY:" in response:
        # Extract SQL and insight parts
        parts = response.split("SQL_QUERY:")
        if len(parts) > 1:
            sql_part = parts[1].split("INSIGHT:")[0] if "INSIGHT:" in parts[1] else parts[1]
            insight_part = parts[1].split("INSIGHT:")[1] if "INSIGHT:" in parts[1] else ""
            
            # Format SQL as code block
            sql_clean = sql_part.replace("```sql", "").replace("```", "").strip()
            formatted_sql = f'<div class="code-block">SQL Query:<br><code>{sql_clean}</code></div>'
            
            # Format insight
            if insight_part:
                formatted_insight = f'<div class="insight-block"><strong>💡 Insight:</strong><br>{insight_part.strip()}</div>'
                return f"{formatted_sql}<br>{formatted_insight}"
            else:
                return formatted_sql
    
    return response

if __name__ == "__main__":
    main()
