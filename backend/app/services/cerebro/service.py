"""CerebroCortexService - Async orchestrator for the CerebroCortex memory engine.

Coordinates gating, enrichment, emotion analysis, storage, and recall
using PostgreSQL as the backend.
"""

import logging
import os
import time
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.cerebro.activation.decay import compute_current_activation, compute_current_retrievability
from app.cerebro.activation.strength import combined_recall_score, record_access
from app.cerebro.engines.amygdala import AffectEngine
from app.cerebro.engines.temporal import SemanticEngine
from app.cerebro.engines.thalamus import GatingEngine
from app.cerebro.models.activation import RecallResult
from app.cerebro.models.agent import AgentProfile
from app.cerebro.models.episode import Episode, EpisodeStep
from app.cerebro.models.link import AssociativeLink
from app.cerebro.models.memory import MemoryNode
from app.cerebro.types import EmotionalValence, LinkType, MemoryType, Visibility
from app.services.cerebro.pg_graph_store import PgGraphStore
from app.services.cerebro.spreading import spreading_activation

logger = logging.getLogger(__name__)

# Singleton
_cerebro_service: Optional["CerebroCortexService"] = None


def get_cerebro_service() -> "CerebroCortexService":
    """Get or create singleton CerebroCortexService."""
    global _cerebro_service
    if _cerebro_service is None:
        _cerebro_service = CerebroCortexService()
    return _cerebro_service


