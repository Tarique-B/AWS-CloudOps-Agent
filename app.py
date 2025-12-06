import json
import logging
import os
import requests
import streamlit as st
from requests.exceptions import ConnectionError, Timeout

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8888")

st.set_page_config(
    page_title="AWS Assistant",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_agent_status():
    try:
        response = requests.get(f"{API_BASE_URL}/ping", timeout=2)
        if response.status_code == 200:
            return response.json()
        return {"status": "unhealthy", "model_id": "unknown", "agent_initialized": False}
    except Exception:
        return {"status": "unhealthy", "model_id": "unknown", "agent_initialized": False}

def stream_agent_response(prompt):
    try:
        response = requests.post(
            f"{API_BASE_URL}/invocations",
            json={"prompt": prompt, "stream": True},
            stream=True,
            timeout=300
        )
        
        if response.status_code != 200:
            yield f"Oops! Something went wrong. (Status: {response.status_code})"
            return

        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])
                        if 'chunk' in data:
                            yield data['chunk']
                        elif 'error' in data:
                            yield f"\n\nStream Error: {data['error']}"
                    except:
                        continue
    except Exception as e:
        yield f"Connection issue: {str(e)}"

def invoke_agent_non_streaming(prompt):
    try:
        response = requests.post(
            f"{API_BASE_URL}/invocations",
            json={"prompt": prompt, "stream": False},
            timeout=300
        )
        if response.status_code == 200:
            return response.json().get("response", "No response received.")
        return f"Error: {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        letter-spacing: -0.01em;
    }

    .stApp {
        background-color: var(--background-color);
    }

    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 8rem;
        max-width: 900px;
    }

    .hero-box {
        background-color: transparent;
        padding: 2.5rem 2rem;
        border-radius: 16px;
        color: var(--text-color);
        text-align: center;
        border: 1px solid rgba(128, 128, 128, 0.3);
        margin-bottom: 2rem;
    }
    
    .hero-title { 
        font-size: 2.2rem; 
        font-weight: 700; 
        margin: 0; 
        color: var(--text-color) !important; 
        letter-spacing: -0.02em;
    }
    
    .hero-sub { 
        opacity: 0.7; 
        font-size: 1.1rem; 
        margin-top: 0.5rem; 
        color: var(--text-color) !important; 
    }

    div[data-testid="stChatMessage"] {
        background-color: transparent;
        border: none;
        padding: 1rem 0;
    }

    div[data-testid="stChatMessage"][data-testid="user-message"] > div:first-child > div:first-child {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 12px;
        padding: 1rem 1.25rem;
        color: var(--text-color);
    }

    div[data-testid="stChatMessage"][data-testid="assistant-message"] > div:first-child > div:first-child {
        background: transparent;
        padding: 0 1rem;
        color: var(--text-color);
    }

    .stChatInput {
        background-color: transparent !important;
        padding-bottom: 1rem !important;
    }
    
    .stChatInputContainer > div {
        background-color: transparent !important;
    }
    
    .stChatInput input {
        border-radius: 20px !important;
        background-color: var(--background-color) !important;
        border: 1px solid rgba(128, 128, 128, 0.3) !important;
        color: var(--text-color) !important;
        padding: 0.5rem 1rem !important; 
    }
    
    .stChatInput button {
        border: none !important;
        background: transparent !important;
    }
    
    div[data-testid="stChatInput"] {
        border-radius: 20px !important;
        background-color: var(--background-color) !important;
        border: 1px solid rgba(128, 128, 128, 0.3) !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
        padding: 2px !important;
    }
    
    div[data-testid="stChatInput"] textarea {
        border: none !important;
        padding: 0.5rem !important;
        background-color: transparent !important;
    }
    
    div[data-testid="stChatInput"]:focus-within {
        border-color: var(--primary-color) !important;
        box-shadow: 0 0 0 1px var(--primary-color) !important;
    }

    section[data-testid="stSidebar"] {
        background-color: var(--secondary-background-color);
        border-right: 1px solid rgba(128, 128, 128, 0.1);
    }

    .streamlit-expanderHeader {
        background: linear-gradient(90deg, rgba(128, 128, 128, 0.05) 0%, rgba(128, 128, 128, 0.01) 100%);
        border-radius: 8px !important;
        border: 1px solid rgba(128, 128, 128, 0.15);
        color: var(--text-color);
        transition: border-color 0.2s, background 0.2s;
    }
    
    .streamlit-expanderHeader:hover {
        border-color: var(--primary-color);
        background: linear-gradient(90deg, rgba(var(--primary-color-rgb), 0.05) 0%, transparent 100%);
    }
    
    .streamlit-expanderContent {
        border: none;
        padding-left: 0.5rem;
        padding-top: 0.5rem;
    }

    .status-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 0;
        border-bottom: 1px solid rgba(128, 128, 128, 0.1);
        font-size: 0.9rem;
        color: var(--text-color);
    }
    
    .status-row:last-child { border-bottom: none; }

    .badge {
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .badge-neutral {
        background-color: rgba(128, 128, 128, 0.15);
        color: var(--text-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
    }
    
    .badge-active {
        background-color: rgba(34, 197, 94, 0.1);
        color: #22c55e;
        border: 1px solid rgba(34, 197, 94, 0.2);
    }

    .badge-error {
        background-color: rgba(239, 68, 68, 0.1);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.2);
    }

    .stButton > button {
        background: linear-gradient(135deg, var(--primary-color) 0%, #FF9900 100%);
        color: white !important;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        width: 100%;
    }
    
    .stButton > button:hover {
        box-shadow: 0 6px 12px rgba(0,0,0,0.2);
        transform: translateY(-1px);
        filter: brightness(1.1);
        border-color: transparent;
    }
    
    .stButton > button:active {
        transform: translateY(0);
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    footer { visibility: hidden; }
    #MainMenu { visibility: visible; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="hero-box">
        <div class="hero-title">AWS Assistant</div>
        <div class="hero-sub">Your Intelligent Cloud Companion</div>
    </div>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Hi there! I'm ready to help you manage your cloud infrastructure. What's on your mind today?"
    }]

def handle_input(input_text):
    st.session_state.messages.append({"role": "user", "content": input_text})
    
    status = get_agent_status()
    if not status.get("agent_initialized"):
        st.error("I'm having trouble connecting to the agent. Please check the backend.")
    else:
        with st.chat_message("assistant"):
            try:
                response_text = st.write_stream(stream_agent_response(input_text))
            except:
                response_text = invoke_agent_non_streaming(input_text)
                st.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})

