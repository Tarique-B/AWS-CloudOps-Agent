"""
Pydantic models for API request/response schemas
"""
from pydantic import BaseModel
from typing import Optional


class InvocationRequest(BaseModel):
    """Request model for agent invocations"""
    prompt: str
    stream: Optional[bool] = True


class PingResponse(BaseModel):
    """Response model for ping/health check endpoint"""
    status: str
    model_id: str
    agent_initialized: bool


class InvocationResponse(BaseModel):
    """Response model for non-streaming invocations"""
    response: str
    status: str

