"""
Agent Exporter — Serializes an agent as a portable JSON bundle.

The bundle contains everything needed to recreate the agent on any
ApexAurum instance:

- Agent config (ID, type, system prompt)
- Memory graph (AgentMemory key-value pairs, NO embeddings)
- Economy state (AJ balance, love depth, level)
- Love history (C/D scores)

"An entity, not a workflow."
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_memory import AgentMemory
# # from app.models.apexjoule import ApexJouleBalance, LoveScore  # DELETED - commercial module removed

logger = logging.getLogger(__name__)

# Bundle format version — increment when schema changes
BUNDLE_VERSION = "1.0.0"


class AgentExporter:
    """Exports a single agent's full state as a portable bundle."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def export_agent(
        self,
        user_id: UUID,
        agent_id: str,
        include_memories: bool = True,
        include_economy: bool = True,
        include_love: bool = True,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """Export agent as a JSON-serializable bundle.

        Args:
            user_id: Owner of the agent
            agent_id: Agent identifier (e.g., "AZOTH", "custom_abc")
            include_memories: Include AgentMemory records
            include_economy: Include AJ balance/level/vitality
            include_love: Include LoveScore history
            system_prompt: Override system prompt (if None, not included)

        Returns:
            Complete portable bundle dict
        """
        bundle = {
            "version": BUNDLE_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "agent": {
                "id": agent_id,
                "system_prompt": system_prompt,
            },
        }

        if include_memories:
            bundle["memories"] = await self._export_memories(user_id, agent_id)

        if include_economy:
            bundle["economy"] = await self._export_economy(user_id, agent_id)

        if include_love:
            bundle["love_history"] = await self._export_love(user_id, agent_id)

        # Stats summary
        bundle["stats"] = {
            "memory_count": len(bundle.get("memories", [])),
            "love_entries": len(bundle.get("love_history", [])),
            "has_economy": "economy" in bundle,
        }

        logger.info(
            f"Exported agent {agent_id} for user {user_id}: "
            f"{bundle['stats']['memory_count']} memories, "
            f"{bundle['stats']['love_entries']} love entries"
        )

        return bundle

    async def _export_memories(self, user_id: UUID, agent_id: str) -> list:
        """Export all AgentMemory records for this agent."""
        result = await self.db.execute(
            select(AgentMemory)
            .where(AgentMemory.user_id == user_id)
            .where(AgentMemory.agent_id == agent_id)
            .order_by(AgentMemory.created_at)
        )
        memories = result.scalars().all()

        return [
            {
                "memory_type": m.memory_type,
                "key": m.key,
                "value": m.value,
                "confidence": m.confidence,
                "access_count": m.access_count,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in memories
        ]

    async def _export_economy(self, user_id: UUID, agent_id: str) -> dict:
        """Export AJ economy state for the agent. (STUBBED — commercial module removed)"""
        # NOTE: ApexJouleBalance model deleted
        # result = await self.db.execute(
        #     select(ApexJouleBalance)
        #     .where(ApexJouleBalance.user_id == user_id)
        #     .where(ApexJouleBalance.entity_id == agent_id.lower())
        # )
        # balance = result.scalar_one_or_none()
        #
        # if not balance:
        #     return {"balance": 0, "total_earned": 0, "total_spent": 0, "level": 1, "love_depth": 1, "vitality": 100}
        #
        # return {
        #     "balance": 0,  # Monetary fields stripped — prevents AJ duplication
        #     "total_earned": 0,
        #     "total_spent": 0,
        #     "level": balance.level,
        #     "love_depth": float(balance.love_depth),
        #     "vitality": float(balance.vitality),
        # }
        return {"balance": 0, "total_earned": 0, "total_spent": 0, "level": 1, "love_depth": 1, "vitality": 100}

    async def _export_love(self, user_id: UUID, agent_id: str) -> list:
        """Export love score history (last 100 entries). (STUBBED — commercial module removed)"""
        # NOTE: LoveScore model deleted
        # result = await self.db.execute(
        #     select(LoveScore)
        #     .where(LoveScore.user_id == user_id)
        #     .where(LoveScore.agent_id == agent_id.lower())
        #     .order_by(LoveScore.created_at.desc())
        #     .limit(100)
        # )
        # scores = result.scalars().all()
        #
        # return [
        #     {
        #         "interaction_type": s.interaction_type,
        #         "c_score": float(s.c_score),
        #         "d_score": float(s.d_score),
        #         "c_breakdown": s.c_breakdown,
        #         "d_breakdown": s.d_breakdown,
        #         "love_depth_after": float(s.love_depth_after) if s.love_depth_after else None,
        #         "created_at": s.created_at.isoformat() if s.created_at else None,
        #     }
        #     for s in scores
        # ]
        return []
