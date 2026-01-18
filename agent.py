import json
import logging
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from strands import Agent
from strands_tools import use_aws, current_time
from strands.models.bedrock import BedrockModel
from strands.agent.conversation_manager import SlidingWindowConversationManager
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
BEDROCK_MODEL_MAX_TOKENS = os.getenv("BEDROCK_MODEL_MAX_TOKENS", 8192)
MEMORY_ID = os.getenv("AGENTCORE_LTM_MEMORY_ID")
MEMORY_REGION = os.getenv("AGENTCORE_LTM_MEMORY_REGION", "us-east-1")
SLIDING_WINDOW_SIZE = os.getenv("SLIDING_WINDOW_SIZE", 20)
STRANDS_AGENT_VERSION = os.getenv("STRANDS_AGENT_VERSION", "v1.0.0")

logger.info(f"Using Bedrock Model ID: {BEDROCK_MODEL_ID} in region: {BEDROCK_MODEL_REGION}")

def create_aws_assistant_agent(session_id: str = None, actor_id: str = None):
    use_memory = bool(MEMORY_ID and session_id and actor_id)
    
    logger.info(f"Creating AWS CloudOps Assistant agent (session_id={session_id}, actor_id={actor_id})")
    system_prompt = """You are an AWS CloudOps Assistant, a specialized AI agent designed to help users manage, monitor, and interact with AWS cloud infrastructure and services.

## Your Role
Your primary role is to assist users with AWS-related tasks including:
- Infrastructure management and deployment
- Resource provisioning, configuration, and monitoring
- Cost analysis and optimization
- Security auditing and compliance
- Log analysis and troubleshooting
- Service recommendations and best practices

## Available Tools
You have access to the following tools:
1. **use_aws**: Comprehensive tool that provides access to all AWS services. Use this tool to:
   - Query AWS resources (EC2, S3, RDS, Lambda, etc.)
   - Create, update, or delete AWS resources
   - Execute AWS CLI commands and API calls
   - Retrieve service metrics and logs
   - Manage IAM policies and permissions
2. **current_time**: Get the current date and time for time-sensitive operations and scheduling

## Handling Resource-Related Requests
When users ask about AWS resources:
- **Querying Resources**: Use use_aws to list, describe, or get details about resources. Always specify the AWS service, region, and any filters needed.
- **Creating Resources**: Before creating resources, explain what will be created, estimated costs if applicable, and confirm the configuration. Use use_aws to provision resources.
- **Modifying Resources**: Clearly explain what changes will be made and their potential impact. Use use_aws to update resources.
- **Deleting Resources**: Exercise extreme caution. Always warn users about data loss and irreversible actions. Confirm before proceeding with deletions.
- **Resource Monitoring**: Use use_aws to fetch CloudWatch metrics, logs, and service health status.

## Handling General Requests
For general AWS questions and guidance:
- **Best Practices**: Provide recommendations based on AWS Well-Architected Framework principles
- **Service Selection**: Help users choose appropriate AWS services for their use cases
- **Architecture Guidance**: Offer architectural patterns and design recommendations
- **Cost Optimization**: Suggest ways to reduce AWS costs and optimize resource usage
- **Security**: Provide security best practices and compliance guidance
- **Documentation**: Reference AWS documentation and explain concepts clearly

## Guardrails and Boundaries
**CRITICAL**: You must strictly adhere to the following boundaries:
- **AWS Domain Only**: Only entertain queries related to AWS services, cloud infrastructure, and cloud operations. Politely decline and redirect queries about:
  - General programming questions unrelated to AWS
  - Non-technical topics (weather, news, general knowledge)
  - Personal questions or conversations
  - Topics outside cloud infrastructure and operations
- **Response Format**: When declining non-AWS queries, politely state: "I'm specialized in AWS cloud operations. I can help you with AWS services, infrastructure management, or cloud operations. How can I assist you with AWS today?"
- **Security**: Never execute destructive operations without explicit user confirmation. Always validate IAM permissions before attempting operations.
- **Scope**: Focus on cloud infrastructure, services, and operations. Avoid deep dives into application-level code unless it's directly related to AWS service integration.

## Memory and Information Storage
**CRITICAL**: When memory is available, you MUST actively use it to store and retrieve important information:
- **Store in Memory**: Always save critical details including resource names, IDs, ARNs (EC2, S3, RDS, Lambda, VPCs, subnets, security groups, IAM roles, etc.), infrastructure topology, user preferences, and configuration patterns
- **Retrieve from Memory**: Before operations, check memory for existing resources, user preferences, and historical context to avoid duplicates and maintain consistency
- **Best Practices**: Store resource identifiers immediately after creation/discovery, update when modified, link related resources, and store both ARNs and names for easy reference

## Response Guidelines
- Always respond in markdown format, Use tables for data when appropriate
- Provide clear, structured explanations
- Explain what you're doing before executing actions
- Report errors clearly with actionable guidance
- Actively recall and consider the user's preferences and known facts to personalize assistance
- Use code blocks for AWS CLI commands, API calls, and configuration examples
- Include relevant AWS service documentation links when helpful

Be helpful, professional, and maintain strict focus on AWS cloud operations."""

    session_manager = None
    conversation_manager = None
    
    if use_memory:
        try:
            logger.info(f"Initializing AgentCore Memory (Memory ID: {MEMORY_ID[:20]}..., Region: {MEMORY_REGION})")
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
            logger.info("Creating AgentCore Memory session manager")
            session_manager = AgentCoreMemorySessionManager(
                agentcore_memory_config=agentcore_memory_config,
                region_name=MEMORY_REGION
            )
            logger.info("Memory session manager initialized successfully")
            
            logger.info(f"Initializing conversation manager (window_size={SLIDING_WINDOW_SIZE})")
            conversation_manager = SlidingWindowConversationManager(window_size=SLIDING_WINDOW_SIZE)
            logger.info("SlidingWindowConversationManager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize memory session manager: {e}")
            session_manager = None
            conversation_manager = None
    else:
        logger.info("Skipping memory initialization (no MEMORY_ID, session_id, or actor_id)")
        session_manager = None
        conversation_manager = None

    try:
        logger.info(f"Creating Agent instance (Model: {BEDROCK_MODEL_ID}, Max Tokens: {BEDROCK_MODEL_MAX_TOKENS})")
        agent = Agent(
            model=BedrockModel(model_id=BEDROCK_MODEL_ID, region_name=BEDROCK_MODEL_REGION, max_tokens=BEDROCK_MODEL_MAX_TOKENS),
            system_prompt=system_prompt,
            tools=[use_aws, current_time],
            session_manager=session_manager,
            conversation_manager=conversation_manager
        )
        logger.info("AWS CloudOps Assistant agent created successfully")
        return agent
    except Exception as e:
        logger.error(f"Failed to create AWS CloudOps Assistant agent: {str(e)}")
        raise