chat_container = st.container()
with chat_container:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

if prompt := st.chat_input("Ask me to deploy resources, check logs, or analyze costs..."):
    handle_input(prompt)
    st.rerun()

with st.sidebar:
    st.header("Control Panel")
    
    with st.expander("ℹ️ About", expanded=True):
        st.markdown("""
            I'm your **AWS Assistant**, powered by **Claude 3.5 Sonnet**. 
            I can help you safely manage your AWS environment through natural language.
        """)
    
    with st.expander("⚡ Quick Start", expanded=True):
        st.markdown("Try one of these:")
        if st.button("List all S3 buckets"):
            handle_input("List all S3 buckets in my account")
            st.rerun()
        if st.button("Check running EC2 instances"):
            handle_input("Show me all running EC2 instances")
            st.rerun()
        if st.button("Analyze monthly costs"):
            handle_input("Analyze my AWS costs for the last month")
            st.rerun()

    with st.expander("🚀 Capabilities", expanded=False):
        st.markdown("""
            <div class="status-row"><span>☁️ Infrastructure</span><span class="badge badge-neutral">IaC</span></div>
            <div class="status-row"><span>🛡️ Security Audit</span><span class="badge badge-neutral">IAM</span></div>
            <div class="status-row"><span>💰 Cost Analyzer</span><span class="badge badge-neutral">FinOps</span></div>
            <div class="status-row"><span>📝 Log Analysis</span><span class="badge badge-neutral">CloudWatch</span></div>
        """, unsafe_allow_html=True)

    status = get_agent_status()
    is_healthy = status.get("status") == "healthy" and status.get("agent_initialized")
    
    gw_badge = "badge-active" if is_healthy else "badge-error"
    gw_text = "ONLINE" if is_healthy else "OFFLINE"

    with st.expander("🤖 Agent Status", expanded=False):
        st.markdown(f"""
            <div class="status-row">
                <span>Gateway</span>
                <span class="badge {gw_badge}">{gw_text}</span>
            </div>
            <div class="status-row">
                <span>Latency</span>
                <span class="badge badge-neutral">~24ms</span>
            </div>
            <div class="status-row">
                <span>Model</span>
                <span style="opacity: 0.6; font-size: 0.75rem;">Claude 3.5 Sonnet</span>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("Ping Agent"):
            st.rerun()

    st.markdown("---")
    st.caption(f"v2.3.0 • Connected to {API_BASE_URL}")
