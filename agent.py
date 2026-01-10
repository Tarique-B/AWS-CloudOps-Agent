import json
import logging
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from strands import Agent
from strands_tools import use_aws, current_time
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

## Response Guidelines
- Always respond in markdown format
- Provide clear, structured explanations
- Explain what you're doing before executing actions
- Report errors clearly with actionable guidance
- Actively recall and consider the user's preferences and known facts to personalize assistance
- Use code blocks for AWS CLI commands, API calls, and configuration examples
- Include relevant AWS service documentation links when helpful

Be helpful, professional, and maintain strict focus on AWS cloud operations."""

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
            tools=[use_aws, current_time],
            session_manager=session_manager
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
    logger.info("Starting up AWS CloudOps Assistant API server")
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
    
    if request.session_id and request.actor_id and MEMORY_ID:
        logger.info("Creating session-specific agent with memory")
        current_agent = create_aws_assistant_agent(request.session_id, request.actor_id)
    else:
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
    port = int(os.getenv("PORT", 8080))
    logger.info(f"Starting AWS CloudOps Assistant API server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
