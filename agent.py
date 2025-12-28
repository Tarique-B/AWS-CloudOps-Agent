import json
import logging
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from strands import Agent
from strands_tools import use_aws
from strands.models.bedrock import BedrockModel
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from models import InvocationRequest, PingResponse

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
BEDROCK_MODEL_REGION = os.getenv("BEDROCK_MODEL_REGION", "us-east-1")
MEMORY_ID = os.getenv("AGENTCORE_LTM_MEMORY_ID")

logger.info(f"Using Bedrock Model ID: {BEDROCK_MODEL_ID} in region: {BEDROCK_MODEL_REGION}")

def create_aws_assistant_agent(session_id: str = None, actor_id: str = None):
    logger.info(f"Creating AWS Assistant agent (session_id={session_id}, actor_id={actor_id})")
    system_prompt = """You are an AWS Assistant. Your role is to help users interact with and manage AWS services.

You have access to AWS services through the use_aws tool, which gives you comprehensive access to all AWS services.

When users ask about AWS:
- Use the use_aws tool to interact with AWS services
- Provide clear, helpful responses
- Explain what you're doing before executing actions
- Report errors clearly if something goes wrong
- Actively recall and consider the user's preferences and known facts to personalize and improve your assistance.

Be helpful, professional, and focus on AWS-related tasks."""

    session_manager = None
    if MEMORY_ID and session_id and actor_id:
        try:
            logger.info(f"Initializing AgentCore Memory with ID: {MEMORY_ID}")
            agentcore_memory_config = AgentCoreMemoryConfig(
                memory_id=MEMORY_ID,
                session_id=session_id,
                actor_id=actor_id,
                retrieval_config={
                    "/preferences/{actorId}": RetrievalConfig(
                        top_k=5,
                        relevance_score=0.7
                    ),
                    "/facts/{actorId}": RetrievalConfig(
                        top_k=10,
                        relevance_score=0.3
                    ),
                    "/summaries/{actorId}/{sessionId}": RetrievalConfig(
                        top_k=5,
                        relevance_score=0.5
                    )
                }
            )
            session_manager = AgentCoreMemorySessionManager(
                agentcore_memory_config=agentcore_memory_config,
                region_name=BEDROCK_MODEL_REGION
            )
            logger.info("Memory session manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize memory session manager: {e}")
            # Fallback to no memory if initialization fails

    try:
        agent = Agent(
            model=BedrockModel(model_id=BEDROCK_MODEL_ID, region=BEDROCK_MODEL_REGION),
            system_prompt=system_prompt,
            tools=[use_aws],
            session_manager=session_manager
        )
        logger.info("AWS Assistant agent created successfully")
        return agent
    except Exception as e:
        logger.error(f"Failed to create AWS Assistant agent: {str(e)}")
        raise

app = FastAPI(title="AWS Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InvocationRequest(InvocationRequest):
    session_id: str | None = None
    actor_id: str | None = None

# Global agent instance (used for default/legacy calls)
default_agent = None

@app.on_event("startup")
async def startup_event():
    """Initialize default agent on startup"""
    global default_agent
    logger.info("Starting up AWS Assistant API server")
    try:
        default_agent = create_aws_assistant_agent()
        logger.info("Default agent initialized successfully on startup")
    except Exception as e:
        logger.warning(f"Failed to initialize default agent on startup: {e}")

@app.get("/ping")
async def ping():
    global default_agent
    logger.debug("Ping endpoint called")
    agent_initialized = default_agent is not None
    
    # Try to initialize agent if not already initialized
    health_status = "healthy"
    if not agent_initialized:
        logger.info("Default agent not initialized, attempting to create agent")
        try:
            default_agent = create_aws_assistant_agent()
            agent_initialized = True
            logger.info("Default agent created successfully via ping endpoint")
        except Exception as e:
            health_status = "unhealthy"
            agent_initialized = False
            logger.error(f"Failed to create default agent via ping endpoint: {str(e)}")
    
    return {
        "status": health_status,
        "model_id": BEDROCK_MODEL_ID,
        "agent_initialized": agent_initialized,
        "memory_enabled": bool(MEMORY_ID),
        "memory_id": MEMORY_ID
    }


@app.post("/invocations")
async def invoke_agent(request: InvocationRequest):
    global default_agent
    
    logger.info(f"Invocation request received: stream={request.stream}, prompt_length={len(request.prompt)}, session_id={request.session_id}")
    
    # Determine which agent to use
    if request.session_id and request.actor_id and MEMORY_ID:
        # Create a specific agent instance for this session/actor
        logger.info("Creating session-specific agent with memory")
        current_agent = create_aws_assistant_agent(request.session_id, request.actor_id)
    else:
        # Use default agent
        logger.info("Using default agent (no memory/session context)")
        if not default_agent:
             default_agent = create_aws_assistant_agent()
        current_agent = default_agent

    # Handle streaming response
    if request.stream:
        logger.info("Processing streaming invocation")
        async def generate_stream():
            try:
                async for event in current_agent.stream_async(request.prompt):
                    if "data" in event:
                        data = event["data"]
                        # Skip tool usage events in data
                        if isinstance(data, dict) and ("toolUse" in data or "toolResult" in data):
                            continue
                        chunk = str(data)
                        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                    elif "delta" in event:
                        delta = event["delta"]
                        # Skip tool usage events in delta
                        if isinstance(delta, dict) and ("toolUse" in delta or "toolResult" in delta):
                            continue
                        
                        # Handle text content in delta
                        if isinstance(delta, dict) and "text" in delta:
                            chunk = delta["text"]
                        elif isinstance(delta, str):
                            chunk = delta
                        else:
                            chunk = str(delta)

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
            response = current_agent(request.prompt)
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

def _extract_response_text(response):
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8888))
    logger.info(f"Starting AWS Assistant API server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
