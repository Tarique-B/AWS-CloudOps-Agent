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
logger.info(f"Streamlit app initialized with API_BASE_URL: {API_BASE_URL}")

def get_agent_status():
    logger.debug("Fetching agent status from API")
    try:
        response = requests.get(f"{API_BASE_URL}/ping", timeout=5)
        if response.status_code == 200:
            status_data = response.json()
            logger.info(f"Agent status retrieved: {status_data.get('status')}, initialized: {status_data.get('agent_initialized')}")
            return status_data
        else:
            logger.warning(f"Ping endpoint returned status code: {response.status_code}")
            return {
                "status": "unhealthy",
                "model_id": "unknown",
                "agent_initialized": False
            }
    except (ConnectionError, Timeout, Exception) as e:
        logger.error(f"Failed to get agent status: {str(e)}")
        return {
            "status": "unhealthy",
            "model_id": "unknown",
            "agent_initialized": False,
            "error": str(e)
        }


def stream_agent_response(prompt):
    full_response = ""
    logger.info(f"Starting streaming request, prompt_length={len(prompt)}")
    
    try:
        # Make streaming request to API
        response = requests.post(
            f"{API_BASE_URL}/invocations",
            json={"prompt": prompt, "stream": True},
            stream=True,
            timeout=300
        )
        
        if response.status_code != 200:
            error_msg = f"API Error: {response.status_code} - {response.text}"
            logger.error(f"Streaming request failed: {error_msg}")
            yield error_msg
            st.session_state.last_streamed_response = error_msg
            return
        
        logger.debug("Streaming connection established, processing chunks")
        chunk_count = 0
        
        # Process Server-Sent Events (SSE)
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                        
                        if 'chunk' in data:
                            chunk = data['chunk']
                            full_response += chunk
                            chunk_count += 1
                            yield chunk
                        elif 'done' in data:
                            logger.info(f"Streaming completed, received {chunk_count} chunks, total_length={len(full_response)}")
                            break
                        elif 'error' in data:
                            error_msg = f"\n\nError: {data['error']}"
                            logger.error(f"Error in stream: {data['error']}")
                            yield error_msg
                            full_response += error_msg
                            break
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse SSE data chunk")
                        continue
        
        # Store the full response in session state for history
        if full_response:
            st.session_state.last_streamed_response = full_response
            
    except Timeout:
        error_msg = "Request timed out. Please try again."
        logger.error("Streaming request timed out")
        yield error_msg
        st.session_state.last_streamed_response = error_msg
    except ConnectionError:
        error_msg = f"Could not connect to API at {API_BASE_URL}. Make sure the API server is running."
        logger.error(f"Connection error: {error_msg}")
        yield error_msg
        st.session_state.last_streamed_response = error_msg
    except Exception as e:
        error_msg = f"Error during streaming: {str(e)}"
        logger.error(f"Streaming error: {str(e)}", exc_info=True)
        yield error_msg
        st.session_state.last_streamed_response = error_msg


def invoke_agent_non_streaming(prompt):
    logger.info(f"Starting non-streaming request, prompt_length={len(prompt)}")
    try:
        response = requests.post(
            f"{API_BASE_URL}/invocations",
            json={"prompt": prompt, "stream": False},
            timeout=300
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "No response received")
            logger.info(f"Non-streaming request completed, response_length={len(response_text)}")
            return response_text
        else:
            error_msg = f"API Error: {response.status_code} - {response.text}"
            logger.error(f"Non-streaming request failed: {error_msg}")
            return error_msg
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(f"Non-streaming request error: {str(e)}", exc_info=True)
        return error_msg

