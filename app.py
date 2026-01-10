import json
import logging
import os
import requests
import streamlit as st
from requests.exceptions import ConnectionError, Timeout
import boto3
import uuid

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
AGENTCORE_RUNTIME_ARN = os.getenv("AGENTCORE_RUNTIME_ARN")
AGENT_RUNTIME = "Agentcore" if AGENTCORE_RUNTIME_ARN else "local"
STRANDS_AGENT_VERSION = os.getenv("STRANDS_AGENT_VERSION", "v1.0.0")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "unknown")

st.set_page_config(
    page_title="AWS CloudOps Assistant",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_agent_status():
    if AGENT_RUNTIME == "Agentcore":
        try:
            return {"status": "healthy", "model_id": "unknown", "agent_initialized": True}
        except Exception:
            return {"status": "unhealthy", "model_id": "unknown", "agent_initialized": False}
    else:
        try:
            response = requests.get(f"{API_BASE_URL}/ping", timeout=2)
            if response.status_code == 200:
                return response.json()
            return {"status": "unhealthy", "model_id": "unknown", "agent_initialized": False}
        except Exception:
            return {"status": "unhealthy", "model_id": "unknown", "agent_initialized": False}

def stream_agent_response(prompt):
    if AGENT_RUNTIME == "Agentcore":
        try:
            client = boto3.client('bedrock-agentcore', region_name=os.getenv("AWS_REGION", "us-east-1"))
            payload = json.dumps({"prompt": prompt})
            runtime_session_id = str(uuid.uuid4())
            
            response = client.invoke_agent_runtime(
                agentRuntimeArn=AGENTCORE_RUNTIME_ARN,
                runtimeSessionId=runtime_session_id,
                payload=payload,
                qualifier="DEFAULT"
            )
            
            # Process the response stream
            for line in response["response"].iter_lines():
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
            yield f"Agentcore runtime error: {str(e)}"
    else:
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
    if AGENT_RUNTIME == "Agentcore":
        try:
            client = boto3.client('bedrock-agentcore', region_name=os.getenv("AWS_REGION", "us-east-1"))
            payload = json.dumps({"prompt": prompt})
            runtime_session_id = str(uuid.uuid4())
            
            response = client.invoke_agent_runtime(
                agentRuntimeArn=AGENTCORE_RUNTIME_ARN,
                runtimeSessionId=runtime_session_id,
                payload=payload,
                qualifier="DEFAULT"
            )
            
            response_data = json.loads(response["response"].read())
            return response_data.get("response", "No response received.")
        except Exception as e:
            return f"Agentcore runtime error: {str(e)}"
    else:
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

def get_model_name(model_id):
    if not model_id or model_id == "unknown":
        return "Unknown"
    
    try:
        parts = model_id.split(".")
        if len(parts) >= 3:
            model_part = parts[2]
            model_parts = model_part.split("-")
            
            if len(model_parts) >= 3:
                name = model_parts[0].capitalize()
                version = f"{model_parts[1]}.{model_parts[2]}"
                variant = model_parts[3].capitalize() if len(model_parts) > 3 else ""
                
                if variant:
                    return f"{name} {version} {variant}"
                else:
                    return f"{name} {version}"
        
        return model_id.split(".")[-1].split(":")[0] if "." in model_id else model_id
    except Exception:
        return model_id            

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
        border: 1px solid rgba(236, 72, 153, 0.15);
        margin-bottom: 2rem;
    }
    
    .hero-title { 
        font-size: 2.2rem; 
        font-weight: 700; 
        margin: 0; 
        background: linear-gradient(135deg, #22C55E 0%, #10B981 15%, #EC4899 35%, #E91E63 50%, #DB2777 65%, #A855F7 85%, #9333EA 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -0.02em;
        background-size: 200% 200%;
        animation: gradient-shift 3s ease infinite;
    }

    @keyframes gradient-shift {
        0%, 100% {
            background-position: 0% 50%;
        }
        50% {
            background-position: 100% 50%;
        }
    }
    
    .hero-sub { 
        opacity: 0.7; 
        font-size: 1.2rem; 
        margin-top: 0.75rem; 
        line-height: 1.6;
        color: var(--text-color) !important; 
    }

    div[data-testid="stChatMessage"] {
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin-bottom: 1rem !important;
        scroll-margin: 0 !important;
    }

    div[data-testid="stChatMessage"] > div {
        display: flex !important;
        align-items: center !important;
        gap: 1rem !important;
    }

    div[data-testid="stChatMessage"] > div > div:first-child {
        flex-shrink: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        visibility: visible !important;
    }

    div[data-testid="stChatMessage"] > div > div:first-child img {
        display: block !important;
        visibility: visible !important;
        width: auto !important;
        height: auto !important;
        margin: 0 !important;
    }

    div[data-testid="stChatMessage"] > div > div:last-child {
        background-color: transparent !important;
        border: 1px solid rgba(236, 72, 153, 0.15) !important;
        border-radius: 12px !important;
        padding: 0.875rem 1.125rem !important;
        color: var(--text-color) !important;
        margin: 0 !important;
        flex: 1 !important;
    }

    div[data-testid="stChatMessage"] .stMarkdown {
        color: var(--text-color) !important;
        font-size: 1.125rem;
        line-height: 1.75;
        background-color: transparent !important;
    }

    div[data-testid="stChatMessage"] .stMarkdown > *:first-child {
        margin-top: 0;
    }

    div[data-testid="stChatMessage"] .stMarkdown > *:last-child {
        margin-bottom: 0;
    }

    div[data-testid="stChatMessage"] .stMarkdown p {
        margin: 0.5rem 0;
        line-height: 1.7;
    }

    div[data-testid="stChatMessage"] .stMarkdown p:first-child {
        margin-top: 0;
    }

    div[data-testid="stChatMessage"] .stMarkdown p:last-child {
        margin-bottom: 0;
    }

    div[data-testid="stChatMessage"] .stMarkdown code {
        background-color: rgba(128, 128, 128, 0.15);
        padding: 0.3rem 0.5rem;
        border-radius: 4px;
        font-size: 0.95em;
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'source-code-pro', monospace;
    }

    div[data-testid="stChatMessage"] .stMarkdown pre {
        background-color: rgba(128, 128, 128, 0.1);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 8px;
        padding: 0.875rem;
        overflow-x: auto;
        margin: 0.75rem 0;
        font-size: 0.9rem;
        line-height: 1.5;
    }

    div[data-testid="stChatMessage"] .stMarkdown pre code {
        background-color: transparent;
        padding: 0;
    }

    div[data-testid="stChatMessage"] .stMarkdown ul,
    div[data-testid="stChatMessage"] .stMarkdown ol {
        margin: 0.75rem 0;
        padding-left: 1.5rem;
        line-height: 1.8;
    }

    div[data-testid="stChatMessage"] .stMarkdown ul li,
    div[data-testid="stChatMessage"] .stMarkdown ol li {
        margin: 0.5rem 0;
    }

    div[data-testid="stChatMessage"] .stMarkdown h1 {
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        color: var(--text-color);
        font-size: 1.75rem;
        line-height: 1.4;
        font-weight: 700;
    }

    div[data-testid="stChatMessage"] .stMarkdown h2 {
        margin-top: 1.25rem;
        margin-bottom: 0.75rem;
        color: var(--text-color);
        font-size: 1.5rem;
        line-height: 1.4;
        font-weight: 600;
    }

    div[data-testid="stChatMessage"] .stMarkdown h3 {
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        color: var(--text-color);
        font-size: 1.25rem;
        line-height: 1.5;
        font-weight: 600;
    }

    div[data-testid="stChatMessage"] .stMarkdown blockquote {
        border-left: 3px solid rgba(128, 128, 128, 0.3);
        padding-left: 1rem;
        margin: 1rem 0;
        color: var(--text-color);
        opacity: 0.9;
        line-height: 1.7;
    }

    div[data-testid="stChatMessage"] .stMarkdown table {
        border-collapse: collapse;
        width: 100%;
        margin: 1rem 0;
        font-size: 0.95rem;
    }

    div[data-testid="stChatMessage"] .stMarkdown table th,
    div[data-testid="stChatMessage"] .stMarkdown table td {
        padding: 0.75rem;
        line-height: 1.6;
    }

    div[data-testid="stChatMessage"] .stMarkdown table th,
    div[data-testid="stChatMessage"] .stMarkdown table td {
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 0.5rem;
    }

    div[data-testid="stChatMessage"] .stMarkdown table th {
        background-color: rgba(128, 128, 128, 0.1);
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
        border: 2px solid transparent !important;
        box-shadow: none !important;
        padding: 0 !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }

    div[data-testid="stChatInput"],
    div[data-testid="stChatInput"] * {
        border-color: rgba(128, 128, 128, 0.3) !important;
    }

    div[data-testid="stChatInput"]::before,
    div[data-testid="stChatInput"]::after {
        display: none !important;
    }
    
    div[data-testid="stChatInput"] textarea {
        border: none !important;
        padding: 0.5rem !important;
        background-color: transparent !important;
        outline: none !important;
    }

    div[data-testid="stChatInput"] textarea:focus {
        outline: none !important;
        border: none !important;
        box-shadow: none !important;
    }

    div[data-testid="stChatInput"] textarea:focus-visible {
        outline: none !important;
        border: none !important;
        box-shadow: none !important;
    }
    
    div[data-testid="stChatInput"]:focus-within {
        border: 2px solid rgba(236, 72, 153, 0.4) !important;
        border-radius: 20px !important;
        box-shadow: 0 0 0 2px rgba(236, 72, 153, 0.1), 0 0 8px rgba(236, 72, 153, 0.15) !important;
        outline: none !important;
    }

    div[data-testid="stChatInput"]:focus-within,
    div[data-testid="stChatInput"]:focus-within * {
        border-color: #A855F7 !important;
        outline: none !important;
    }

    div[data-testid="stChatInput"]:focus-within textarea {
        border: none !important;
    }

    div[data-testid="stChatInput"] *:focus {
        outline: none !important;
        box-shadow: none !important;
        border: none !important;
    }

    div[data-testid="stChatInput"] *:focus-visible {
        outline: none !important;
        box-shadow: none !important;
        border: none !important;
    }

    div[data-testid="stChatInput"] input:focus,
    div[data-testid="stChatInput"] textarea:focus,
    div[data-testid="stChatInput"] input:focus-visible,
    div[data-testid="stChatInput"] textarea:focus-visible {
        outline: none !important;
        border: none !important;
        box-shadow: none !important;
    }

    div[data-testid="stChatInput"],
    div[data-testid="stChatInput"] *,
    div[data-testid="stChatInput"]:focus-within,
    div[data-testid="stChatInput"]:focus-within * {
        border-color: rgba(128, 128, 128, 0.3) !important;
        outline-color: rgba(128, 128, 128, 0.3) !important;
    }

    div[data-testid="stChatInput"] [style*="red"],
    div[data-testid="stChatInput"] [style*="Red"],
    div[data-testid="stChatInput"] [style*="RED"],
    div[data-testid="stChatInput"] [style*="#ff"],
    div[data-testid="stChatInput"] [style*="#FF"],
    div[data-testid="stChatInput"] [style*="rgb(255"],
    div[data-testid="stChatInput"] [style*="rgba(255"] {
        border-color: rgba(128, 128, 128, 0.3) !important;
    }

    div[data-testid="stChatInput"],
    div[data-testid="stChatInput"] > *,
    div[data-testid="stChatInput"] > * > * {
        border-left-color: rgba(128, 128, 128, 0.3) !important;
        border-right-color: rgba(128, 128, 128, 0.3) !important;
        border-top-color: rgba(128, 128, 128, 0.3) !important;
        border-bottom-color: rgba(128, 128, 128, 0.3) !important;
    }
    
    [data-testid="stAppViewContainer"] {
        overflow-anchor: none !important;
    }
    
    [data-testid="stVerticalBlock"] {
        scroll-behavior: auto !important;
        overflow-anchor: none !important;
    }
    
    .main .block-container {
        scroll-behavior: auto !important;
        overflow-anchor: none !important;
    }
    
    section[data-testid="stMain"] {
        overflow-anchor: none !important;
    }

    section[data-testid="stSidebar"] {
        background-color: var(--secondary-background-color);
        border-right: 1px solid rgba(128, 128, 128, 0.1);
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] [data-baseweb="heading"],
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        background: linear-gradient(135deg, #22C55E 0%, #10B981 15%, #EC4899 35%, #E91E63 50%, #DB2777 65%, #A855F7 85%, #9333EA 100%) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        background-clip: text !important;
        background-size: 200% 200% !important;
        animation: gradient-shift 3s ease infinite !important;
        color: transparent !important;
    }

    .streamlit-expanderHeader {
        background: rgba(236, 72, 153, 0.04) !important;
        border-radius: 8px !important;
        border: 1px solid rgba(236, 72, 153, 0.12) !important;
        color: var(--text-color) !important;
        transition: all 0.2s ease !important;
        padding: 0.75rem 1rem !important;
        margin-bottom: 0.5rem !important;
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        gap: 0.5rem !important;
    }

    .streamlit-expanderHeader::before {
        content: '▶' !important;
        font-size: 0.7rem !important;
        color: rgba(236, 72, 153, 0.6) !important;
        transition: transform 0.2s ease !important;
        margin-right: 0.25rem !important;
    }

    .streamlit-expanderHeader[aria-expanded="true"]::before {
        transform: rotate(90deg) !important;
    }
    
    .streamlit-expanderHeader:hover {
        border-color: rgba(236, 72, 153, 0.2) !important;
        background: rgba(236, 72, 153, 0.06) !important;
        transform: translateX(2px) !important;
    }
    
    .streamlit-expanderContent {
        border: none !important;
        padding: 0.5rem !important;
        background: transparent !important;
        border-radius: 8px !important;
        margin-top: 0.5rem !important;
    }

    .streamlit-expanderHeader[aria-expanded="true"] {
        background: rgba(236, 72, 153, 0.06) !important;
        border-color: rgba(236, 72, 153, 0.18) !important;
    }

    .status-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        font-size: 0.9rem;
        color: rgba(236, 72, 153, 0.7);
        background: rgba(236, 72, 153, 0.04);
        margin-bottom: 0.5rem;
        border: 1px solid rgba(236, 72, 153, 0.12);
    }
    
    .streamlit-expanderContent .status-row:last-of-type {
        margin-bottom: 0.5rem;
    }

    .status-row .badge-active {
        background: rgba(34, 197, 94, 0.2);
        color: #22c55e;
    }

    .status-row:has(.badge-active) {
        background: rgba(34, 197, 94, 0.1);
        color: #22c55e;
        border-color: rgba(34, 197, 94, 0.2);
    }

    .status-row:has(.badge-error) {
        background: rgba(239, 68, 68, 0.1);
        color: #ef4444;
        border-color: rgba(239, 68, 68, 0.2);
    }

    .badge {
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .badge-neutral {
        background-color: rgba(236, 72, 153, 0.1);
        color: rgba(236, 72, 153, 0.8);
        border: 1px solid rgba(236, 72, 153, 0.2);
    }
    
    .badge-active {
        background-color: rgba(34, 197, 94, 0.15);
        color: #22c55e;
        border: 1px solid rgba(34, 197, 94, 0.2);
    }

    .badge-error {
        background-color: rgba(239, 68, 68, 0.15);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.2);
    }

    @keyframes thinking-dots {
        0% { content: "."; }
        33% { content: ".."; }
        66%, 100% { content: "..."; }
    }

    @keyframes pulse-glow {
        0%, 100% {
            opacity: 0.6;
            transform: scale(1);
        }
        50% {
            opacity: 1;
            transform: scale(1.05);
        }
    }

    @keyframes spin {
        from {
            transform: rotate(0deg);
        }
        to {
            transform: rotate(360deg);
        }
    }

    .thinking-dots {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        color: var(--text-color);
        opacity: 0.8;
        font-size: 1rem;
    }

    .thinking-dots::before {
        content: '';
        width: 16px;
        height: 16px;
        border: 2px solid rgba(19, 124, 189, 0.3);
        border-top-color: #1f77b4;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
        display: inline-block;
    }

    .thinking-dots::after {
        content: "...";
        animation: thinking-dots 1.5s steps(3, end) infinite;
    }

    .loading-container {
        display: flex !important;
        align-items: center !important;
        gap: 0.75rem !important;
        padding: 1rem 1.25rem !important;
        background: rgba(236, 72, 153, 0.04) !important;
        border: 1px solid rgba(236, 72, 153, 0.15) !important;
        border-radius: 16px !important;
        margin: 0 !important;
        min-height: 60px !important;
        width: 100% !important;
    }

    .loading-spinner {
        width: 20px !important;
        height: 20px !important;
        border: 3px solid rgba(236, 72, 153, 0.2) !important;
        border-top-color: rgba(236, 72, 153, 0.7) !important;
        border-radius: 50% !important;
        animation: spin 0.8s linear infinite !important;
        flex-shrink: 0 !important;
    }

    .loading-text {
        background: linear-gradient(135deg, #22C55E 0%, #10B981 15%, #EC4899 35%, #E91E63 50%, #DB2777 65%, #A855F7 85%, #9333EA 100%) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        background-clip: text !important;
        background-size: 200% 200% !important;
        animation: gradient-shift 3s ease infinite !important;
        font-size: 0.95rem !important;
        font-weight: 500 !important;
    }

    .loading-dots::after {
        content: '...';
        animation: loading-dots 1.4s steps(4, end) infinite;
        display: inline-block;
        width: 1.5em;
        text-align: left;
    }

    @keyframes loading-dots {
        0% { content: ''; }
        25% { content: '.'; }
        50% { content: '..'; }
        75%, 100% { content: '...'; }
    }

    .stButton > button {
        background: rgba(236, 72, 153, 0.05) !important;
        color: rgba(236, 72, 153, 0.8) !important;
        border: 1px solid rgba(236, 72, 153, 0.15) !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
        box-shadow: none !important;
        width: 100% !important;
    }
    
    .stButton > button:hover {
        background: rgba(236, 72, 153, 0.08) !important;
        border-color: rgba(236, 72, 153, 0.25) !important;
        transform: translateY(-1px) !important;
        color: rgba(219, 39, 119, 0.9) !important;
        box-shadow: 0 2px 4px rgba(236, 72, 153, 0.1) !important;
    }
    
    .stButton > button:active {
        transform: translateY(0) !important;
        background: rgba(236, 72, 153, 0.06) !important;
    }

    footer { visibility: hidden; }
    #MainMenu { visibility: visible; }
    </style>
    <script>
    (function() {
        let lastScrollTop = 0;
        let isUserScrolling = false;
        let scrollTimeout;
        let preventAutoScroll = false;
        
        function saveScrollPosition() {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            sessionStorage.setItem('streamlitScrollPosition', scrollTop);
            lastScrollTop = scrollTop;
        }
        
        window.addEventListener('scroll', function() {
            const currentScroll = window.pageYOffset || document.documentElement.scrollTop;
            const scrollDiff = Math.abs(currentScroll - lastScrollTop);
            
            if (scrollDiff > 5) {
                isUserScrolling = true;
                preventAutoScroll = true;
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(function() {
                    isUserScrolling = false;
                    preventAutoScroll = false;
                }, 500);
                saveScrollPosition();
            }
            lastScrollTop = currentScroll;
        }, { passive: true });
        
        const restoreScroll = function() {
            if (preventAutoScroll || isUserScrolling) {
                return;
            }
            const savedPosition = sessionStorage.getItem('streamlitScrollPosition');
            if (savedPosition) {
                const pos = parseInt(savedPosition);
                const currentPos = window.pageYOffset || document.documentElement.scrollTop;
                if (Math.abs(pos - currentPos) > 10) {
                    window.scrollTo({
                        top: pos,
                        behavior: 'auto'
                    });
                }
            }
        };
        
        window.addEventListener('load', restoreScroll);
        
        const observer = new MutationObserver(function() {
            if (!preventAutoScroll && !isUserScrolling) {
                setTimeout(restoreScroll, 10);
            }
        });
        
        if (document.body) {
            observer.observe(document.body, {
                childList: true,
                subtree: true,
                attributes: false
            });
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            if (document.body) {
                observer.observe(document.body, {
                    childList: true,
                    subtree: true,
                    attributes: false
                });
            }
        });

        function markAgentStatusExpander() {
            const headers = document.querySelectorAll('.streamlit-expanderHeader');
            headers.forEach(header => {
                if (header.textContent.includes('🤖') || header.textContent.includes('Agent Status')) {
                    header.classList.add('agent-status-header');
                }
            });
        }

        function markStatusRows() {
            const statusRows = document.querySelectorAll('.status-row');
            statusRows.forEach(row => {
                const badge = row.querySelector('.badge-active');
                if (badge) {
                    row.style.background = 'rgba(20, 83, 45, 0.4)';
                    row.style.color = '#4ade80';
                    row.style.borderColor = 'rgba(34, 197, 94, 0.2)';
                }
            });
        }

        function applySidebarHeaderGradient() {
            const sidebar = document.querySelector('section[data-testid="stSidebar"]');
            if (sidebar) {
                const headers = sidebar.querySelectorAll('h1, h2, h3, [data-baseweb="heading"]');
                headers.forEach(header => {
                    if (header.textContent.includes('Control Panel')) {
                        header.style.background = 'linear-gradient(135deg, #22C55E 0%, #10B981 15%, #EC4899 35%, #E91E63 50%, #DB2777 65%, #A855F7 85%, #9333EA 100%)';
                        header.style.webkitBackgroundClip = 'text';
                        header.style.webkitTextFillColor = 'transparent';
                        header.style.backgroundClip = 'text';
                        header.style.backgroundSize = '200% 200%';
                        header.style.animation = 'gradient-shift 3s ease infinite';
                        header.style.color = 'transparent';
                    }
                });
            }
        }

        markAgentStatusExpander();
        markStatusRows();
        applySidebarHeaderGradient();
        setInterval(() => {
            markAgentStatusExpander();
            markStatusRows();
            applySidebarHeaderGradient();
        }, 500);
    })();
    </script>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="hero-box">
        <div class="hero-title">AWS CloudOps Assistant</div>
        <div class="hero-sub">Your Intelligent CloudOps Companion</div>
    </div>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Hi there! I'm ready to help you manage your cloud infrastructure. What's on your mind today?"
    }]

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

