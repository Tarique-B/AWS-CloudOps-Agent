"""
AWS Assistant Agent using Strands Agents framework
Provides REST API endpoints for agent interactions
"""
import json
import logging
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from strands import Agent
from strands_tools import use_aws
from strands.models.bedrock import BedrockModel
from models import InvocationRequest, PingResponse

# ============================================================================
# Logging Configuration
# ============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
logger.info(f"Using Bedrock Model ID: {BEDROCK_MODEL_ID}")

# ============================================================================
# Agent Creation
# ============================================================================
def create_aws_assistant_agent():
    """
    Create an AWS Assistant agent using Strands Agents framework
    
    Returns:
        Agent: Configured Strands agent with AWS tools
    """
    logger.info("Creating AWS Assistant agent")
    system_prompt = """You are an AWS Assistant. Your role is to help users interact with and manage AWS services.

You have access to AWS services through the use_aws tool, which gives you comprehensive access to all AWS services.

When users ask about AWS:
- Use the use_aws tool to interact with AWS services
- Provide clear, helpful responses
- Explain what you're doing before executing actions
- Report errors clearly if something goes wrong

Be helpful, professional, and focus on AWS-related tasks."""

    try:
        agent = Agent(
            model=BedrockModel(model_id=BEDROCK_MODEL_ID),
            system_prompt=system_prompt,
            tools=[use_aws]
        )
        logger.info("AWS Assistant agent created successfully")
        return agent
    except Exception as e:
        logger.error(f"Failed to create AWS Assistant agent: {str(e)}")
        raise

# ============================================================================
# FastAPI Application Setup
# ============================================================================
app = FastAPI(title="AWS Assistant API", version="1.0.0")

# Enable CORS for Streamlit app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Streamlit origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance
agent = None

# ============================================================================
# Startup Event
# ============================================================================
@app.on_event("startup")
async def startup_event():
    """Initialize agent on startup"""
    global agent
    logger.info("Starting up AWS Assistant API server")
    try:
        agent = create_aws_assistant_agent()
        logger.info("Agent initialized successfully on startup")
    except Exception as e:
        logger.warning(f"Failed to initialize agent on startup: {e}")

# ============================================================================
# API Endpoints
# ============================================================================
@app.get("/ping")
async def ping():
    """
    Ping endpoint to check agent health and status
    Returns the health status, model ID, and initialization state
    """
    global agent
    logger.debug("Ping endpoint called")
    agent_initialized = agent is not None
    
    # Try to initialize agent if not already initialized
    health_status = "healthy"
    if not agent_initialized:
        logger.info("Agent not initialized, attempting to create agent")
        try:
            agent = create_aws_assistant_agent()
            agent_initialized = True
            logger.info("Agent created successfully via ping endpoint")
        except Exception as e:
            health_status = "unhealthy"
            agent_initialized = False
            logger.error(f"Failed to create agent via ping endpoint: {str(e)}")
    
    logger.info(f"Ping response: status={health_status}, initialized={agent_initialized}")
    return PingResponse(
        status=health_status,
        model_id=BEDROCK_MODEL_ID,
        agent_initialized=agent_initialized
    )


@app.post("/invocations")
async def invoke_agent(request: InvocationRequest):
    """
    Invoke the agent with a prompt
    Supports both streaming and non-streaming responses
    """
    global agent
    
    logger.info(f"Invocation request received: stream={request.stream}, prompt_length={len(request.prompt)}")
    
    # Ensure agent is initialized
    if not agent:
        logger.info("Agent not initialized, creating agent")
        try:
            agent = create_aws_assistant_agent()
        except Exception as e:
            logger.error(f"Agent initialization failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Agent initialization failed: {str(e)}"
            )
    
    # Handle streaming response
    if request.stream:
        logger.info("Processing streaming invocation")
        async def generate_stream():
            try:
                async for event in agent.stream_async(request.prompt):
                    if "data" in event:
                        chunk = str(event["data"])
                        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                    elif "delta" in event:
                        chunk = str(event["delta"])
                        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                yield f"data: {json.dumps({'done': True})}\n\n"
                logger.info("Streaming invocation completed successfully")
            except Exception as e:
                logger.error(f"Error during streaming invocation: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    # Handle non-streaming response
    else:
        logger.info("Processing non-streaming invocation")
        try:
            response = agent(request.prompt)
            response_text = _extract_response_text(response)
            logger.info(f"Non-streaming invocation completed, response_length={len(response_text)}")
            
            return {
                "response": response_text,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Agent invocation failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Agent invocation failed: {str(e)}"
            )

# ============================================================================
# Helper Functions
# ============================================================================
def _extract_response_text(response):
    """
    Extract text content from agent response
    
    Args:
        response: Agent response object
        
    Returns:
        str: Extracted text content
    """
    if isinstance(response, dict) and "content" in response:
        content = response["content"]
        if isinstance(content, list) and len(content) > 0:
            first_item = content[0]
            if isinstance(first_item, dict) and "text" in first_item:
                return first_item["text"]
            else:
                return str(first_item)
        else:
            return str(content)
    else:
        return str(response)

# ============================================================================
# Main Entry Point
# ============================================================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8888))
    logger.info(f"Starting AWS Assistant API server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
