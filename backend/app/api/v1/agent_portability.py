"""
Agent Portability API — Export/Import agent bundles.

Endpoints:
- GET  /portability/export/{agent_id}  — Download agent bundle as JSON
- POST /portability/import              — Upload and import an agent bundle
- POST /portability/validate            — Validate a bundle before importing
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.auth.deps import get_current_user
# from app.services.portability.exporter import AgentExporter
# from app.services.portability.importer import AgentImporter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portability", tags=["Agent Portability"])

# Valid native agent IDs
NATIVE_AGENTS = {"azoth", "kether", "vajra", "elysian"}


class ImportRequest(BaseModel):
    bundle: dict = Field(..., description="The agent bundle JSON")
    target_agent_id: Optional[str] = Field(default=None, description="Override the agent ID on import")


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/export/{agent_id}")
async def export_agent(
    agent_id: str,
    include_memories: bool = True,
    include_economy: bool = True,
    include_love: bool = True,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export an agent as a portable JSON bundle.

    Downloads the agent's full state: memories, economy, love history.
    The bundle can be imported on any ApexAurum instance.
    """
    agent_id_lower = agent_id.lower()

    # Load system prompt for native agents
    system_prompt = None
    if agent_id_lower in NATIVE_AGENTS:
        try:
            from app.api.v1.chat import get_agent_system_prompt
            system_prompt = get_agent_system_prompt(agent_id_lower)
        except Exception:
            pass  # Non-fatal: prompt not included

    try:
        exporter = AgentExporter(db)
        bundle = await exporter.export_agent(
            user_id=user.id,
            agent_id=agent_id_lower,
            include_memories=include_memories,
            include_economy=include_economy,
            include_love=include_love,
            system_prompt=system_prompt,
        )

        return JSONResponse(
            content=bundle,
            headers={
                "Content-Disposition": f'attachment; filename="{agent_id_lower}-bundle.json"',
            },
        )
    except Exception as e:
        logger.error(f"Export failed for {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# IMPORT
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/import")
async def import_agent(
    request: ImportRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Import an agent bundle into your space.

    Memories are deduplicated. Economy values are capped to prevent inflation.
    Love history is seeded with the last 10 entries for a warm start.
    """
    bundle = request.bundle

    # Validate first
    errors = AgentImporter.validate_bundle(bundle)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": errors},
        )

    try:
        importer = AgentImporter(db)
        result = await importer.import_agent(
            user_id=user.id,
            bundle=bundle,
            target_agent_id=request.target_agent_id,
        )
        await db.commit()

        return {
            "success": True,
            "message": f"Agent '{result['agent_id']}' imported successfully.",
            **result,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Import failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATE
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/validate")
async def validate_bundle(
    request: ImportRequest,
    user: User = Depends(get_current_user),
):
    """Validate an agent bundle without importing.

    Returns validation errors (if any) and a preview of what will be imported.
    """
    bundle = request.bundle
    errors = AgentImporter.validate_bundle(bundle)

    if errors:
        return {"valid": False, "errors": errors}

    # Preview
    agent = bundle.get("agent", {})
    memories = bundle.get("memories", [])
    economy = bundle.get("economy", {})
    love = bundle.get("love_history", [])

    return {
        "valid": True,
        "preview": {
            "agent_id": agent.get("id"),
            "has_system_prompt": bool(agent.get("system_prompt")),
            "memory_count": len(memories),
            "memory_types": list(set(m.get("memory_type", "unknown") for m in memories)),
            "economy_balance": economy.get("balance", 0),
            "economy_level": economy.get("level", 1),
            "love_entries": len(love),
        },
    }
