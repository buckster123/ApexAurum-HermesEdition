"""
Hermes Agent Bridge - API Endpoints

Exposes ApexAurum tools to Hermes agent via HTTP.
"""

import os
from uuid import UUID, uuid5, NAMESPACE_DNS
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional, Any

from app.tools import get_registry
from app.tools.base import ToolContext

router = APIRouter()

HERMES_API_KEY = os.getenv("HERMES_API_KEY", "apex-hermes-local")


def _to_uuid(user_id: Optional[str]) -> Optional[UUID]:
    """Convert a string user_id to UUID. If not a valid UUID, generate a deterministic one."""
    if not user_id:
        return None
    try:
        return UUID(user_id)
    except ValueError:
        # Generate deterministic UUID from string so it's stable across calls
        return uuid5(NAMESPACE_DNS, user_id)


def verify_hermes_key(x_hermes_key: str = Header(..., alias="X-Hermes-Key")):
    if x_hermes_key != HERMES_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid Hermes API key")
    return True


class ToolExecuteRequest(BaseModel):
    tool_name: str
    params: dict
    user_id: Optional[str] = "hermes"
    agent_id: Optional[str] = "HERMES"


class ToolExecuteResponse(BaseModel):
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None


@router.get("/tools")
async def list_tools(_: bool = Depends(verify_hermes_key)):
    """List all available tools in Hermes-compatible format."""
    registry = get_registry()
    tools = []
    for tool in registry.get_all_tools():
        tools.append({
            "name": tool.name,
            "description": tool.schema.description,
            "category": tool.schema.category,
            "parameters": tool.schema.input_schema,
            "requires_confirmation": tool.schema.requires_confirmation,
            "requires_auth": tool.schema.requires_auth,
        })
    return {"tools": tools}


@router.post("/execute", response_model=ToolExecuteResponse)
async def execute_tool(
    request: ToolExecuteRequest,
    _: bool = Depends(verify_hermes_key),
):
    """Execute a tool by name with parameters."""
    registry = get_registry()
    tool = registry.get_tool(request.tool_name)
    if not tool:
        return ToolExecuteResponse(
            success=False,
            error=f"Tool '{request.tool_name}' not found",
        )

    context = ToolContext(
        user_id=_to_uuid(request.user_id),
        agent_id=request.agent_id,
    )

    try:
        result = await registry.execute(
            name=request.tool_name,
            params=request.params,
            context=context,
        )
        return ToolExecuteResponse(
            success=result.success,
            result=result.result if result.success else None,
            error=result.error if not result.success else None,
            execution_time_ms=result.execution_time_ms,
        )
    except Exception as e:
        return ToolExecuteResponse(
            success=False,
            error=str(e),
        )