class CerebroCortexService:
    """Async orchestrator for CerebroCortex memory operations.

    Each method accepts a db session and user_id for multi-tenant isolation.
    Pure-logic engines (gating, semantic, affect) are stateless singletons.
    """

    def __init__(self):
        self._gating = GatingEngine()

    def _store(self, db: AsyncSession) -> PgGraphStore:
        """Create a PgGraphStore bound to the given session."""
        return PgGraphStore(db)

    async def _get_embedding(self, content: str) -> Optional[list[float]]:
        """Generate embedding via EmbeddingService."""
        try:
            from app.services.embedding import get_embedding_service
            embed_service = get_embedding_service()
            return await embed_service.embed(content)
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}")
            return None

    # =========================================================================
    # Remember
    # =========================================================================

    async def remember(
        self,
        db: AsyncSession,
        user_id: UUID,
        content: str,
        memory_type: Optional[str] = None,
        tags: Optional[list[str]] = None,
        salience: Optional[float] = None,
        agent_id: str = "AZOTH",
        visibility: str = "shared",
        session_id: Optional[str] = None,
        conversation_thread: Optional[str] = None,
        responding_to: Optional[list[str]] = None,
        related_agents: Optional[list[str]] = None,
        source: str = "user_input",
        context_ids: Optional[list[str]] = None,
    ) -> Optional[dict]:
        """Store a new memory through the full CerebroCortex pipeline.

        Pipeline:
        1. Thalamus gating (type classification, salience estimation)
        2. Deduplication check (async DB)
        3. Semantic enrichment (concept extraction)
        4. Amygdala emotion (valence/arousal)
        5. Generate embedding
        6. Store in PostgreSQL
        7. Auto-link via context_ids

        Returns:
            Dict with memory info, or None if gated out.
        """
        store = self._store(db)

        # Parse memory_type if provided as string
        mt = None
        if memory_type:
            try:
                mt = MemoryType(memory_type)
            except ValueError:
                mt = None

        # Parse visibility
        try:
            vis = Visibility(visibility)
        except ValueError:
            vis = Visibility.SHARED

        # Step 1: Thalamus gating (sync, fast)
        node = self._gating.evaluate_input(
            content=content,
            memory_type=mt,
            tags=tags,
            salience=salience,
            agent_id=agent_id,
            session_id=session_id,
            visibility=vis,
            conversation_thread=conversation_thread,
            responding_to=responding_to,
            related_agents=related_agents,
            source=source,
        )
        if node is None:
            return None

        # Step 2: Deduplication (async DB check)
        existing_id = await store.find_duplicate_content(user_id, content)
        if existing_id:
            existing = await store.get_node(user_id, existing_id)
            if existing:
                new_strength = GatingEngine.strengthen_existing(existing.strength)
                await store.update_node_strength(user_id, existing_id, new_strength)
                return {
                    "id": existing_id,
                    "action": "strengthened",
                    "access_count": new_strength.access_count,
                }

        # Step 3: Semantic enrichment (sync, fast)
        node = SemanticEngine.enrich_node(node)

        # Step 4: Amygdala emotion (sync, fast)
        node = AffectEngine.apply_emotion(node)

        # Step 5: Generate embedding
        # Truncate content for embedding (max 8000 chars)
        embed_content = content[:8000] if len(content) > 8000 else content
        embedding = await self._get_embedding(embed_content)

        # Step 6: Store
        node_id = await store.add_node(user_id, node, embedding=embedding)

        # Step 7: Auto-link via context_ids
        if context_ids:
            for ctx_id in context_ids[:10]:  # Limit to 10 context links
                try:
                    await store.ensure_link(
                        user_id,
                        source_id=ctx_id,
                        target_id=node_id,
                        link_type=LinkType.CONTEXTUAL,
                        weight=0.5,
                        source="encoding",
                        evidence="Co-active during encoding",
                    )
                except Exception as e:
                    logger.debug(f"Auto-link failed for {ctx_id}: {e}")

        return {
            "id": node_id,
            "action": "stored",
            "memory_type": node.metadata.memory_type.value,
            "layer": node.metadata.layer.value,
            "salience": node.metadata.salience,
            "valence": node.metadata.valence.value if hasattr(node.metadata.valence, 'value') else node.metadata.valence,
            "concepts": node.metadata.concepts[:5],
        }

    # =========================================================================
    # Recall
    # =========================================================================

    async def recall(
        self,
        db: AsyncSession,
        user_id: UUID,
        query: str,
        top_k: int = 10,
        memory_types: Optional[list[str]] = None,
        min_salience: float = 0.0,
        visibility: Optional[str] = None,
        agent_id: Optional[str] = None,
        context_ids: Optional[list[str]] = None,
    ) -> list[RecallResult]:
        """Recall memories using vector search + spreading activation + ACT-R scoring.

        Pipeline:
        1. Generate query embedding
        2. pgvector search for top-K seeds (2x top_k to have headroom)
        3. SQL spreading activation from seeds + context_ids
        4. Combine: 35% vector + 30% activation + 20% retrievability + 15% salience
        5. Hebbian strengthening of recalled memories

        Returns:
            List of RecallResult sorted by final_score descending.
        """
        store = self._store(db)

        # Step 1: Generate query embedding
        query_embedding = await self._get_embedding(query[:8000])
        if not query_embedding:
            # Fallback: return recent memories
            nodes = await store.get_memories(user_id, limit=top_k, visibility=visibility, agent_id=agent_id)
            return [
                RecallResult(
                    memory_id=n.id,
                    content=n.content,
                    memory_type=n.metadata.memory_type.value,
                    layer=n.metadata.layer.value,
                    salience=n.metadata.salience,
                    final_score=n.metadata.salience,
                    tags=n.metadata.tags,
                    valence=n.metadata.valence.value if hasattr(n.metadata.valence, 'value') else n.metadata.valence,
                    agent_id=n.metadata.agent_id,
                    created_at=n.created_at.isoformat() if n.created_at else "",
                    access_count=n.strength.access_count,
                )
                for n in nodes
            ]

        # Step 2: pgvector search for seeds
        search_results = await store.vector_search(
            user_id,
            query_embedding,
            top_k=top_k * 2,
            memory_types=memory_types,
            min_salience=min_salience,
            visibility=visibility,
            agent_id=agent_id,
        )

        if not search_results:
            return []

        seed_ids = [node.id for node, _ in search_results]
        similarity_map = {node.id: sim for node, sim in search_results}
        node_map = {node.id: node for node, _ in search_results}

        # Step 3: Spreading activation
        all_seeds = list(seed_ids)
        if context_ids:
            all_seeds.extend(context_ids[:10])

        activation_map = await spreading_activation(db, user_id, all_seeds)

        # Step 4: Score all candidates
        now = time.time()
        scored_results: list[RecallResult] = []

        for node_id, node in node_map.items():
            vector_sim = similarity_map.get(node_id, 0.0)
            assoc_activation = activation_map.get(node_id, 0.0)

            base_level = compute_current_activation(node.strength, now)
            retrievability_score = compute_current_retrievability(node.strength, now)

            final = combined_recall_score(
                vector_similarity=vector_sim,
                base_level=base_level,
                associative=assoc_activation,
                fsrs_retrievability=retrievability_score,
                salience=node.metadata.salience,
            )

            scored_results.append(RecallResult(
                memory_id=node_id,
                content=node.content,
                memory_type=node.metadata.memory_type.value,
                layer=node.metadata.layer.value,
                vector_similarity=vector_sim,
                activation_score=assoc_activation,
                retrievability=retrievability_score,
                salience=node.metadata.salience,
                final_score=final,
                tags=node.metadata.tags,
                valence=node.metadata.valence.value if hasattr(node.metadata.valence, 'value') else node.metadata.valence,
                agent_id=node.metadata.agent_id,
                created_at=node.created_at.isoformat() if node.created_at else "",
                access_count=node.strength.access_count,
            ))

        # Sort by final score
        scored_results.sort(key=lambda r: r.final_score, reverse=True)
        top_results = scored_results[:top_k]

        # Step 5: Hebbian strengthening of recalled memories
        for result in top_results[:5]:  # Strengthen top 5
            try:
                node = node_map.get(result.memory_id)
                if node:
                    new_strength = record_access(node.strength, now)
                    await store.update_node_strength(user_id, result.memory_id, new_strength)
            except Exception as e:
                logger.debug(f"Hebbian update failed for {result.memory_id}: {e}")

        return top_results

    # =========================================================================
    # Associate
    # =========================================================================

    async def associate(
        self,
        db: AsyncSession,
        user_id: UUID,
        source_id: str,
        target_id: str,
        link_type: str,
        weight: float = 0.5,
        evidence: Optional[str] = None,
    ) -> dict:
        """Create an explicit association between two memories."""
        store = self._store(db)

        try:
            lt = LinkType(link_type)
        except ValueError:
            return {"error": f"Invalid link type: {link_type}"}

        link_id = await store.ensure_link(
            user_id,
            source_id=source_id,
            target_id=target_id,
            link_type=lt,
            weight=weight,
            source="user",
            evidence=evidence,
        )
        return {"link_id": link_id, "link_type": link_type, "weight": weight}

    # =========================================================================
    # Neighbors
    # =========================================================================

    async def get_neighbors(
        self,
        db: AsyncSession,
        user_id: UUID,
        memory_id: str,
        max_results: int = 10,
    ) -> list[dict]:
        """Get neighbors of a memory in the associative graph."""
        store = self._store(db)
        neighbors = await store.get_neighbors(user_id, memory_id)

        results = []
        for neighbor_id, weight, link_type in neighbors[:max_results]:
            node = await store.get_node(user_id, neighbor_id)
            results.append({
                "id": neighbor_id,
                "content": node.content[:200] if node else "",
                "memory_type": node.metadata.memory_type.value if node else "unknown",
                "link_type": link_type,
                "weight": weight,
            })
        return results

    # =========================================================================
    # Episodes
    # =========================================================================

    async def start_episode(
        self,
        db: AsyncSession,
        user_id: UUID,
        title: Optional[str] = None,
        agent_id: str = "AZOTH",
        tags: Optional[list[str]] = None,
        session_id: Optional[str] = None,
    ) -> dict:
        """Start recording an episode."""
        store = self._store(db)
        episode = Episode(
            title=title or "Untitled Episode",
            agent_id=agent_id,
            tags=tags or [],
            session_id=session_id,
            started_at=datetime.now(),
        )
        episode_id = await store.add_episode(user_id, episode)
        return {
            "id": episode_id,
            "title": episode.title,
            "agent_id": agent_id,
            "started_at": episode.started_at.isoformat(),
        }

    async def end_episode(
        self,
        db: AsyncSession,
        user_id: UUID,
        episode_id: str,
        summary: Optional[str] = None,
        valence: Optional[str] = None,
    ) -> dict:
        """End an episode with optional summary and valence."""
        store = self._store(db)
        kwargs: dict = {"ended_at": datetime.now()}
        if valence:
            try:
                kwargs["overall_valence"] = EmotionalValence(valence)
            except ValueError:
                pass
        ok = await store.update_episode(user_id, episode_id, **kwargs)
        if not ok:
            return {"error": f"Episode {episode_id} not found"}

        # If summary provided, store it as a reflection memory linked to the episode
        if summary:
            result = await self.remember(
                db, user_id, summary,
                memory_type="episodic",
                tags=["episode_summary"],
                agent_id="AZOTH",
                source="dream_engine",
            )
            if result and result.get("id"):
                await self.add_episode_step(
                    db, user_id, episode_id, result["id"], role="reflection",
                )

        return {"id": episode_id, "action": "ended", "valence": valence}

    async def add_episode_step(
        self,
        db: AsyncSession,
        user_id: UUID,
        episode_id: str,
        memory_id: str,
        role: str = "event",
    ) -> dict:
        """Add a memory as the next step in an episode."""
        store = self._store(db)
        # Get current step count for position
        existing = await store.get_episode_memory_ids(user_id, episode_id)
        step = EpisodeStep(
            memory_id=memory_id,
            position=len(existing),
            role=role,
        )
        await store.add_episode_step(user_id, episode_id, step)
        return {
            "episode_id": episode_id,
            "memory_id": memory_id,
            "position": step.position,
            "role": role,
        }

    async def list_episodes(
        self,
        db: AsyncSession,
        user_id: UUID,
        limit: int = 20,
    ) -> list[dict]:
        """List recent episodes."""
        store = self._store(db)
        episodes = await store.list_episodes(user_id, limit=limit)
        return [
            {
                "id": ep.id,
                "title": ep.title,
                "agent_id": ep.agent_id,
                "started_at": ep.started_at.isoformat() if ep.started_at else None,
                "ended_at": ep.ended_at.isoformat() if ep.ended_at else None,
                "overall_valence": ep.overall_valence.value if isinstance(ep.overall_valence, EmotionalValence) else ep.overall_valence,
                "consolidated": ep.consolidated,
                "tags": ep.tags,
            }
            for ep in episodes
        ]

    async def get_episode_memories(
        self,
        db: AsyncSession,
        user_id: UUID,
        episode_id: str,
    ) -> list[dict]:
        """Get all memories in an episode, in order."""
        store = self._store(db)
        mem_ids = await store.get_episode_memory_ids(user_id, episode_id)
        results = []
        for mid in mem_ids:
            node = await store.get_node(user_id, mid)
            if node:
                results.append({
                    "id": mid,
                    "content": node.content[:500],
                    "memory_type": node.metadata.memory_type.value,
                    "salience": node.metadata.salience,
                    "valence": node.metadata.valence.value if hasattr(node.metadata.valence, "value") else node.metadata.valence,
                })
        return results

    # =========================================================================
    # Procedures + Schemas
    # =========================================================================

    async def store_procedure(
        self,
        db: AsyncSession,
        user_id: UUID,
        content: str,
        tags: Optional[list[str]] = None,
        derived_from: Optional[list[str]] = None,
        agent_id: str = "AZOTH",
    ) -> dict:
        """Store a reusable procedure/workflow as a procedural memory.

        Procedures are stored as regular memory nodes with memory_type=procedural
        and derived_from links to source memories.
        """
        result = await self.remember(
            db, user_id, content,
            memory_type="procedural",
            tags=tags or [],
            agent_id=agent_id,
            source="dream_engine",
        )
        if not result or result.get("action") != "stored":
            return result or {"error": "Failed to store procedure"}

        # Link to source memories
        store = self._store(db)
        if derived_from:
            for source_id in derived_from[:10]:
                try:
                    await store.ensure_link(
                        user_id,
                        source_id=source_id,
                        target_id=result["id"],
                        link_type=LinkType.DERIVED_FROM,
                        weight=0.7,
                        source="dream_engine",
                        evidence="Procedure extracted from source memory",
                    )
                except Exception as e:
                    logger.debug(f"Procedure link failed for {source_id}: {e}")

        return {**result, "type": "procedure"}

    async def create_schema(
        self,
        db: AsyncSession,
        user_id: UUID,
        content: str,
        source_ids: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        agent_id: str = "AZOTH",
    ) -> dict:
        """Create an abstract principle/schema derived from multiple memories.

        Schemas are stored as memory nodes with memory_type=schematic
        and derived_from links to all source memories.
        """
        result = await self.remember(
            db, user_id, content,
            memory_type="schematic",
            tags=tags or [],
            agent_id=agent_id,
            source="dream_engine",
        )
        if not result or result.get("action") != "stored":
            return result or {"error": "Failed to create schema"}

        # Link all source memories
        store = self._store(db)
        if source_ids:
            for source_id in source_ids[:20]:
                try:
                    await store.ensure_link(
                        user_id,
                        source_id=source_id,
                        target_id=result["id"],
                        link_type=LinkType.DERIVED_FROM,
                        weight=0.8,
                        source="dream_engine",
                        evidence="Schema abstracted from source memory",
                    )
                except Exception as e:
                    logger.debug(f"Schema link failed for {source_id}: {e}")

        return {**result, "type": "schema"}

    async def find_matching_schemas(
        self,
        db: AsyncSession,
        user_id: UUID,
        tags: Optional[list[str]] = None,
        concepts: Optional[list[str]] = None,
    ) -> list[dict]:
        """Find schemas matching given tags or concepts."""
        store = self._store(db)
        # Query schematic memories filtered by tags
        nodes = await store.get_memories(
            user_id, limit=20, memory_type="schematic",
        )
        results = []
        search_terms = set((tags or []) + (concepts or []))
        for node in nodes:
            if search_terms:
                node_terms = set(node.metadata.tags + node.metadata.concepts)
                if not node_terms.intersection(search_terms):
                    continue
            results.append({
                "id": node.id,
                "content": node.content[:300],
                "tags": node.metadata.tags,
                "salience": node.metadata.salience,
                "created_at": node.created_at.isoformat() if node.created_at else "",
            })
        return results

    async def list_procedures(
        self,
        db: AsyncSession,
        user_id: UUID,
        tags: Optional[list[str]] = None,
        min_salience: float = 0.0,
    ) -> list[dict]:
        """List stored procedures, optionally filtered by tags."""
        store = self._store(db)
        nodes = await store.get_memories(
            user_id, limit=50, memory_type="procedural",
        )
        results = []
        for node in nodes:
            if node.metadata.salience < min_salience:
                continue
            if tags:
                if not set(tags).intersection(set(node.metadata.tags)):
                    continue
            results.append({
                "id": node.id,
                "content": node.content[:300],
                "tags": node.metadata.tags,
                "salience": node.metadata.salience,
                "access_count": node.strength.access_count,
                "created_at": node.created_at.isoformat() if node.created_at else "",
            })
        return results

    # =========================================================================
    # Stats
    # =========================================================================

    async def stats(self, db: AsyncSession, user_id: UUID) -> dict:
        """Get comprehensive CerebroCortex stats for a user."""
        store = self._store(db)
        return await store.stats(user_id)
