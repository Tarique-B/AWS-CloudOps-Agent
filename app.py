import json
import logging
import os
import requests
import streamlit as st
from requests.exceptions import ConnectionError, Timeout
import boto3
import uuid
import random
import string

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
AGENTCORE_RUNTIME_ARN = os.getenv("AGENTCORE_RUNTIME_ARN")
AGENTCORE_RUNTIME_REGION = os.getenv("AGENTCORE_RUNTIME_REGION", "us-east-1")
AGENTCORE_RUNTIME_ENDPOINT = os.getenv("AGENTCORE_RUNTIME_ENDPOINT", "DEFAULT")
AGENT_RUNTIME = "Agentcore" if AGENTCORE_RUNTIME_ARN else "local"
STRANDS_AGENT_VERSION = os.getenv("STRANDS_AGENT_VERSION", "v1.0.0")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "unknown")

st.set_page_config(
    page_title="AWS CloudOps Assistant",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_agent_runtime_info():
    if AGENT_RUNTIME != "Agentcore" or not AGENTCORE_RUNTIME_ARN:
        return None
    
    try:
        client = boto3.client('bedrock-agentcore-control', region_name=AGENTCORE_RUNTIME_REGION)
        
        runtime_id = AGENTCORE_RUNTIME_ARN.split('/')[-1] if '/' in AGENTCORE_RUNTIME_ARN else AGENTCORE_RUNTIME_ARN.split(':')[-1] if ':' in AGENTCORE_RUNTIME_ARN else AGENTCORE_RUNTIME_ARN
        
        response = client.get_agent_runtime(agentRuntimeId=runtime_id)
        
        env_vars = response.get('environmentVariables', {})
        memory_id = env_vars.get('AGENTCORE_LTM_MEMORY_ID', '')
        memory_region = env_vars.get('AGENTCORE_LTM_MEMORY_REGION', '')
        model_id = env_vars.get('BEDROCK_MODEL_ID', '')
        agent_version = env_vars.get('STRANDS_AGENT_VERSION', '')
        
        return {
            "status": response.get('status', 'UNKNOWN'),
            "memory_id": memory_id,
            "memory_region": memory_region,
            "model_id": model_id,
            "agent_version": agent_version,
            "runtime_name": response.get('agentRuntimeName', ''),
            "runtime_version": response.get('agentRuntimeVersion', '')
        }
    except Exception as e:
        logger.error(f"Failed to get agent runtime info: {e}")
        return None

def get_agent_status():
    if AGENT_RUNTIME == "Agentcore":
        try:
            logger.debug("[Step 4/7]: Checking AgentCore runtime status")
            runtime_info = get_agent_runtime_info()
            if runtime_info:
                status = "healthy" if runtime_info.get("status") == "READY" else "unhealthy"
                logger.debug(f"[Step 4/7]: AgentCore status: {status}, Model: {runtime_info.get('model_id', 'unknown')}")
                return {
                    "status": status,
                    "model_id": runtime_info.get("model_id", "unknown"),
                    "agent_initialized": True,
                    "runtime_info": runtime_info
                }
            logger.warning("[Step 4/7]: AgentCore runtime info not available")
            return {"status": "healthy", "model_id": "unknown", "agent_initialized": True}
        except Exception as e:
            logger.error(f"[Step 4/7]: Failed to get AgentCore status: {str(e)}")
            return {"status": "unhealthy", "model_id": "unknown", "agent_initialized": False}
    else:
        try:
            logger.debug(f"[Step 4/7]: Checking local API status: {API_BASE_URL}/ping")
            response = requests.get(f"{API_BASE_URL}/ping", timeout=2)
            if response.status_code == 200:
                status_data = response.json()
                logger.debug(f"[Step 4/7]: Local API status: {status_data.get('status', 'unknown')}")
                return status_data
            logger.warning(f"[Step 4/7]: Local API returned status code: {response.status_code}")
            return {"status": "unhealthy", "model_id": "unknown", "agent_initialized": False}
        except Exception as e:
            logger.error(f"[Step 4/7]: Failed to connect to local API: {str(e)}")
            return {"status": "unhealthy", "model_id": "unknown", "agent_initialized": False}

def stream_agent_response(prompt, session_id=None, actor_id=None):
    if AGENT_RUNTIME == "Agentcore":
        try:
            logger.info(f"[Step 5/7]: Creating Bedrock AgentCore client (Region: {AGENTCORE_RUNTIME_REGION})")
            client = boto3.client('bedrock-agentcore', region_name=AGENTCORE_RUNTIME_REGION)
            
            payload_data = {"prompt": prompt}
            if session_id:
                payload_data["session_id"] = session_id
            if actor_id:
                payload_data["actor_id"] = actor_id
            
            payload = json.dumps(payload_data)
            logger.info(f"[Step 5/7]: Payload prepared: prompt_length={len(prompt)}, has_session_id={bool(session_id)}, has_actor_id={bool(actor_id)}")
            
            if session_id and len(session_id) >= 33:
                runtime_session_id = session_id
                logger.info(f"[Step 5/7]: Using provided session_id: {runtime_session_id[:20]}...")
            else:
                session_uuid = uuid.uuid4().hex
                runtime_session_id = f"session_{session_uuid}_{uuid.uuid4().hex[:10]}"
                logger.info(f"[Step 5/7]: Generated new runtime_session_id: {runtime_session_id}")
            
            logger.info(f"[Step 5/7]: Invoking AgentCore Runtime (ARN: {AGENTCORE_RUNTIME_ARN[:50]}...)")
            response = client.invoke_agent_runtime(
                agentRuntimeArn=AGENTCORE_RUNTIME_ARN,
                runtimeSessionId=runtime_session_id,
                payload=payload,
                qualifier=AGENTCORE_RUNTIME_ENDPOINT
            )
            logger.info("[Step 5/7]: AgentCore invocation successful, processing response stream")
            
            # Process the response stream
            line_count = 0
            for line in response["response"].iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        try:
                            data = json.loads(line_str[6:])
                            if 'chunk' in data:
                                line_count += 1
                                if line_count == 1:
                                    logger.info("[Step 5/7]: First data chunk received from stream")
                                yield data['chunk']
                            elif 'error' in data:
                                logger.error(f"[Step 5/7]: Error in stream: {data['error']}")
                                yield f"\n\nStream Error: {data['error']}"
                        except Exception as parse_error:
                            logger.debug(f"[Step 5/7]: Failed to parse stream line: {str(parse_error)}")
                            continue
            logger.info(f"[Step 5/7]: Stream processing complete. Total data lines: {line_count}")
        except Exception as e:
            logger.error(f"[Step 5/7]: AgentCore runtime error: {str(e)}")
            yield f"Agentcore runtime error: {str(e)}"
    else:
        try:
            logger.info(f"[Step 5/7]: Preparing request to local API: {API_BASE_URL}/invocations")
            request_data = {"prompt": prompt, "stream": True}
            if session_id:
                request_data["session_id"] = session_id
            if actor_id:
                request_data["actor_id"] = actor_id
            
            logger.info(f"[Step 5/7]: Request data: prompt_length={len(prompt)}, has_session_id={bool(session_id)}, has_actor_id={bool(actor_id)}")
            logger.info(f"[Step 5/7]: Sending POST request to API (timeout: 300s)")
            
            response = requests.post(
                f"{API_BASE_URL}/invocations",
                json=request_data,
                stream=True,
                timeout=300
            )
            
            logger.info(f"[Step 5/7]: API response received. Status code: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"[Step 5/7]: API returned error status: {response.status_code}")
                yield f"Oops! Something went wrong. (Status: {response.status_code})"
                return

            logger.info("[Step 5/7]: Processing API response stream")
            line_count = 0
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        try:
                            data = json.loads(line_str[6:])
                            if 'chunk' in data:
                                line_count += 1
                                if line_count == 1:
                                    logger.info("[Step 5/7]: First data chunk received from API stream")
                                yield data['chunk']
                            elif 'error' in data:
                                logger.error(f"[Step 5/7]: Error in API stream: {data['error']}")
                                yield f"\n\nStream Error: {data['error']}"
                        except Exception as parse_error:
                            logger.debug(f"[Step 5/7]: Failed to parse API stream line: {str(parse_error)}")
                            continue
            logger.info(f"[Step 5/7]: API stream processing complete. Total data lines: {line_count}")
        except Exception as e:
            logger.error(f"[Step 5/7]: Connection error: {str(e)}")
            yield f"Connection issue: {str(e)}"

def invoke_agent_non_streaming(prompt, session_id=None, actor_id=None):
    logger.info("[Step 5/7]: Using non-streaming mode")
    if AGENT_RUNTIME == "Agentcore":
        try:
            logger.info(f"[Step 5/7]: Creating Bedrock AgentCore client (Region: {AGENTCORE_RUNTIME_REGION})")
            client = boto3.client('bedrock-agentcore', region_name=AGENTCORE_RUNTIME_REGION)
            
            payload_data = {"prompt": prompt}
            if session_id:
                payload_data["session_id"] = session_id
            if actor_id:
                payload_data["actor_id"] = actor_id
            
            payload = json.dumps(payload_data)
            logger.info(f"[Step 5/7]: Payload prepared: prompt_length={len(prompt)}, has_session_id={bool(session_id)}, has_actor_id={bool(actor_id)}")
            
            if session_id and len(session_id) >= 33:
                runtime_session_id = session_id
                logger.info(f"[Step 5/7]: Using provided session_id: {runtime_session_id[:20]}...")
            else:
                session_uuid = uuid.uuid4().hex
                runtime_session_id = f"session_{session_uuid}_{uuid.uuid4().hex[:10]}"
                logger.info(f"[Step 5/7]: Generated new runtime_session_id: {runtime_session_id}")
            
            logger.info(f"[Step 5/7]: Invoking AgentCore Runtime (non-streaming, ARN: {AGENTCORE_RUNTIME_ARN[:50]}...)")
            response = client.invoke_agent_runtime(
                agentRuntimeArn=AGENTCORE_RUNTIME_ARN,
                runtimeSessionId=runtime_session_id,
                payload=payload,
                qualifier=AGENTCORE_RUNTIME_ENDPOINT
            )
            
            logger.info("[Step 5/7]: AgentCore invocation successful, reading response")
            response_data = json.loads(response["response"].read())
            response_text = response_data.get("response", "No response received.")
            logger.info(f"[Step 5/7]: Response received. Length: {len(response_text)}")
            return response_text
        except Exception as e:
            logger.error(f"[Step 5/7]: AgentCore runtime error: {str(e)}")
            return f"Agentcore runtime error: {str(e)}"
    else:
        try:
            logger.info(f"[Step 5/7]: Preparing request to local API: {API_BASE_URL}/invocations (non-streaming)")
            request_data = {"prompt": prompt, "stream": False}
            if session_id:
                request_data["session_id"] = session_id
            if actor_id:
                request_data["actor_id"] = actor_id
            
            logger.info(f"[Step 5/7]: Request data: prompt_length={len(prompt)}, has_session_id={bool(session_id)}, has_actor_id={bool(actor_id)}")
            logger.info(f"[Step 5/7]: Sending POST request to API (timeout: 300s)")
            
            response = requests.post(
                f"{API_BASE_URL}/invocations",
                json=request_data,
                timeout=300
            )
            
            logger.info(f"[Step 5/7]: API response received. Status code: {response.status_code}")
            if response.status_code == 200:
                response_text = response.json().get("response", "No response received.")
                logger.info(f"[Step 5/7]: Response received. Length: {len(response_text)}")
                return response_text
            logger.error(f"[Step 5/7]: API returned error status: {response.status_code}")
            return f"Error: {response.status_code}"
        except Exception as e:
            logger.error(f"[Step 5/7]: Connection error: {str(e)}")
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

if "session_id" not in st.session_state:
    session_uuid = uuid.uuid4().hex
    st.session_state.session_id = f"session_{session_uuid}_{uuid.uuid4().hex[:10]}"

if "actor_id" not in st.session_state:
    st.session_state.actor_id = f"tarique_{uuid.uuid4().hex[:12]}"

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
    logger.info(f"[Step 1/7]: User input received: {input_text[:100]}...")
    logger.info(f"[Step 1/7]: Session ID: {st.session_state.get('session_id', 'N/A')}, Actor ID: {st.session_state.get('actor_id', 'N/A')}")
    
    st.session_state.messages.append({"role": "user", "content": input_text})
    st.session_state.messages.append({"role": "assistant", "content": "LOADING"})
    if "processing" not in st.session_state:
        st.session_state.processing = False
    if "pending_user_input" not in st.session_state:
        st.session_state.pending_user_input = None
    st.session_state.processing = True
    st.session_state.pending_user_input = input_text
    logger.info("[Step 2/7]: User input queued for processing")
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
                
                logger.info(f"[Step 3/7]: Processing user input: {user_input[:100]}...")
                logger.info(f"[Step 4/7]: Checking agent status (Runtime: {AGENT_RUNTIME})")
                
                status = get_agent_status()
                logger.info(f"[Step 4/7]: Agent status: initialized={status.get('agent_initialized')}, status={status.get('status')}")
                
                if not status.get("agent_initialized"):
                    logger.error("[Step 4/7]: Agent not initialized - cannot process request")
                    message_placeholder.error("I'm having trouble connecting to the agent. Please check the backend.")
                    st.session_state.messages[i] = {"role": "assistant", "content": "Error: Agent not initialized."}
                else:
                    try:
                        logger.info(f"[Step 5/7]: Invoking agent (streaming mode, Runtime: {AGENT_RUNTIME})")
                        response_text = ""
                        first_chunk = True
                        chunk_count = 0
                        for chunk in stream_agent_response(user_input, st.session_state.session_id, st.session_state.actor_id):
                            if first_chunk:
                                logger.info("[Step 6/7]: First response chunk received, starting to display")
                                message_placeholder.empty()
                                first_chunk = False
                            chunk_count += 1
                            response_text += chunk
                            message_placeholder.markdown(response_text)
                        logger.info(f"[Step 7/7]: Streaming complete. Total chunks: {chunk_count}, Response length: {len(response_text)}")
                        st.session_state.messages[i] = {"role": "assistant", "content": response_text}
                    except Exception as e:
                        logger.warning(f"[Step 5/7]: Streaming failed, falling back to non-streaming: {str(e)}")
                        logger.info("[Step 5/7]: Attempting non-streaming invocation")
                        message_placeholder.empty()
                        response_text = invoke_agent_non_streaming(user_input, st.session_state.session_id, st.session_state.actor_id)
                        logger.info(f"[Step 7/7]: Non-streaming response received. Length: {len(response_text)}")
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
    
    with st.expander("📋 Session Info", expanded=False):
        current_actor_id = st.session_state.get("actor_id") or ""
        
        st.markdown("""
            <div class="status-row">
                <span>Username</span>
                <span class="badge badge-neutral">{actor_id}</span>
            </div>
        """.format(actor_id=current_actor_id if current_actor_id else "Not set"), unsafe_allow_html=True)
        
        username = st.text_input(
            "Username",
            value=current_actor_id,
            key="actor_id_input",
            placeholder="Enter username (used as Actor ID)",
            label_visibility="collapsed"
        )
        
        if st.button("Update Username", use_container_width=True):
            if username and username.strip():
                st.session_state.actor_id = username.strip()
                if "actor_id_input" in st.session_state:
                    del st.session_state.actor_id_input
                st.success(f"Username updated to: {username.strip()}")
            else:
                st.session_state.actor_id = f"user_{uuid.uuid4().hex[:12]}"
                if "actor_id_input" in st.session_state:
                    del st.session_state.actor_id_input
                st.info("Username reset to default")
            st.rerun()
        
        session_id_display = st.session_state.session_id
        session_id_short = "SESSION_" + session_id_display[8:13] if len(session_id_display) > 13 else session_id_display
        
        st.markdown(f"""
            <div class="status-row">
                <span>Session ID</span>
                <span class="badge badge-neutral" title="{session_id_display}">{session_id_short}</span>
            </div>
        """, unsafe_allow_html=True)
        
        if AGENT_RUNTIME == "Agentcore":
            runtime_info = get_agent_runtime_info()
            memory_enabled = "No"
            if runtime_info and runtime_info.get("memory_id"):
                memory_enabled = "Yes"
            
            st.markdown(f"""
                <div class="status-row">
                    <span>Memory</span>
                    <span class="badge badge-neutral">{memory_enabled}</span>
                </div>
            """, unsafe_allow_html=True)
        
        if st.button("🔄 New Session", use_container_width=True):
            session_uuid = uuid.uuid4().hex
            st.session_state.session_id = f"session_{session_uuid}_{uuid.uuid4().hex[:10]}"
            st.session_state.messages = [{
                "role": "assistant",
                "content": "New session started. How can I assist you?"
            }]
            st.success("New session created!")
            st.rerun()
    
    with st.expander("🚀 Capabilities", expanded=False):
        st.markdown("""
            <div class="status-row"><span>☁️ Infrastructure</span><span class="badge badge-neutral">IaC</span></div>
            <div class="status-row"><span>🛡️ Security Audit</span><span class="badge badge-neutral">IAM</span></div>
            <div class="status-row"><span>💰 Cost Analyzer</span><span class="badge badge-neutral">FinOps</span></div>
            <div class="status-row"><span>📝 Log Analysis</span><span class="badge badge-neutral">CloudWatch</span></div>
        """, unsafe_allow_html=True)
    
    with st.expander("⚡ Quick Start", expanded=False):
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
    
    runtime_info = status.get("runtime_info") if AGENT_RUNTIME == "Agentcore" else None
    memory_id_display = ""
    agent_version_display = ""
    
    if runtime_info:
        memory_id = runtime_info.get("memory_id", "")
        if memory_id and len(memory_id) > 11:
            memory_id_display = f"{memory_id[:8]}...{memory_id[-3:]}"
        elif memory_id:
            memory_id_display = memory_id
        
        agent_version_display = runtime_info.get("agent_version", "")

    with st.expander("🤖 Agent Status", expanded=False):
        endpoint_row = f"""
            <div class="status-row">
                <span>Endpoint</span>
                <span class="badge badge-neutral">{AGENTCORE_RUNTIME_ENDPOINT}</span>
            </div>
        """ if AGENT_RUNTIME == "Agentcore" else ""
        
        memory_row = ""
        if AGENT_RUNTIME == "Agentcore" and runtime_info and memory_id_display:
            memory_row = f"""
            <div class="status-row">
                <span>AgentCore Memory</span>
                <span class="badge badge-neutral" title="{runtime_info.get('memory_id', '')}">{memory_id_display}</span>
            </div>
            """
        
        version_row = ""
        if agent_version_display:
            version_row = f"""
            <div class="status-row">
                <span>Agent Version</span>
                <span class="badge badge-neutral">{agent_version_display}</span>
            </div>
            """
        
        st.markdown(f"""
            <div class="status-row">
                <span>connection</span>
                <span class="badge {gw_badge}">{gw_text}</span>
            </div>
            <div class="status-row">
                <span>Runtime</span>
                <span class="badge badge-neutral">{AGENT_RUNTIME}</span>
            </div>
            {endpoint_row}
            {memory_row}
            {version_row}
            <div class="status-row">
                <span>Latency</span>
                <span class="badge badge-neutral">~24ms</span>
            </div>
            <div class="status-row">
                <span>Model</span>
                <span class="badge badge-neutral">{get_model_name(runtime_info.get('model_id', BEDROCK_MODEL_ID) if runtime_info else BEDROCK_MODEL_ID)}</span>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top: 0.75rem;'></div>", unsafe_allow_html=True)
        if st.button("Ping Agent"):
            st.rerun()

    with st.expander("ℹ️ About", expanded=False):
        st.markdown("""
            I'm your **AWS CloudOps Assistant**, powered by **Bedrock FMs and Bedrock AgentCore**. 
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
    
    runtime_info = status.get("runtime_info") if AGENT_RUNTIME == "Agentcore" else None
    agent_version_display = runtime_info.get("agent_version") if runtime_info and runtime_info.get("agent_version") else STRANDS_AGENT_VERSION
    runtime_display = "Agentcore" if AGENT_RUNTIME == "Agentcore" else AGENT_RUNTIME
    
    st.markdown(f"""
        <div style="
            text-align: center;
            font-size: 0.75rem;
            color: rgba(34, 197, 94, 0.7);
            padding: 0.5rem 0;
            border-top: 1px solid rgba(34, 197, 94, 0.1);
            margin-top: 1rem;
        ">
            {agent_version_display} • Connected to {runtime_display}
            <br>
            <span style="font-size: 0.65rem; opacity: 0.8;">Powered by Strands Agents</span>
        </div>
    """, unsafe_allow_html=True)