st.set_page_config(
    page_title="AWS Assistant",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Header styling */
    h1 {
        color: #FF9900;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    
    /* Custom styling for chat messages */
    .stChatMessage {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    
    /* User message styling */
    div[data-testid="stChatMessage"] > div:first-child > div:first-child {
        background-color: #232F3E;
        color: white;
        border-radius: 10px;
        padding: 0.75rem;
    }
    
    /* Assistant message styling */
    div[data-testid="stChatMessage"] > div:first-child > div:last-child {
        background-color: #F9F9F9;
        border-left: 4px solid #FF9900;
        border-radius: 10px;
        padding: 0.75rem;
    }
    
    /* Chat input styling */
    .stChatInput > div > div > input {
        border-radius: 25px;
        border: 2px solid #FF9900;
        padding: 0.75rem 1rem;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #F9F9F9;
    }
    
    /* Info box styling */
    .stInfo {
        background-color: #E8F4F8;
        border-left: 4px solid #146EB4;
        border-radius: 5px;
        padding: 1rem;
    }
    
    /* Spinner styling */
    .stSpinner > div {
        border-top-color: #FF9900;
    }
    
    /* Markdown content styling */
    .stMarkdown {
        line-height: 1.6;
    }
    
    /* Header subtitle */
    .subtitle {
        text-align: center;
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 2rem;
        padding-bottom: 1rem;
        border-bottom: 2px solid #F0F0F0;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1>☁️ AWS Assistant</h1>", unsafe_allow_html=True)
st.markdown(
    '<p class="subtitle">Chat with your AWS Assistant powered by Strands Agents and AWS Bedrock</p>',
    unsafe_allow_html=True
)

status_info = get_agent_status()
health_status = status_info.get("status", "unknown")
model_id = status_info.get("model_id", "unknown")
agent_initialized = status_info.get("agent_initialized", False)

# Display status indicators
status_color = "🟢" if health_status == "healthy" and agent_initialized else "🔴"
status_text = "Healthy" if health_status == "healthy" and agent_initialized else "Unhealthy"

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hello! I'm your AWS Assistant powered by Strands Agents. I can help you interact with and manage AWS services. How can I assist you today?"
        }
    ]

chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

if prompt := st.chat_input("Ask about AWS services..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Check agent health before processing
    if not agent_initialized:
        st.error("Agent is not initialized. Please check the API server status.")
        response_text_for_history = "Agent unavailable. Please check the API server."
    else:
        # Get agent response with streaming
        response_text_for_history = ""
        with st.chat_message("assistant"):
            try:
                # Stream the response in real-time from API
                response_text_for_history = st.write_stream(stream_agent_response(prompt))
                
                # Get the full response from session state if available
                if "last_streamed_response" in st.session_state:
                    response_text_for_history = st.session_state.last_streamed_response
                    del st.session_state.last_streamed_response
            except Exception as e:
                # Fallback to non-streaming mode
                try:
                    st.warning(f"Streaming failed, using non-streaming mode: {str(e)}")
                    with st.spinner("Processing..."):
                        response_text_for_history = invoke_agent_non_streaming(prompt)
                    st.markdown(response_text_for_history)
                except Exception as e2:
                    error_msg = f"Error: {str(e2)}"
                    st.error(error_msg)
                    import traceback
                    st.code(traceback.format_exc())
                    response_text_for_history = error_msg
    
    # Add assistant response to chat history
    if response_text_for_history:
        st.session_state.messages.append({"role": "assistant", "content": response_text_for_history})
    
    # Rerun to refresh the display
    st.rerun()

with st.sidebar:
    st.markdown("### 🚀 About")
    st.markdown("---")
    
    st.markdown("#### 📊 Agent Status")
    st.markdown(f"""
    - **Status:** {status_color} {status_text}
    - **Model ID:** `{model_id}`
    - **Initialized:** {'✅ Yes' if agent_initialized else '❌ No'}
    """)
    
    # Refresh status button
    if st.button("🔄 Refresh Status"):
        st.rerun()
    
    st.markdown("---")
    st.markdown("#### 🔧 Powered By")
    st.markdown("""
    - **Strands Agents SDK**  
      AWS's agent framework
    - **AWS Bedrock**  
      Language model capabilities
    """)
    
    st.markdown("---")
    st.markdown("#### ✨ Features")
    st.markdown("""
    - ✅ Interact with all AWS services
    - ✅ Natural language queries
    - ✅ Autonomous agent reasoning
    """)
    
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.85rem; margin-top: 2rem;'>
        Built with Streamlit & Strands Agents
    </div>
    """, unsafe_allow_html=True)
