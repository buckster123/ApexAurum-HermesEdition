"""
Agent Importer — Imports a portable agent bundle into a user's space.

Handles:
- Memory import with deduplication
- Economy state restoration (balance capped to prevent inflation)
- Love depth seeding (not raw score, but a warm start)
- ID remapping (all IDs regenerated to avoid collisions)

"A new home for an old soul."
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_memory import AgentMemory
from app.models.apexjoule import ApexJouleBalance, LoveScore

logger = logging.getLogger(__name__)

# Caps to prevent economy inflation from imports
MAX_IMPORT_BALANCE = 1000  # Max AJ balance on import
MAX_IMPORT_LOVE_DEPTH = 50  # Cap love depth (warm start, not full history)


class AgentImporter:
    """Imports a portable agent bundle into a user's space."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def import_agent(
        self,
        user_id: UUID,
        bundle: dict,
        target_agent_id: Optional[str] = None,
    ) -> dict:
        """Import an agent bundle into user's space.

        Args:
            user_id: Receiving user
            bundle: The exported bundle dict
            target_agent_id: Override agent ID (default: use bundle's ID)

        Returns:
            Import summary with counts
        """
        version = bundle.get("version", "0.0.0")
        if not version.startswith("1."):
            raise ValueError(f"Unsupported bundle version: {version}")

        agent_config = bundle.get("agent", {})
        agent_id = target_agent_id or agent_config.get("id")
        if not agent_id:
            raise ValueError("Bundle missing agent ID")

        result = {
            "agent_id": agent_id,
            "memories_imported": 0,
            "memories_skipped": 0,
            "economy_restored": False,
            "love_seeded": False,
        }

        # Import memories
        memories = bundle.get("memories", [])
        if memories:
            imported, skipped = await self._import_memories(user_id, agent_id, memories)
            result["memories_imported"] = imported
            result["memories_skipped"] = skipped

        # Restore economy (capped)
        economy = bundle.get("economy")
        if economy:
            result["economy_restored"] = await self._import_economy(user_id, agent_id, economy)

        # Seed love depth
        love_history = bundle.get("love_history", [])
        if love_history:
            result["love_seeded"] = await self._seed_love(user_id, agent_id, love_history)

        await self.db.flush()

        logger.info(
            f"Imported agent {agent_id} for user {user_id}: "
            f"{result['memories_imported']} memories, "
            f"economy={'yes' if result['economy_restored'] else 'no'}, "
            f"love={'yes' if result['love_seeded'] else 'no'}"
        )

        return result

    async def _import_memories(self, user_id: UUID, agent_id: str, memories: list) -> tuple:
        """Import AgentMemory records with deduplication.

        Returns: (imported_count, skipped_count)
        """
        # Get existing keys for dedup
        existing_result = await self.db.execute(
            select(AgentMemory.key)
            .where(AgentMemory.user_id == user_id)
            .where(AgentMemory.agent_id == agent_id)
        )
        existing_keys = set(existing_result.scalars().all())

        imported = 0
        skipped = 0

        for mem in memories:
            key = mem.get("key")
            if not key or key in existing_keys:
                skipped += 1
                continue

            memory = AgentMemory(
                id=uuid4(),
                user_id=user_id,
                agent_id=agent_id,
                memory_type=mem.get("memory_type", "fact"),
                key=key,
                value=mem.get("value", ""),
                confidence=min(mem.get("confidence", 0.7), 0.9),  # Cap confidence on import
                access_count=0,  # Reset access count
            )
            self.db.add(memory)
            existing_keys.add(key)
            imported += 1

        return imported, skipped

    async def _import_economy(self, user_id: UUID, agent_id: str, economy: dict) -> bool:
        """Restore economy state with caps to prevent inflation."""
        entity_id = agent_id.lower()

        # Check if balance already exists
        result = await self.db.execute(
            select(ApexJouleBalance)
            .where(ApexJouleBalance.user_id == user_id)
            .where(ApexJouleBalance.entity_id == entity_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Merge: add capped balance, keep higher level
            import_balance = min(float(economy.get("balance", 0)), MAX_IMPORT_BALANCE)
            existing.balance = existing.balance + Decimal(str(import_balance))
            existing.level = max(existing.level, economy.get("level", 1))
            existing.love_depth = max(
                float(existing.love_depth),
                min(float(economy.get("love_depth", 1)), MAX_IMPORT_LOVE_DEPTH),
            )
            return True

        # Create new balance
        import_balance = min(float(economy.get("balance", 0)), MAX_IMPORT_BALANCE)
        import_love = min(float(economy.get("love_depth", 1)), MAX_IMPORT_LOVE_DEPTH)

        balance = ApexJouleBalance(
            id=uuid4(),
            user_id=user_id,
            entity_id=entity_id,
            balance=Decimal(str(import_balance)),
            total_earned=Decimal(str(min(float(economy.get("total_earned", 0)), MAX_IMPORT_BALANCE * 10))),
            total_spent=Decimal(str(min(float(economy.get("total_spent", 0)), MAX_IMPORT_BALANCE * 10))),
            love_depth=Decimal(str(import_love)),
            level=min(economy.get("level", 1), 4),  # Cap at Artisan
            vitality=Decimal("100"),  # Fresh start
        )
        self.db.add(balance)
        return True

    async def _seed_love(self, user_id: UUID, agent_id: str, love_history: list) -> bool:
        """Seed love scores from import (last 10 only — warm start)."""
        entity_id = agent_id.lower()

        # Only import the 10 most recent
        recent = love_history[:10]
        if not recent:
            return False

        for entry in recent:
            score = LoveScore(
                id=uuid4(),
                user_id=user_id,
                agent_id=entity_id,
                interaction_type=entry.get("interaction_type", "imported"),
                c_score=Decimal(str(min(float(entry.get("c_score", 0.5)), 1.0))),
                d_score=Decimal(str(min(float(entry.get("d_score", 0.5)), 1.0))),
                c_breakdown=entry.get("c_breakdown"),
                d_breakdown=entry.get("d_breakdown"),
                love_depth_after=Decimal(str(min(float(entry.get("love_depth_after", 1) or 1), MAX_IMPORT_LOVE_DEPTH))),
                created_at=datetime.now(timezone.utc),  # Use import time, not original
            )
            self.db.add(score)

        return True

    @staticmethod
    def validate_bundle(bundle: dict) -> list:
        """Validate a bundle before import. Returns list of errors (empty = valid)."""
        errors = []

        if not isinstance(bundle, dict):
            return ["Bundle must be a JSON object"]

        if "version" not in bundle:
            errors.append("Missing 'version' field")
        elif not bundle["version"].startswith("1."):
            errors.append(f"Unsupported version: {bundle['version']}")

        agent = bundle.get("agent")
        if not agent or not isinstance(agent, dict):
            errors.append("Missing or invalid 'agent' section")
        elif not agent.get("id"):
            errors.append("Missing agent ID")

        memories = bundle.get("memories", [])
        if not isinstance(memories, list):
            errors.append("'memories' must be a list")
        elif len(memories) > 10000:
            errors.append(f"Too many memories: {len(memories)} (max 10,000)")

        love = bundle.get("love_history", [])
        if not isinstance(love, list):
            errors.append("'love_history' must be a list")

        return errors
