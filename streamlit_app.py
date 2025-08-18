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

# Custom CSS for beautiful ChatGPT-style interface
st.markdown("""
<style>
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main container */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
        padding: 0;
    }
    
    /* Chat container */
    .chat-container {
        max-width: 800px;
        margin: 0 auto;
        background: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
        overflow: hidden;
        height: 90vh;
        display: flex;
        flex-direction: column;
    }
    
    /* Header */
    .chat-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        text-align: center;
        font-size: 24px;
        font-weight: bold;
    }
    
    /* Messages area */
    .messages-area {
        flex: 1;
        overflow-y: auto;
        padding: 20px;
        background: #f8f9fa;
    }
    
    /* Message bubbles */
    .message {
        margin-bottom: 20px;
        display: flex;
        align-items: flex-start;
    }
    
    .user-message {
        justify-content: flex-end;
    }
    
    .bot-message {
        justify-content: flex-start;
    }
    
    .message-content {
        max-width: 70%;
        padding: 15px 20px;
        border-radius: 20px;
        font-size: 16px;
        line-height: 1.5;
    }
    
    .user-message .message-content {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-bottom-right-radius: 5px;
    }
    
    .bot-message .message-content {
        background: white;
        color: #333;
        border: 1px solid #e1e5e9;
        border-bottom-left-radius: 5px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    }
    
    /* Input area */
    .input-area {
        padding: 20px;
        background: white;
        border-top: 1px solid #e1e5e9;
    }
    
    .input-container {
        display: flex;
        gap: 10px;
        align-items: center;
    }
    
    .stTextInput > div > div > input {
        border-radius: 25px;
        border: 2px solid #e1e5e9;
        padding: 15px 20px;
        font-size: 16px;
        background: #f8f9fa;
        transition: all 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        background: white;
    }
    
    .stButton > button {
        border-radius: 50%;
        width: 50px;
        height: 50px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        color: white;
        font-size: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* Code blocks */
    .code-block {
        background: #f6f8fa;
        border: 1px solid #e1e4e8;
        border-radius: 6px;
        padding: 16px;
        margin: 10px 0;
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        font-size: 14px;
        overflow-x: auto;
        color: #24292e;
    }
    
    /* Insight blocks */
    .insight-block {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        font-weight: 500;
    }
    
    /* Charts */
    .chart-container {
        background: white;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    }
    
    /* Loading animation */
    .typing-indicator {
        display: flex;
        align-items: center;
        gap: 5px;
        padding: 15px 20px;
        background: white;
        border-radius: 20px;
        border-bottom-left-radius: 5px;
        max-width: 70%;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    }
    
    .typing-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #667eea;
        animation: typing 1.4s infinite ease-in-out;
    }
    
    .typing-dot:nth-child(1) { animation-delay: -0.32s; }
    .typing-dot:nth-child(2) { animation-delay: -0.16s; }
    
    @keyframes typing {
        0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
        40% { transform: scale(1); opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Database connection function
def get_db_connection():
    """Get database connection via API"""
    return None  # We'll use API calls instead

# Query database function
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

# Get data overview
def get_data_overview():
    """Get data overview via API"""
    try:
        response = requests.get(
            "https://seventaps-analytics-5135b3a0701a.herokuapp.com/api/ui/nlp-status",
            timeout=10
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
        columns = viz_data["columns"]
        
        if not data or len(data) < 2:
            return
            
        # Convert to DataFrame format
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
        st.error(f"Chart rendering error: {str(e)}")

# System context for the bot
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

CONVERSATION CONTEXT:
- Build on previous conversations and insights
- Reference earlier findings when relevant
- Provide deeper analysis based on what we've already discovered
- Connect new insights to previous observations

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
- Build on previous analysis when relevant
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
            # Compress bot responses to key insights
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
        # Build conversation context
        conversation_context = build_conversation_context()
        
        # Prepare messages
        messages = [
            {"role": "system", "content": SYSTEM_CONTEXT},
        ]
        
        # Add conversation context if available
        if conversation_context:
            messages.append({
                "role": "system", 
                "content": f"Previous conversation context:\n{conversation_context}\n\nBuild on this context in your response."
            })
        
        messages.append({"role": "user", "content": user_input})
        
        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        bot_response = response.choices[0].message.content
        
        # Extract SQL query
        sql_query = extract_sql_from_response(bot_response)
        
        # Execute query if SQL found
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
    
    # Format SQL blocks
    if 'SQL_QUERY:' in formatted:
        formatted = formatted.replace('SQL_QUERY:', '<div class="code-block"><strong>SQL Query:</strong><br>')
        formatted = formatted.replace('INSIGHT:', '</div><div class="insight-block"><strong>💡 Insight:</strong> ')
        formatted = formatted.replace('```sql', '<div class="code-block">')
        formatted = formatted.replace('```', '</div>')
    
    return formatted

# Main function
def main():
    # Header
    st.markdown("""
    <div class="chat-header">
        🧠 Seven Analytics
    </div>
    """, unsafe_allow_html=True)
    
    # Chat container
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Messages area
    st.markdown('<div class="messages-area">', unsafe_allow_html=True)
    
    # Display messages
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f"""
            <div class="message user-message">
                <div class="message-content">{message["content"]}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Bot message
            formatted_response = format_bot_response(message["content"])
            st.markdown(f"""
            <div class="message bot-message">
                <div class="message-content">{formatted_response}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Show visualization if available
            if "viz_data" in message and message["viz_data"]:
                render_streamlit_chart(message["viz_data"])
    
    # Show typing indicator if processing
    if "processing" in st.session_state and st.session_state.processing:
        st.markdown("""
        <div class="message bot-message">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Input area
    st.markdown('<div class="input-area">', unsafe_allow_html=True)
    
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
                
                # Set processing flag
                st.session_state.processing = True
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Process user input if processing flag is set
    if "processing" in st.session_state and st.session_state.processing:
        # Generate bot response
        bot_response_data = generate_bot_response_with_openai(user_input)
        
        # Add bot message
        st.session_state.messages.append({
            "role": "assistant", 
            "content": bot_response_data["response"],
            "viz_data": bot_response_data["viz_data"]
        })
        
        # Clear processing flag and input
        del st.session_state.processing
        st.session_state.user_input = ""
        st.rerun()

if __name__ == "__main__":
    main()
