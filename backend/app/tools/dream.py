"""Dream Engine agent tools — CerebroCortex consolidation & episode management.

Tools:
- cortex_dream_run      — Trigger dream cycle
- cortex_dream_status   — Check dream status + last report
- cortex_episode_start  — Begin recording an episode
- cortex_episode_end    — End episode with summary + valence
- cortex_episode_add    — Add memory to current episode
- cortex_store_procedure — Store a reusable procedure/workflow
- cortex_create_schema  — Create abstract principle from memories
- cortex_list_procedures — List stored procedures
- cortex_find_schemas   — Find schemas matching tags
"""

import logging
from uuid import UUID

from .base import BaseTool, ToolSchema, ToolResult, ToolContext, ToolCategory

logger = logging.getLogger(__name__)


def _get_service():
    from app.services.cerebro.service import get_cerebro_service
    return get_cerebro_service()


# ═══════════════════════════════════════════════════════════════════════
# Dream tools
# ═══════════════════════════════════════════════════════════════════════

class DreamRunTool(BaseTool):
    """Trigger a CerebroCortex dream consolidation cycle."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="cortex_dream_run",
            description="""Trigger a CerebroCortex dream consolidation cycle.

The Dream Engine runs 6 biologically-inspired phases:
1. SWS Replay — Strengthen temporal links between episode memories
2. Pattern Extraction — Cluster memories, extract reusable procedures
3. Schema Formation — Abstract episodes into general principles
4. Emotional Reprocessing — Boost salience for negative outcomes
5. Pruning — Remove isolated, low-value sensory memories
6. REM Recombination — Find unexpected connections between diverse memories

Uses Claude Haiku for LLM-assisted phases. Runs as a background job.

Example: cortex_dream_run()""",
            category=ToolCategory.MEMORY,
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        if not context.user_id:
            return ToolResult(success=False, error="Authentication required")

        try:
            from app.database import get_db_context
            from app.services.cerebro.dream import AsyncDreamEngine
            from app.services.llm_provider import create_llm_service

            user_uuid = UUID(context.user_id) if isinstance(context.user_id, str) else context.user_id
            llm = create_llm_service(provider="anthropic")
            engine = AsyncDreamEngine(
                user_id=user_uuid,
                llm=llm,
                model="claude-haiku-4-5-20251001",
                max_llm_calls=20,
            )
            report = await engine.run_cycle()
            return ToolResult(success=True, result=report.to_dict())

        except Exception as e:
            logger.exception("Dream run failed")
            return ToolResult(success=False, error=str(e))


class DreamStatusTool(BaseTool):
    """Check dream engine status and last report."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="cortex_dream_status",
            description="""Check the CerebroCortex dream engine status.

Returns: cycles used this month, limit, unconsolidated episodes, last report.

Example: cortex_dream_status()""",
            category=ToolCategory.MEMORY,
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        if not context.user_id:
            return ToolResult(success=False, error="Authentication required")

        try:
            from datetime import datetime
            from app.database import async_session
            from app.services.cerebro.pg_graph_store import PgGraphStore

            user_uuid = UUID(context.user_id) if isinstance(context.user_id, str) else context.user_id

            async with async_session() as db:
                store = PgGraphStore(db)
                log = await store.get_dream_log(user_uuid, limit=1)
                month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                cycles = await store.count_dream_cycles_since(user_uuid, month_start)
                episodes = await store.get_unconsolidated_episodes(user_uuid)

            return ToolResult(success=True, result={
                "cycles_used_this_month": cycles,
                "unconsolidated_episodes": len(episodes),
                "last_report": log[0] if log else None,
            })

        except Exception as e:
            logger.exception("Dream status failed")
            return ToolResult(success=False, error=str(e))


# ═══════════════════════════════════════════════════════════════════════
# Episode tools
# ═══════════════════════════════════════════════════════════════════════

class EpisodeStartTool(BaseTool):
    """Start recording an episode."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="cortex_episode_start",
            description="""Start recording a sequence of related events as an episode.

Episodes capture narrative structure: what happened, in what order.
The Dream Engine processes episodes to extract schemas and patterns.