if "processing" not in st.session_state:
    st.session_state.processing = False

if "pending_user_input" not in st.session_state:
    st.session_state.pending_user_input = None

def process_user_input(input_text):
    st.session_state.messages.append({"role": "user", "content": input_text})
    st.session_state.messages.append({"role": "assistant", "content": "LOADING"})
    if "processing" not in st.session_state:
        st.session_state.processing = False
    if "pending_user_input" not in st.session_state:
        st.session_state.pending_user_input = None
    st.session_state.processing = True
    st.session_state.pending_user_input = input_text
    st.rerun()

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        if msg["content"] == "LOADING" and i == len(st.session_state.messages) - 1:
            message_placeholder = st.empty()
            message_placeholder.markdown("""
                <div class="loading-container">
                    <div class="loading-spinner"></div>
                    <div class="loading-text">Invoking agent<span class="loading-dots"></span></div>
                </div>
            """, unsafe_allow_html=True)
            
            if st.session_state.get("processing") and st.session_state.get("pending_user_input"):
                user_input = st.session_state.pending_user_input
                st.session_state.processing = False
                st.session_state.pending_user_input = None
                
                status = get_agent_status()
                if not status.get("agent_initialized"):
                    message_placeholder.error("I'm having trouble connecting to the agent. Please check the backend.")
                    st.session_state.messages[i] = {"role": "assistant", "content": "Error: Agent not initialized."}
                else:
                    try:
                        response_text = ""
                        first_chunk = True
                        for chunk in stream_agent_response(user_input):
                            if first_chunk:
                                message_placeholder.empty()
                                first_chunk = False
                            response_text += chunk
                            message_placeholder.markdown(response_text)
                        st.session_state.messages[i] = {"role": "assistant", "content": response_text}
                    except Exception as e:
                        message_placeholder.empty()
                        response_text = invoke_agent_non_streaming(user_input)
                        message_placeholder.markdown(response_text)
                        st.session_state.messages[i] = {"role": "assistant", "content": response_text}
        elif msg["content"] == "LOADING":
            st.markdown("""
                <div class="loading-container">
                    <div class="loading-spinner"></div>
                    <div class="loading-text">Invoking agent<span class="loading-dots"></span></div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(msg["content"])

if st.session_state.pending_prompt:
    prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None
    process_user_input(prompt)
    st.rerun()

if prompt := st.chat_input("Ask me to deploy resources, check logs, or analyze costs..."):
    process_user_input(prompt)
    st.rerun()

with st.sidebar:
    st.header("Control Panel")
    
    with st.expander("🚀 Capabilities", expanded=True):
        st.markdown("""
            <div class="status-row"><span>☁️ Infrastructure</span><span class="badge badge-neutral">IaC</span></div>
            <div class="status-row"><span>🛡️ Security Audit</span><span class="badge badge-neutral">IAM</span></div>
            <div class="status-row"><span>💰 Cost Analyzer</span><span class="badge badge-neutral">FinOps</span></div>
            <div class="status-row"><span>📝 Log Analysis</span><span class="badge badge-neutral">CloudWatch</span></div>
        """, unsafe_allow_html=True)
    
    with st.expander("⚡ Quick Start", expanded=True):
        st.markdown("Try one of these:")
        if st.button("List all S3 buckets"):
            st.session_state.pending_prompt = "List all S3 buckets in my account"
            st.rerun()
        if st.button("Check running EC2 instances"):
            st.session_state.pending_prompt = "Show me all running EC2 instances"
            st.rerun()
        if st.button("Analyze monthly costs"):
            st.session_state.pending_prompt = "Analyze my AWS costs for the last month"
            st.rerun()

    status = get_agent_status()
    is_healthy = status.get("status") == "healthy" and status.get("agent_initialized")
    
    gw_badge = "badge-active" if is_healthy else "badge-error"
    gw_text = "ONLINE" if is_healthy else "OFFLINE"

    with st.expander("🤖 Agent Status", expanded=True):
        st.markdown(f"""
            <div class="status-row">
                <span>connection</span>
                <span class="badge {gw_badge}">{gw_text}</span>
            </div>
            <div class="status-row">
                <span>Runtime</span>
                <span class="badge badge-neutral">{AGENT_RUNTIME}</span>
            </div>
            <div class="status-row">
                <span>Latency</span>
                <span class="badge badge-neutral">~24ms</span>
            </div>
            <div class="status-row">
                <span>Model</span>
                <span class="badge badge-neutral">{get_model_name(BEDROCK_MODEL_ID)}</span>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top: 0.75rem;'></div>", unsafe_allow_html=True)
        if st.button("Ping Agent"):
            st.rerun()

    with st.expander("ℹ️ About", expanded=False):
        st.markdown("""
            I'm your **AWS CloudOps Assistant**, powered by **Bedrock FMs**. 
            I can help you safely manage your AWS environment through natural language.
        """)

    st.markdown("---")
    
    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = [{
            "role": "assistant",
            "content": "Hi there! I'm ready to help you manage your cloud infrastructure. What's on your mind today?"
        }]
        st.session_state.processing = False
        st.session_state.pending_user_input = None
        st.rerun()
    
    st.markdown("<div style='margin-top: 3rem;'></div>", unsafe_allow_html=True)
    st.markdown(f"""
        <div style="
            text-align: center;
            font-size: 0.75rem;
            color: rgba(34, 197, 94, 0.7);
            padding: 0.5rem 0;
            border-top: 1px solid rgba(34, 197, 94, 0.1);
            margin-top: 1rem;
        ">
            {STRANDS_AGENT_VERSION} • Connected to {AGENT_RUNTIME}
        </div>
    """, unsafe_allow_html=True)