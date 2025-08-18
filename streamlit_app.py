import streamlit as st
import requests
import json
import openai
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Page config
st.set_page_config(
    page_title="Seven Analytics",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Simple CSS
st.markdown("""
<style>
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Simple chat styling */
    .user-message {
        background: #007bff;
        color: white;
        padding: 12px 16px;
        border-radius: 18px 18px 4px 18px;
        margin: 8px 0;
        max-width: 70%;
        margin-left: auto;
        word-wrap: break-word;
    }
    
    .bot-message {
        background: #f1f3f4;
        color: #333;
        padding: 12px 16px;
        border-radius: 18px 18px 18px 4px;
        margin: 8px 0;
        max-width: 70%;
        word-wrap: break-word;
    }
    
    .code-block {
        background: #f6f8fa;
        border: 1px solid #e1e4e8;
        border-radius: 6px;
        padding: 12px;
        margin: 8px 0;
        font-family: monospace;
        font-size: 14px;
        overflow-x: auto;
    }
    
    .chart-container {
        background: white;
        border: 1px solid #e1e5e9;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Add introduction message
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "Hi, I'm @seven, how can I help you today?"
    })

# Database functions
def query_database(sql_query):
    """Execute SQL query via API"""
    try:
        response = requests.post(
            "https://seventaps-analytics-5135b3a0701a.herokuapp.com/ui/db-query",
            json={"query": sql_query},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API Error: {response.status_code}"}
    except Exception as e:
        return {"error": f"Connection Error: {str(e)}"}

# Create visualization function
def create_visualization(data, chart_type="bar"):
    """Create visualization data"""
    if not data or "error" in data:
        return None
    
    try:
        df_data = data.get("data", [])
        if not df_data:
            return None
            
        return {
            "data": df_data,
            "type": chart_type,
            "columns": data.get("columns", [])
        }
    except Exception as e:
        return None

# Render Streamlit chart
def render_streamlit_chart(viz_data):
    """Render chart using Streamlit native components"""
    if not viz_data:
        return
    
    try:
        data = viz_data["data"]
        chart_type = viz_data["type"]
        
        if not data or len(data) < 2:
            return
            
        import pandas as pd
        df = pd.DataFrame(data[1:], columns=data[0])
        
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        
        if chart_type == "bar":
            st.bar_chart(df.set_index(df.columns[0]))
        elif chart_type == "line":
            st.line_chart(df.set_index(df.columns[0]))
        elif chart_type == "area":
            st.area_chart(df.set_index(df.columns[0]))
        elif chart_type == "scatter":
            if len(df.columns) >= 2:
                st.scatter_chart(df, x=df.columns[0], y=df.columns[1])
        
        st.markdown('</div>', unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Chart error: {str(e)}")

# System context
SYSTEM_CONTEXT = """
You are Seven, a digital wellness data analyst for the 7taps learning platform. You have access to a comprehensive learning analytics database with the following structure:

DATABASE SCHEMA:
- statements_new: Learning activities and responses (statement_id, actor_id, activity_id, verb_id, timestamp, source, raw_json)
- results_new: Learning results and scores (statement_id, score, success, duration, response)
- context_extensions_new: Extended context data (statement_id, extension_key, extension_value)

DATA OVERVIEW:
- 633 total learning activities and responses
- Learners engage through various channels (surveys, real-time activities, etc.)
- All data is unified and accessible through a single interface

COMMON QUERIES:
- "Show total learning activities" → SELECT COUNT(*) FROM statements_new
- "Learning activities by lesson" → SELECT ce.extension_value as lesson, COUNT(*) FROM statements_new s JOIN context_extensions_new ce ON s.statement_id = ce.statement_id WHERE ce.extension_key = 'lesson_number' GROUP BY ce.extension_value
- "Recent activity timeline" → SELECT DATE(timestamp) as date, COUNT(*) FROM statements_new GROUP BY DATE(timestamp) ORDER BY date DESC LIMIT 10
- "Unique learners" → SELECT COUNT(DISTINCT actor_id) as unique_learners FROM statements_new

RESPONSE FORMAT:
Always respond with:
1. SQL_QUERY: <executable SQL>
2. INSIGHT: <human-readable interpretation focusing on wellness impact and behavior change>

IMPORTANT GUIDELINES:
- Present unified results, not technical data sources
- If asked about "all learners" or "total activities", give the combined total
- Focus on insights and outcomes, not data origins
- Use natural language that emphasizes results and impact
- Don't break down by technical sources unless specifically asked

STYLE:
- Emphasize behavior change and wellness impact
- Use encouraging, supportive language
- Focus on actionable insights
- Present unified, user-friendly results
- Be conversational and helpful
"""

# Build conversation context
def build_conversation_context():
    """Build conversation context from recent messages"""
    if len(st.session_state.messages) < 2:
        return ""
    
    recent_messages = st.session_state.messages[-6:]  # Last 3 exchanges
    context = []
    
    for msg in recent_messages:
        if msg["role"] == "user":
            context.append(f"User: {msg['content']}")
        else:
            compressed = compress_bot_response(msg['content'])
            if compressed:
                context.append(f"Seven: {compressed}")
    
    return "\n".join(context)

# Compress bot response
def compress_bot_response(response):
    """Extract key insights from bot response"""
    lines = response.split('\n')
    insights = []
    
    for line in lines:
        if line.startswith('INSIGHT:') or 'insight' in line.lower():
            insights.append(line.strip())
        elif 'learners' in line.lower() or 'activities' in line.lower():
            insights.append(line.strip())
    
    return ' '.join(insights[:2]) if insights else ""

# Generate bot response with OpenAI
def generate_bot_response_with_openai(user_input):
    """Generate response using OpenAI API"""
    try:
        conversation_context = build_conversation_context()
        
        messages = [
            {"role": "system", "content": SYSTEM_CONTEXT},
        ]
        
        if conversation_context:
            messages.append({
                "role": "system", 
                "content": f"Previous conversation context:\n{conversation_context}\n\nBuild on this context in your response."
            })
        
        messages.append({"role": "user", "content": user_input})
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        bot_response = response.choices[0].message.content
        
        sql_query = extract_sql_from_response(bot_response)
        
        viz_data = None
        if sql_query:
            query_result = query_database(sql_query)
            if query_result and "error" not in query_result:
                viz_data = create_visualization(query_result)
        
        return {
            "response": bot_response,
            "sql_query": sql_query,
            "viz_data": viz_data
        }
        
    except Exception as e:
        return {
            "response": f"I'm having trouble connecting to my AI brain right now. Error: {str(e)}",
            "sql_query": None,
            "viz_data": None
        }

# Extract SQL from response
def extract_sql_from_response(response):
    """Extract SQL query from bot response"""
    lines = response.split('\n')
    for line in lines:
        if line.startswith('SQL_QUERY:') or line.startswith('```sql'):
            sql = line.replace('SQL_QUERY:', '').replace('```sql', '').replace('```', '').strip()
            if sql and sql.upper().startswith('SELECT'):
                return sql
    return None

# Format bot response
def format_bot_response(response):
    """Format bot response with styling"""
    formatted = response
    
    if 'SQL_QUERY:' in formatted:
        formatted = formatted.replace('SQL_QUERY:', '<div class="code-block"><strong>SQL Query:</strong><br>')
        formatted = formatted.replace('INSIGHT:', '</div><div class="code-block"><strong>💡 Insight:</strong> ')
        formatted = formatted.replace('```sql', '<div class="code-block">')
        formatted = formatted.replace('```', '</div>')
    
    return formatted

# Main function
def main():
    # Header
    st.title("🧠 Seven Analytics")
    st.markdown("Ask me about your learning analytics data")
    
    # Display messages
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f'<div class="user-message">{message["content"]}</div>', unsafe_allow_html=True)
        else:
            formatted_response = format_bot_response(message["content"])
            st.markdown(f'<div class="bot-message">{formatted_response}</div>', unsafe_allow_html=True)
            
            if "viz_data" in message and message["viz_data"]:
                render_streamlit_chart(message["viz_data"])
    
    # Input area
    st.markdown("---")
    
    col1, col2 = st.columns([6, 1])
    
    with col1:
        user_input = st.text_input(
            "Ask me about your learning analytics...",
            key="user_input",
            label_visibility="collapsed",
            placeholder="How many learners do I have?"
        )
    
    with col2:
        if st.button("🚀", key="send_button"):
            if user_input.strip():
                # Add user message
                st.session_state.messages.append({"role": "user", "content": user_input})
                
                # Generate bot response
                bot_response_data = generate_bot_response_with_openai(user_input)
                
                # Add bot message
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": bot_response_data["response"],
                    "viz_data": bot_response_data["viz_data"]
                })
                
                st.rerun()

if __name__ == "__main__":
    main()