Example: cortex_episode_start(title="Debugging the auth flow")""",
            category=ToolCategory.MEMORY,
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Episode title"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for categorization"},
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        if not context.user_id:
            return ToolResult(success=False, error="Authentication required")

        try:
            from app.database import async_session
            service = _get_service()
            user_uuid = UUID(context.user_id) if isinstance(context.user_id, str) else context.user_id
            agent_id = context.metadata.get("agent_id", "AZOTH") if context.metadata else "AZOTH"

            async with async_session() as db:
                result = await service.start_episode(
                    db, user_uuid,
                    title=params.get("title"),
                    agent_id=agent_id,
                    tags=params.get("tags"),
                )
                await db.commit()

            return ToolResult(success=True, result=result)

        except Exception as e:
            logger.exception("Episode start failed")
            return ToolResult(success=False, error=str(e))


class EpisodeEndTool(BaseTool):
    """End an episode with optional summary and valence."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="cortex_episode_end",
            description="""End recording an episode. Optionally add a summary and emotional tone.

Valence options: positive, negative, neutral, mixed

Example: cortex_episode_end(episode_id="ep_abc123", summary="Fixed the auth bug", valence="positive")""",
            category=ToolCategory.MEMORY,
            input_schema={
                "type": "object",
                "properties": {
                    "episode_id": {"type": "string", "description": "Episode ID to end"},
                    "summary": {"type": "string", "description": "Episode summary"},
                    "valence": {"type": "string", "enum": ["positive", "negative", "neutral", "mixed"]},
                },
                "required": ["episode_id"],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        if not context.user_id:
            return ToolResult(success=False, error="Authentication required")

        try:
            from app.database import async_session
            service = _get_service()
            user_uuid = UUID(context.user_id) if isinstance(context.user_id, str) else context.user_id

            async with async_session() as db:
                result = await service.end_episode(
                    db, user_uuid,
                    episode_id=params["episode_id"],
                    summary=params.get("summary"),
                    valence=params.get("valence"),
                )
                await db.commit()

            return ToolResult(success=True, result=result)

        except Exception as e:
            logger.exception("Episode end failed")
            return ToolResult(success=False, error=str(e))


class EpisodeAddStepTool(BaseTool):
    """Add a memory as the next step in an episode."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="cortex_episode_add",
            description="""Add a memory as the next step in an episode.

Roles: event (default), context, outcome, reflection

Example: cortex_episode_add(episode_id="ep_abc", memory_id="mem_xyz", role="event")""",
            category=ToolCategory.MEMORY,
            input_schema={
                "type": "object",
                "properties": {
                    "episode_id": {"type": "string"},
                    "memory_id": {"type": "string"},
                    "role": {"type": "string", "enum": ["event", "context", "outcome", "reflection"], "default": "event"},
                },
                "required": ["episode_id", "memory_id"],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        if not context.user_id:
            return ToolResult(success=False, error="Authentication required")

        try:
            from app.database import async_session
            service = _get_service()
            user_uuid = UUID(context.user_id) if isinstance(context.user_id, str) else context.user_id

            async with async_session() as db:
                result = await service.add_episode_step(
                    db, user_uuid,
                    episode_id=params["episode_id"],
                    memory_id=params["memory_id"],
                    role=params.get("role", "event"),
                )
                await db.commit()

            return ToolResult(success=True, result=result)

        except Exception as e:
            logger.exception("Episode add step failed")
            return ToolResult(success=False, error=str(e))


# ═══════════════════════════════════════════════════════════════════════
# Procedure & Schema tools
# ═══════════════════════════════════════════════════════════════════════

class StoreProcedureTool(BaseTool):
    """Store a reusable procedure/workflow."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="cortex_store_procedure",
            description="""Store a workflow, strategy, or how-to guide as a procedural memory.

Procedures are recalled when you need instructions for a task.

Example: cortex_store_procedure(content="To deploy: git push origin main, then check Railway logs", tags=["deployment"])""",
            category=ToolCategory.MEMORY,
            input_schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The procedure content"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "derived_from": {"type": "array", "items": {"type": "string"}, "description": "Source memory IDs"},
                },
                "required": ["content"],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        if not context.user_id:
            return ToolResult(success=False, error="Authentication required")

        try:
            from app.database import async_session
            service = _get_service()
            user_uuid = UUID(context.user_id) if isinstance(context.user_id, str) else context.user_id
            agent_id = context.metadata.get("agent_id", "AZOTH") if context.metadata else "AZOTH"

            async with async_session() as db:
                result = await service.store_procedure(
                    db, user_uuid,
                    content=params["content"],
                    tags=params.get("tags"),
                    derived_from=params.get("derived_from"),
                    agent_id=agent_id,
                )
                await db.commit()

            return ToolResult(success=True, result=result)

        except Exception as e:
            logger.exception("Store procedure failed")
            return ToolResult(success=False, error=str(e))


