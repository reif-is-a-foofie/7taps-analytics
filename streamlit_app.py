import streamlit as st

# Page config
st.set_page_config(
    page_title="Seven Analytics",
    page_icon="🧠",
    layout="wide"
)

# Simple test
st.title("🧠 Seven Analytics")
st.write("This is a test to see if the app renders.")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "Hi, I'm @seven, how can I help you today?"
    })

# Display messages
for message in st.session_state.messages:
    if message["role"] == "user":
        st.write(f"**You:** {message['content']}")
    else:
        st.write(f"**Seven:** {message['content']}")

# Input
user_input = st.text_input("Ask me something...")

if st.button("Send"):
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.messages.append({"role": "assistant", "content": f"You said: {user_input}"})
        st.rerun()

st.write("App is working!")
