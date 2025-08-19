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
    initial_sidebar_state="expanded"
)

# Modern CSS for clean chat interface
st.markdown("""
<style>
    /* Reset and base styles */
    * {
        box-sizing: border-box;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main container - full height, clean background */
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 0;
        margin: 0;
        min-height: 100vh;
    }
    
    /* Block container - remove default padding */
    .block-container {
        padding: 0 !important;
        max-width: none !important;
        margin: 0 !important;
    }
    
    /* Chat layout - modern flexbox design */
    .chat-layout {
        display: flex;
        flex-direction: column;
        height: 100vh;
        background: white;
        border-radius: 12px;
        margin: 20px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        overflow: hidden;
    }
    
    /* Header */
    .chat-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px 30px;
        text-align: center;
        font-size: 24px;
        font-weight: 600;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    }
    
    /* Messages container - scrollable, clean spacing */
    .messages-container {
        flex: 1;
        overflow-y: auto;
        padding: 20px 30px;
        background: #fafbfc;
        display: flex;
        flex-direction: column;
        gap: 16px;
    }
    
    /* Message bubbles - modern design with shadows */
    .message {
        display: flex;
        margin: 0;
        animation: fadeIn 0.3s ease-in;
    }
    
    .message.user {
        justify-content: flex-end;
    }
    
    .message.assistant {
        justify-content: flex-start;
    }
    
    .message.system {
        justify-content: center;
    }
    
    .message-bubble {
        max-width: 75%;
        padding: 16px 20px;
        border-radius: 20px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        word-wrap: break-word;
        line-height: 1.5;
        position: relative;
    }
    
    .message-bubble.user {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-bottom-right-radius: 6px;
    }
    
    .message-bubble.assistant {
        background: white;
        color: #2d3748;
        border: 1px solid #e2e8f0;
        border-bottom-left-radius: 6px;
    }
    
    .message-bubble.system {
        background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
        color: #744210;
        border-radius: 12px;
        font-style: italic;
        text-align: center;
        max-width: 90%;
    }
    
    /* Input area - modern, fixed bottom design */
    .input-container {
        background: white;
        padding: 20px 30px;
        border-top: 1px solid #e2e8f0;
        box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
    }
    
    .input-row {
        display: flex;
        gap: 12px;
        align-items: center;
    }
    
               /* Input field styling */
           .stTextInput > div > div > input {
               border: 2px solid #e2e8f0 !important;
               border-radius: 25px !important;
               padding: 16px 24px !important;
               font-size: 16px !important;
               background: white !important;
               color: #2d3748 !important;
               transition: all 0.3s ease !important;
               box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
           }
           
           .stTextInput > div > div > input:focus {
               border-color: #667eea !important;
               background: white !important;
               color: #2d3748 !important;
               box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15) !important;
               outline: none !important;
           }
           
           .stTextInput > div > div > input::placeholder {
               color: #a0aec0 !important;
               font-style: italic !important;
           }
    
    /* Send button styling */
    .stButton > button {
        border-radius: 50% !important;
        width: 50px !important;
        height: 50px !important;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        border: none !important;
        color: white !important;
        font-size: 20px !important;
        min-width: 50px !important;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3) !important;
        transition: all 0.3s ease !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4) !important;
    }
    
    /* Code blocks */
    .code-block {
        background: #2d3748;
        color: #e2e8f0;
        border-radius: 8px;
        padding: 16px;
        margin: 12px 0;
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        font-size: 14px;
        overflow-x: auto;
        border-left: 4px solid #667eea;
    }
    
    /* Chart containers */
    .chart-container {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        margin: 16px 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }
    
    /* Animations */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Scrollbar styling */
    .messages-container::-webkit-scrollbar {
        width: 6px;
    }
    
    .messages-container::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 3px;
    }
    
    .messages-container::-webkit-scrollbar-thumb {
        background: #c1c1c1;
        border-radius: 3px;
    }
    
    .messages-container::-webkit-scrollbar-thumb:hover {
        background: #a8a8a8;
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .chat-layout {
            margin: 10px;
            border-radius: 8px;
        }
        
        .chat-header {
            padding: 15px 20px;
            font-size: 20px;
        }
        
        .messages-container {
            padding: 15px 20px;
        }
        
        .input-container {
            padding: 15px 20px;
        }
        
        .message-bubble {
            max-width: 85%;
        }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Add introduction message
    st.session_state.messages.append({
            "role": "system", 
            "content": """Hi, I'm @seven, your AI analytics assistant!

I can help you explore your learning data, create visualizations, and answer questions about engagement patterns. 

**Quick Commands:**
• "Show me engagement trends"
• "Which lessons are most popular?"
• "How many users completed the course?"
• "Create a visualization of user progress"

What would you like to know about your learning analytics?"""
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
            
        # Convert to DataFrame for Streamlit
        import pandas as pd
        
        # Extract headers and data
        headers = data[0]
        rows = data[1:]
        
        if not rows:
            return
            
        df = pd.DataFrame(rows, columns=headers)
        
        # Render appropriate chart
        if chart_type == "bar":
            st.bar_chart(df.set_index(headers[0]))
        elif chart_type == "line":
            st.line_chart(df.set_index(headers[0]))
        elif chart_type == "area":
            st.area_chart(df.set_index(headers[0]))
        else:
            st.dataframe(df)
            
    except Exception as e:
        st.error(f"Chart rendering error: {str(e)}")

# OpenAI integration
def generate_bot_response(user_message, conversation_history):
    """Generate response using OpenAI"""
    try:
        # Build conversation context
        messages = [
            {
                "role": "system",
                "content": """You are Seven, an AI analytics assistant for 7taps learning data. You help users explore their learning analytics through natural conversation.

Key capabilities:
- Query learning data (633 statements, 21 learners, 10 lessons)
- Create visualizations and charts
- Analyze engagement patterns
- Provide insights about learner behavior

Data sources:
- statements_new: Main learning activity data
- context_extensions_new: Metadata (lesson numbers, card types, etc.)
- results_new: Learner responses and outcomes

Common queries you can help with:
- Learner engagement by lesson
- Card type popularity
- Learner progression through course
- Recent activity trends

Always be helpful, conversational, and provide actionable insights. When appropriate, suggest visualizations or follow-up questions."""
            }
        ]
        
        # Add conversation history (compressed)
        if conversation_history:
            compressed_history = f"Previous conversation context: {conversation_history[-3:] if len(conversation_history) > 3 else conversation_history}"
            messages.append({"role": "user", "content": compressed_history})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Generate response using new OpenAI API
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"I'm having trouble connecting to my AI brain right now. Error: {str(e)}"

# Main chat interface
def main():
    # Sidebar with navigation and resources
    with st.sidebar:
        st.title("Seven Analytics")
        st.markdown("---")
        
        # Quick Links Section
        st.subheader("Quick Links")
        
        # API Documentation
        if st.button("API Docs", help="View API documentation"):
            st.markdown("**API Documentation:**")
            st.markdown("- [Swagger UI](https://seventaps-analytics.herokuapp.com/docs)")
            st.markdown("- [Data Access Guide](https://seventaps-analytics.herokuapp.com/api/data/guide)")
        
        if st.button("Database", help="View database schema and tables"):
            st.markdown("**Database Resources:**")
            st.markdown("- [Schema Overview](https://seventaps-analytics.herokuapp.com/api/data/schema)")
            st.markdown("- [Sample Queries](https://seventaps-analytics.herokuapp.com/api/data/samples)")
        
        st.markdown("---")
        
        # Data Status
        st.subheader("Data Status")
        try:
            # Get data status from API
            response = requests.get("https://seventaps-analytics.herokuapp.com/api/data/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                st.success(f"Connected to database")
                st.info(f"{data.get('total_statements', 0)} statements")
                st.info(f"{data.get('unique_users', 0)} users")
                st.info(f"{data.get('total_lessons', 0)} lessons")
            else:
                st.error("Cannot connect to database")
        except:
            st.warning("Database status unavailable")
        
        st.markdown("---")
        
        # Useful Commands
        st.subheader("Try These Commands")
        commands = [
            "Show me engagement trends",
            "Which lessons are most popular?",
            "How many users completed the course?",
            "What's the average time per lesson?",
            "Show me recent activity",
            "Create a visualization of user progress"
        ]
        
        for cmd in commands:
            if st.button(cmd, key=f"cmd_{cmd[:20]}"):
                st.session_state.suggested_query = cmd
        
        st.markdown("---")
        
        # System Info
        st.subheader("System Info")
        st.info("**Backend:** FastAPI on Heroku")
        st.info("**Database:** PostgreSQL")
        st.info("**Chat:** OpenAI GPT-3.5")
        st.info("**UI:** Streamlit")
        
        # External Links
        st.markdown("---")
        st.subheader("External Links")
        st.markdown("- [Main Analytics App](https://seventaps-analytics.herokuapp.com/)")
        st.markdown("- [Admin Dashboard](https://seventaps-analytics.herokuapp.com/ui/admin)")
        st.markdown("- [Data Access Guide](https://seventaps-analytics.herokuapp.com/api/data/guide)")
    
    # Main chat area - full width
    # Chat layout container
    st.markdown('<div class="chat-layout">', unsafe_allow_html=True)
    
        # Header
    st.markdown('<div class="chat-header">Seven Analytics</div>', unsafe_allow_html=True)
    
    # Messages container
    st.markdown('<div class="messages-container">', unsafe_allow_html=True)
    
    # Display messages
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]
        
        # Determine message class
        if role == "user":
            message_class = "user"
        elif role == "assistant":
            message_class = "assistant"
        else:
            message_class = "system"
        
        # Render message
        st.markdown(f'''
        <div class="message {message_class}">
            <div class="message-bubble {message_class}">
                {content}
            </div>
        </div>
        ''', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # Close messages container
    
    # Input container
    st.markdown('<div class="input-container">', unsafe_allow_html=True)
    st.markdown('<div class="input-row">', unsafe_allow_html=True)
    
    # User input
    user_input = st.text_input(
        "Type your message...",
        key="user_input",
        placeholder="Ask me about your learning analytics...",
        label_visibility="collapsed"
    )
    
    # Send button
    if st.button("➤", key="send_button"):
        if user_input.strip():
            # Add user message
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # Generate bot response
            conversation_history = [msg["content"] for msg in st.session_state.messages[-5:]]
            bot_response = generate_bot_response(user_input, conversation_history)
            
            # Add bot response
            st.session_state.messages.append({"role": "assistant", "content": bot_response})
            
            # Rerun to update display
            st.rerun()
    
        st.markdown('</div>', unsafe_allow_html=True)  # Close input row
        st.markdown('</div>', unsafe_allow_html=True)  # Close input container
        st.markdown('</div>', unsafe_allow_html=True)  # Close chat layout
    
    # Handle suggested queries
    if hasattr(st.session_state, 'suggested_query'):
        if st.session_state.suggested_query:
            user_input = st.session_state.suggested_query
            st.session_state.suggested_query = None
            
            # Add user message
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # Generate bot response
            conversation_history = [msg["content"] for msg in st.session_state.messages[-5:]]
            bot_response = generate_bot_response(user_input, conversation_history)
            
            # Add bot response
            st.session_state.messages.append({"role": "assistant", "content": bot_response})
            
            # Rerun to update display
            st.rerun()

if __name__ == "__main__":
    main()