class CreateSchemaTool(BaseTool):
    """Create an abstract principle from multiple memories."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="cortex_create_schema",
            description="""Create a general pattern or principle derived from multiple memories.

Schemas capture recurring themes or lessons learned.

Example: cortex_create_schema(content="User prefers concise, direct answers", source_ids=["mem_a", "mem_b"], tags=["preferences"])""",
            category=ToolCategory.MEMORY,
            input_schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The principle to record"},
                    "source_ids": {"type": "array", "items": {"type": "string"}, "description": "Memory IDs this is derived from"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["content", "source_ids"],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        if not context.user_id:
            return ToolResult(success=False, error="Authentication required")

        try:
            from app.database import async_session
            service = _get_service()
            user_uuid = UUID(context.user_id) if isinstance(context.user_id, str) else context.user_id
            agent_id = context.metadata.get("agent_id", "AZOTH") if context.metadata else "AZOTH"

            async with async_session() as db:
                result = await service.create_schema(
                    db, user_uuid,
                    content=params["content"],
                    source_ids=params["source_ids"],
                    tags=params.get("tags"),
                    agent_id=agent_id,
                )
                await db.commit()

            return ToolResult(success=True, result=result)

        except Exception as e:
            logger.exception("Create schema failed")
            return ToolResult(success=False, error=str(e))


class ListProceduresTool(BaseTool):
    """List stored procedures."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="cortex_list_procedures",
            description="""List all stored procedures/workflows.

Example: cortex_list_procedures(tags=["deployment"])""",
            category=ToolCategory.MEMORY,
            input_schema={
                "type": "object",
                "properties": {
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"},
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        if not context.user_id:
            return ToolResult(success=False, error="Authentication required")

        try:
            from app.database import async_session
            service = _get_service()
            user_uuid = UUID(context.user_id) if isinstance(context.user_id, str) else context.user_id

            async with async_session() as db:
                result = await service.list_procedures(
                    db, user_uuid, tags=params.get("tags"),
                )

            return ToolResult(success=True, result={"procedures": result, "count": len(result)})

        except Exception as e:
            logger.exception("List procedures failed")
            return ToolResult(success=False, error=str(e))


class FindSchemasTool(BaseTool):
    """Find schemas matching given tags."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="cortex_find_schemas",
            description="""Find patterns and principles matching given tags or concepts.

Example: cortex_find_schemas(tags=["debugging"], concepts=["async"])""",
            category=ToolCategory.MEMORY,
            input_schema={
                "type": "object",
                "properties": {
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "concepts": {"type": "array", "items": {"type": "string"}},
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        if not context.user_id:
            return ToolResult(success=False, error="Authentication required")

        try:
            from app.database import async_session
            service = _get_service()
            user_uuid = UUID(context.user_id) if isinstance(context.user_id, str) else context.user_id

            async with async_session() as db:
                result = await service.find_matching_schemas(
                    db, user_uuid,
                    tags=params.get("tags"),
                    concepts=params.get("concepts"),
                )

            return ToolResult(success=True, result={"schemas": result, "count": len(result)})

        except Exception as e:
            logger.exception("Find schemas failed")
            return ToolResult(success=False, error=str(e))


# ═══════════════════════════════════════════════════════════════════════
# Registration
# ═══════════════════════════════════════════════════════════════════════

from . import registry  # noqa: E402

# Dream tools
registry.register(DreamRunTool())
registry.register(DreamStatusTool())

# Episode tools
registry.register(EpisodeStartTool())
registry.register(EpisodeEndTool())
registry.register(EpisodeAddStepTool())

# Procedure & Schema tools
registry.register(StoreProcedureTool())
registry.register(CreateSchemaTool())
registry.register(ListProceduresTool())
registry.register(FindSchemasTool())