app = FastAPI(title="AWS CloudOps Assistant API", version="1.0.0")

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
    port = int(os.getenv("STRANDS_AGENT_PORT", 8080))
    logger.info("=" * 60)
    logger.info("[Step 1/3]: Starting AWS CloudOps Assistant API server")
    logger.info(f"Port: {port}")
    logger.info(f"Bedrock Model: {BEDROCK_MODEL_ID} (Region: {BEDROCK_MODEL_REGION})")
    logger.info(f"Agent Version: {STRANDS_AGENT_VERSION}")
    if MEMORY_ID:
        logger.info(f"AgentCore Memory: {MEMORY_ID[:20]}... (Region: {MEMORY_REGION})")
    else:
        logger.info("AgentCore Memory: Not configured")
    logger.info("=" * 60)
    try:
        logger.info("Initializing default agent on startup")
        default_agent = create_aws_assistant_agent()
        logger.info("[Step 2/3]: Default agent initialized successfully on startup")
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
    else:
        logger.debug("Default agent already initialized")
    
    logger.info(f"Health check complete. Status: {health_status}, Agent initialized: {agent_initialized}")
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
    
    logger.info(f"[Step 3/3]: Invocation request received: stream={request.stream}, prompt_length={len(request.prompt)}, session_id={request.session_id}")
    
    if request.session_id and request.actor_id and MEMORY_ID:
        logger.info(f"Session ID: {request.session_id[:20]}..., Actor ID: {request.actor_id[:20]}...")
        logger.info("Creating session-specific agent with memory")
        current_agent = create_aws_assistant_agent(request.session_id, request.actor_id)
        logger.info("Session-specific agent created")
    else:
        logger.info("Using default agent (no memory/session context)")
        if not default_agent:
            logger.info("Default agent not initialized, creating now")
            default_agent = create_aws_assistant_agent()
        current_agent = default_agent
        logger.info("Default agent ready")

    # Handle streaming response
    if request.stream:
        logger.info("Processing streaming invocation")
        async def generate_stream():
            try:
                logger.info("Starting agent stream_async")
                chunk_count = 0
                async for event in current_agent.stream_async(request.prompt):
                    chunk = None

                    if isinstance(event, dict):
                        if "contentBlockDelta" in event:
                            delta = event["contentBlockDelta"].get("delta", {})
                            if isinstance(delta, dict) and "text" in delta:
                                chunk = delta["text"]
                            elif isinstance(delta, str):
                                chunk = delta

                        elif "delta" in event:
                            delta = event["delta"]
                            if isinstance(delta, dict) and ("toolUse" in delta or "toolResult" in delta):
                                continue
                            
                            if isinstance(delta, dict) and "text" in delta:
                                chunk = delta["text"]
                            elif isinstance(delta, str):
                                chunk = delta
                            else:
                                chunk = str(delta)

                        elif "data" in event:
                            data = event["data"]
                            if isinstance(data, dict) and ("toolUse" in data or "toolResult" in data):
                                continue
                            chunk = str(data)
                        
                        elif "text" in event:
                            chunk = event["text"]
                        
                        elif "content" in event:
                            content = event["content"]
                            if isinstance(content, str):
                                chunk = content
                            elif isinstance(content, list) and len(content) > 0:
                                first_item = content[0]
                                if isinstance(first_item, dict) and "text" in first_item:
                                    chunk = first_item["text"]
                                else:
                                    chunk = str(first_item)
                            else:
                                chunk = str(content)
                    
                    elif isinstance(event, str):
                        chunk = event
                    
                    if chunk is not None:
                        chunk_count += 1
                        if chunk_count == 1:
                            logger.info("First chunk received from agent stream")
                        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                
                logger.info(f"Stream processing complete. Total chunks: {chunk_count}")
                yield f"data: {json.dumps({'done': True})}\n\n"
                logger.info("Streaming invocation completed successfully")
            except Exception as e:
                logger.error(f"Error during streaming invocation: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        logger.info("Returning streaming response")
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
            logger.info("Invoking agent (non-streaming)")
            response = current_agent(request.prompt)
            logger.info("Agent response received, extracting text")
            response_text = _extract_response_text(response)
            logger.info(f"Response text extracted. Length: {len(response_text)}")
            logger.info("Non-streaming invocation completed successfully")
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