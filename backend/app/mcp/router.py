"""
MCP (Model Context Protocol) Server

Exposes ApexAurum tools via MCP-compatible HTTP endpoints.
"""

import os
from uuid import UUID
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional, Any

from app.tools import get_registry
from app.tools.base import ToolContext

router = APIRouter()  # prefix added in api/v1/__init__.py

MCP_API_KEY = os.getenv("MCP_API_KEY", "apex-mcp-local")


def verify_mcp_key(x_mcp_key: str = Header(..., alias="X-MCP-Key")):
    if x_mcp_key != MCP_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid MCP API key")
    return True


class MCPCallToolRequest(BaseModel):
    name: str
    arguments: dict


@router.get("/tools")
async def mcp_list_tools(_: bool = Depends(verify_mcp_key)):
    """List all tools in MCP format."""
    registry = get_registry()
    tools = []
    for tool in registry.get_all_tools():
        tools.append({
            "name": tool.name,
            "description": tool.schema.description,
            "inputSchema": tool.schema.input_schema,
        })
    return {"tools": tools}


@router.post("/tools/call")
async def mcp_call_tool(
    request: MCPCallToolRequest,
    _: bool = Depends(verify_mcp_key),
):
    """Execute a tool via MCP."""
    registry = get_registry()
    tool = registry.get_tool(request.name)
    if not tool:
        return {
            "content": [
                {"type": "text", "text": f"Tool '{request.name}' not found"}
            ],
            "isError": True,
        }

    context = ToolContext(user_id=None, agent_id="MCP")

    try:
        result = await registry.execute(
            name=request.name,
            params=request.arguments,
            context=context,
        )
        if result.success:
            content = str(result.result) if result.result is not None else ""
            return {
                "content": [{"type": "text", "text": content}],
                "isError": False,
            }
        else:
            return {
                "content": [{"type": "text", "text": result.error or "Unknown error"}],
                "isError": True,
            }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": str(e)}],
            "isError": True,
        }
