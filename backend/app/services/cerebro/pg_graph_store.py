"""PostgreSQL graph store adapter for CerebroCortex.

Replaces the SQLite/ChromaDB/igraph triple backend with a single
async PostgreSQL backend using pgvector for embeddings.
"""

import hashlib
import json
import logging
import time
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.cerebro.models.memory import MemoryMetadata, MemoryNode, StrengthState
from app.cerebro.models.link import AssociativeLink
from app.cerebro.models.episode import Episode, EpisodeStep
from app.cerebro.models.agent import AgentProfile
from app.cerebro.types import LinkType, MemoryLayer, MemoryType, EmotionalValence

logger = logging.getLogger(__name__)


class PgGraphStore:
    """Async PostgreSQL adapter implementing CerebroCortex storage.

    Every method takes user_id as first param for multi-tenant isolation.
    Uses existing EmbeddingService for vector generation.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _content_hash(content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    # =========================================================================
    # Memory node CRUD
    # =========================================================================

    async def add_node(
        self,
        user_id: UUID,
        node: MemoryNode,
        embedding: Optional[list[float]] = None,
    ) -> str:
        """Add a memory node to PostgreSQL with optional embedding."""
        content_hash = self._content_hash(node.content)
        meta = node.metadata
        strength = node.strength

        embedding_clause = ""
        embedding_val = None
        if embedding:
            embedding_clause = ", embedding"
            embedding_val = f"[{','.join(str(x) for x in embedding)}]"

        params = {
            "id": node.id,
            "user_id": str(user_id),
            "content": node.content,
            "content_hash": content_hash,
            "memory_type": meta.memory_type.value,
            "layer": meta.layer.value,
            "agent_id": meta.agent_id,
            "visibility": meta.visibility.value,
            "stability": strength.stability,
            "difficulty": strength.difficulty,
            "access_count": strength.access_count,
            "access_timestamps_json": json.dumps(strength.access_timestamps),
            "compressed_count": strength.compressed_count,
            "compressed_avg_interval": strength.compressed_avg_interval,
            "last_retrievability": strength.last_retrievability,
            "last_activation": strength.last_activation,
            "last_computed_at": strength.last_computed_at,
            "valence": meta.valence.value if isinstance(meta.valence, EmotionalValence) else meta.valence,
            "arousal": meta.arousal,
            "salience": meta.salience,
            "episode_id": meta.episode_id,
            "session_id": meta.session_id,
            "conversation_thread": meta.conversation_thread,
            "tags": json.dumps(meta.tags),
            "concepts": json.dumps(meta.concepts),
            "responding_to": json.dumps(meta.responding_to),
            "related_agents": json.dumps(meta.related_agents),
            "source": meta.source,
            "derived_from": json.dumps(meta.derived_from),
            "created_at": node.created_at,
            "last_accessed_at": node.last_accessed_at,
            "promoted_at": node.promoted_at,
        }

        if embedding_val:
            params["embedding"] = embedding_val
            sql = text("""
                INSERT INTO cerebro_memory_nodes (
                    id, user_id, content, content_hash, memory_type, layer, agent_id, visibility,
                    stability, difficulty, access_count, access_timestamps_json,
                    compressed_count, compressed_avg_interval,
                    last_retrievability, last_activation, last_computed_at,
                    valence, arousal, salience,
                    episode_id, session_id, conversation_thread,
                    tags, concepts, responding_to, related_agents,
                    source, derived_from,
                    created_at, last_accessed_at, promoted_at, embedding
                ) VALUES (
                    :id, :user_id, :content, :content_hash, :memory_type, :layer, :agent_id, :visibility,
                    :stability, :difficulty, :access_count, CAST(:access_timestamps_json AS jsonb),
                    :compressed_count, :compressed_avg_interval,
                    :last_retrievability, :last_activation, :last_computed_at,
                    :valence, :arousal, :salience,
                    :episode_id, :session_id, :conversation_thread,
                    CAST(:tags AS jsonb), CAST(:concepts AS jsonb), CAST(:responding_to AS jsonb), CAST(:related_agents AS jsonb),
                    :source, CAST(:derived_from AS jsonb),
                    :created_at, :last_accessed_at, :promoted_at, CAST(:embedding AS vector)
                )
            """)
        else:
            sql = text("""
                INSERT INTO cerebro_memory_nodes (
                    id, user_id, content, content_hash, memory_type, layer, agent_id, visibility,
                    stability, difficulty, access_count, access_timestamps_json,
                    compressed_count, compressed_avg_interval,
                    last_retrievability, last_activation, last_computed_at,
                    valence, arousal, salience,
                    episode_id, session_id, conversation_thread,
                    tags, concepts, responding_to, related_agents,
                    source, derived_from,
                    created_at, last_accessed_at, promoted_at
                ) VALUES (
                    :id, :user_id, :content, :content_hash, :memory_type, :layer, :agent_id, :visibility,
                    :stability, :difficulty, :access_count, CAST(:access_timestamps_json AS jsonb),
                    :compressed_count, :compressed_avg_interval,
                    :last_retrievability, :last_activation, :last_computed_at,
                    :valence, :arousal, :salience,
                    :episode_id, :session_id, :conversation_thread,
                    CAST(:tags AS jsonb), CAST(:concepts AS jsonb), CAST(:responding_to AS jsonb), CAST(:related_agents AS jsonb),
                    :source, CAST(:derived_from AS jsonb),
                    :created_at, :last_accessed_at, :promoted_at
                )
            """)

        await self.db.execute(sql, params)
        await self.db.commit()
        return node.id

    async def get_node(self, user_id: UUID, node_id: str) -> Optional[MemoryNode]:
        """Get a memory node by ID."""
        result = await self.db.execute(
            text("SELECT * FROM cerebro_memory_nodes WHERE id = :id AND user_id = :user_id"),
            {"id": node_id, "user_id": str(user_id)},
        )
        row = result.mappings().first()
        if not row:
            return None
        return self._row_to_memory_node(row)

    async def find_duplicate_content(self, user_id: UUID, content: str) -> Optional[str]:
        """Check if content already exists (by hash). Returns existing ID or None."""
        h = self._content_hash(content)
        result = await self.db.execute(
            text("SELECT id FROM cerebro_memory_nodes WHERE user_id = :user_id AND content_hash = :hash LIMIT 1"),
            {"user_id": str(user_id), "hash": h},
        )
        row = result.mappings().first()
        return row["id"] if row else None

    async def update_node_strength(self, user_id: UUID, node_id: str, strength: StrengthState) -> bool:
        """Update only the strength parameters for a node."""
        result = await self.db.execute(
            text("""
                UPDATE cerebro_memory_nodes SET
                    stability = :stability, difficulty = :difficulty,
                    access_count = :access_count,
                    access_timestamps_json = CAST(:timestamps AS jsonb),
                    compressed_count = :compressed_count,
                    compressed_avg_interval = :compressed_avg_interval,
                    last_retrievability = :last_retrievability,
                    last_activation = :last_activation,
                    last_computed_at = :last_computed_at,
                    last_accessed_at = NOW()
                WHERE id = :id AND user_id = :user_id
            """),
            {
                "stability": strength.stability,
                "difficulty": strength.difficulty,
                "access_count": strength.access_count,
                "timestamps": json.dumps(strength.access_timestamps),
                "compressed_count": strength.compressed_count,
                "compressed_avg_interval": strength.compressed_avg_interval,
                "last_retrievability": strength.last_retrievability,
                "last_activation": strength.last_activation,
                "last_computed_at": strength.last_computed_at,
                "id": node_id,
                "user_id": str(user_id),
            },
        )
        await self.db.commit()
        return result.rowcount > 0

    async def update_node_metadata(self, user_id: UUID, node_id: str, **kwargs) -> bool:
        """Update specific metadata fields for a node."""
        allowed = {
            "layer", "valence", "arousal", "salience", "episode_id",
            "session_id", "promoted_at", "concepts", "tags",
        }
        updates = []
        params = {"id": node_id, "user_id": str(user_id)}
        for key, val in kwargs.items():
            if key in allowed:
                if key in ("concepts", "tags"):
                    updates.append(f"{key} = CAST(:{key} AS jsonb)")
                    params[key] = json.dumps(val) if isinstance(val, list) else val
                else:
                    updates.append(f"{key} = :{key}")
                    params[key] = val
        if not updates:
            return False
        sql = text(f"UPDATE cerebro_memory_nodes SET {', '.join(updates)} WHERE id = :id AND user_id = :user_id")
        result = await self.db.execute(sql, params)
        await self.db.commit()
        return result.rowcount > 0

    # =========================================================================
    # Vector search
    # =========================================================================

    async def vector_search(
        self,
        user_id: UUID,
        query_embedding: list[float],
        top_k: int = 20,
        memory_types: Optional[list[str]] = None,
        min_salience: float = 0.0,
        visibility: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> list[tuple[MemoryNode, float]]:
        """Search memories by vector similarity using pgvector.

        Returns list of (MemoryNode, similarity_score) tuples.
        """
        embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

        where_clauses = ["user_id = :user_id", "embedding IS NOT NULL"]
        params: dict = {"user_id": str(user_id), "embedding": embedding_str, "top_k": top_k}

        if memory_types:
            where_clauses.append("memory_type = ANY(:memory_types)")
            params["memory_types"] = memory_types

        if min_salience > 0:
            where_clauses.append("salience >= :min_salience")
            params["min_salience"] = min_salience

        if visibility:
            where_clauses.append("visibility = :visibility")
            params["visibility"] = visibility

        if agent_id:
            where_clauses.append("agent_id = :agent_id")
            params["agent_id"] = agent_id

        where = " AND ".join(where_clauses)

        result = await self.db.execute(
            text(f"""
                SELECT *, 1 - (embedding <=> CAST(:embedding AS vector)) as similarity
                FROM cerebro_memory_nodes
                WHERE {where}
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :top_k
            """),
            params,
        )
        rows = result.mappings().all()

        results = []
        for row in rows:
            node = self._row_to_memory_node(row)
            similarity = float(row.get("similarity", 0))
            results.append((node, similarity))
        return results

    # =========================================================================
    # Associative link CRUD
    # =========================================================================

    async def add_link(self, user_id: UUID, link: AssociativeLink) -> str:
        """Add an associative link. On conflict, strengthen existing."""
        try:
            await self.db.execute(
                text("""
                    INSERT INTO cerebro_associative_links (
                        id, user_id, source_id, target_id, link_type, weight,
                        activation_count, created_at, last_activated,
                        source_reason, evidence
                    ) VALUES (
                        :id, :user_id, :source_id, :target_id, :link_type, :weight,
                        :activation_count, :created_at, :last_activated,
                        :source_reason, :evidence
                    )
                    ON CONFLICT ON CONSTRAINT uq_cerebro_link DO UPDATE SET
                        weight = GREATEST(cerebro_associative_links.weight, EXCLUDED.weight),
                        last_activated = NOW(),
                        activation_count = cerebro_associative_links.activation_count + 1
                """),
                {
                    "id": link.id,
                    "user_id": str(user_id),
                    "source_id": link.source_id,
                    "target_id": link.target_id,
                    "link_type": link.link_type.value,
                    "weight": link.weight,
                    "activation_count": link.activation_count,
                    "created_at": link.created_at,
                    "last_activated": link.last_activated,
                    "source_reason": link.source,
                    "evidence": link.evidence,
                },
            )
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.warning(f"Failed to add link: {e}")
            raise
        return link.id

    async def ensure_link(
        self,
        user_id: UUID,
        source_id: str,
        target_id: str,
        link_type: LinkType,
        weight: float = 0.5,
        source: str = "system",
        evidence: Optional[str] = None,
    ) -> str:
        """Create a link if it doesn't exist, or strengthen if it does."""
        link = AssociativeLink(
            source_id=source_id,
            target_id=target_id,
            link_type=link_type,
            weight=weight,
            source=source,
            evidence=evidence,
        )
        return await self.add_link(user_id, link)

    async def strengthen_link(self, user_id: UUID, source_id: str, target_id: str, boost: float = 0.1) -> None:
        """Hebbian learning: strengthen a link that was traversed."""
        await self.db.execute(
            text("""
                UPDATE cerebro_associative_links
                SET weight = LEAST(weight + :boost, 1.0),
                    last_activated = NOW(),
                    activation_count = activation_count + 1
                WHERE user_id = :user_id AND source_id = :source_id AND target_id = :target_id
            """),
            {"boost": boost, "user_id": str(user_id), "source_id": source_id, "target_id": target_id},
        )
        await self.db.commit()

    async def get_neighbors(
        self,
        user_id: UUID,
        node_id: str,
        link_types: Optional[list[str]] = None,
        min_weight: float = 0.0,
    ) -> list[tuple[str, float, str]]:
        """Get neighbors of a node via SQL.

        Returns: [(neighbor_id, weight, link_type), ...]
        """
        where_clauses = [
            "user_id = :user_id",
            "(source_id = :node_id OR target_id = :node_id)",
        ]
        params: dict = {"user_id": str(user_id), "node_id": node_id}

        if link_types:
            where_clauses.append("link_type = ANY(:link_types)")
            params["link_types"] = link_types

        if min_weight > 0:
            where_clauses.append("weight >= :min_weight")
            params["min_weight"] = min_weight

        where = " AND ".join(where_clauses)

        result = await self.db.execute(
            text(f"""
                SELECT source_id, target_id, weight, link_type
                FROM cerebro_associative_links
                WHERE {where}
                ORDER BY weight DESC
                LIMIT 50
            """),
            params,
        )
        rows = result.mappings().all()

        neighbors = []
        for row in rows:
            neighbor_id = row["target_id"] if row["source_id"] == node_id else row["source_id"]
            neighbors.append((neighbor_id, float(row["weight"]), row["link_type"]))
        return neighbors

    async def get_degree(self, user_id: UUID, node_id: str) -> int:
        """Get the number of links for a node."""
        result = await self.db.execute(
            text("""
                SELECT COUNT(*) as c FROM cerebro_associative_links
                WHERE user_id = :user_id AND (source_id = :node_id OR target_id = :node_id)
            """),
            {"user_id": str(user_id), "node_id": node_id},
        )
        row = result.mappings().first()
        return row["c"] if row else 0

    # =========================================================================
    # Episode CRUD
    # =========================================================================

    async def add_episode(self, user_id: UUID, episode: Episode) -> str:
        """Add an episode."""
        await self.db.execute(
            text("""
                INSERT INTO cerebro_episodes (
                    id, user_id, title, agent_id, session_id,
                    started_at, ended_at,
                    overall_valence, peak_arousal, tags,
                    consolidated, schema_extracted, created_at
                ) VALUES (
                    :id, :user_id, :title, :agent_id, :session_id,
                    :started_at, :ended_at,
                    :overall_valence, :peak_arousal, CAST(:tags AS jsonb),
                    :consolidated, :schema_extracted, :created_at
                )
            """),
            {
                "id": episode.id,
                "user_id": str(user_id),
                "title": episode.title,
                "agent_id": episode.agent_id,
                "session_id": episode.session_id,
                "started_at": episode.started_at,
                "ended_at": episode.ended_at,
                "overall_valence": episode.overall_valence.value if isinstance(episode.overall_valence, EmotionalValence) else episode.overall_valence,
                "peak_arousal": episode.peak_arousal,
                "tags": json.dumps(episode.tags),
                "consolidated": episode.consolidated,
                "schema_extracted": episode.schema_extracted,
                "created_at": episode.created_at,
            },
        )
        await self.db.commit()
        return episode.id

    async def add_episode_step(self, user_id: UUID, episode_id: str, step: EpisodeStep) -> None:
        """Add a step to an episode."""
        await self.db.execute(
            text("""
                INSERT INTO cerebro_episode_steps (episode_id, user_id, memory_id, position, role, timestamp)
                VALUES (:episode_id, :user_id, :memory_id, :position, :role, :timestamp)
            """),
            {
                "episode_id": episode_id,
                "user_id": str(user_id),
                "memory_id": step.memory_id,
                "position": step.position,
                "role": step.role,
                "timestamp": step.timestamp,
            },
        )
        await self.db.commit()

    # =========================================================================
    # Agent CRUD
    # =========================================================================

    async def register_agent(self, user_id: UUID, profile: AgentProfile) -> str:
        """Register or update an agent profile."""
        await self.db.execute(
            text("""
                INSERT INTO cerebro_agents (
                    id, user_id, display_name, generation, lineage, specialization,
                    origin_story, color, symbol, registered_at
                ) VALUES (
                    :id, :user_id, :display_name, :generation, :lineage, :specialization,
                    :origin_story, :color, :symbol, :registered_at
                )
                ON CONFLICT (id, user_id) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    specialization = EXCLUDED.specialization,
                    color = EXCLUDED.color,
                    symbol = EXCLUDED.symbol
            """),
            {
                "id": profile.id,
                "user_id": str(user_id),
                "display_name": profile.display_name,
                "generation": profile.generation,
                "lineage": profile.lineage,
                "specialization": profile.specialization,
                "origin_story": profile.origin_story,
                "color": profile.color,
                "symbol": profile.symbol,
                "registered_at": profile.registered_at,
            },
        )
        await self.db.commit()
        return profile.id

    async def list_agents(self, user_id: UUID) -> list[AgentProfile]:
        """List all registered agents for a user."""
        result = await self.db.execute(
            text("SELECT * FROM cerebro_agents WHERE user_id = :user_id ORDER BY registered_at"),
            {"user_id": str(user_id)},
        )
        rows = result.mappings().all()
        return [
            AgentProfile(
                id=r["id"],
                display_name=r["display_name"],
                generation=r["generation"],
                lineage=r.get("lineage") or "Unknown",
                specialization=r.get("specialization") or "General",
                origin_story=r.get("origin_story"),
                color=r.get("color") or "#888888",
                symbol=r.get("symbol") or "A",
                registered_at=r["registered_at"],
            )
            for r in rows
        ]

    # =========================================================================
    # Stats
    # =========================================================================

    async def stats(self, user_id: UUID) -> dict:
        """Get comprehensive stats for a user's memory graph."""
        r = await self.db.execute(
            text("SELECT COUNT(*) as c FROM cerebro_memory_nodes WHERE user_id = :uid"),
            {"uid": str(user_id)},
        )
        node_count = r.scalar() or 0

        r = await self.db.execute(
            text("SELECT COUNT(*) as c FROM cerebro_associative_links WHERE user_id = :uid"),
            {"uid": str(user_id)},
        )
        link_count = r.scalar() or 0

        r = await self.db.execute(
            text("SELECT memory_type, COUNT(*) as c FROM cerebro_memory_nodes WHERE user_id = :uid GROUP BY memory_type"),
            {"uid": str(user_id)},
        )
        type_counts = {row.memory_type: row.c for row in r}

        r = await self.db.execute(
            text("SELECT layer, COUNT(*) as c FROM cerebro_memory_nodes WHERE user_id = :uid GROUP BY layer"),
            {"uid": str(user_id)},
        )
        layer_counts = {row.layer: row.c for row in r}

        r = await self.db.execute(
            text("SELECT visibility, COUNT(*) as c FROM cerebro_memory_nodes WHERE user_id = :uid GROUP BY visibility"),
            {"uid": str(user_id)},
        )
        visibility_counts = {row.visibility: row.c for row in r}

        r = await self.db.execute(
            text("SELECT link_type, COUNT(*) as c FROM cerebro_associative_links WHERE user_id = :uid GROUP BY link_type"),
            {"uid": str(user_id)},
        )
        link_type_counts = {row.link_type: row.c for row in r}

        r = await self.db.execute(
            text("SELECT COUNT(*) as c FROM cerebro_episodes WHERE user_id = :uid"),
            {"uid": str(user_id)},
        )
        episode_count = r.scalar() or 0

        r = await self.db.execute(
            text("SELECT agent_id, COUNT(*) as c FROM cerebro_memory_nodes WHERE user_id = :uid GROUP BY agent_id"),
            {"uid": str(user_id)},
        )
        agent_counts = {row.agent_id: row.c for row in r}

        return {
            "nodes": node_count,
            "links": link_count,
            "episodes": episode_count,
            "memory_types": type_counts,
            "layers": layer_counts,
            "visibility": visibility_counts,
            "link_types": link_type_counts,
            "agents": agent_counts,
        }

    # =========================================================================
    # Query helpers
    # =========================================================================

    async def get_memories(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
        layer: Optional[str] = None,
        visibility: Optional[str] = None,
        agent_id: Optional[str] = None,
        memory_type: Optional[str] = None,
    ) -> list[MemoryNode]:
        """Get memories with filters."""
        where_clauses = ["user_id = :user_id"]
        params: dict = {"user_id": str(user_id), "limit": limit, "offset": offset}

        if layer:
            where_clauses.append("layer = :layer")
            params["layer"] = layer
        if visibility:
            where_clauses.append("visibility = :visibility")
            params["visibility"] = visibility
        if agent_id:
            where_clauses.append("agent_id = :agent_id")
            params["agent_id"] = agent_id
        if memory_type:
            where_clauses.append("memory_type = :memory_type")
            params["memory_type"] = memory_type

        where = " AND ".join(where_clauses)
        result = await self.db.execute(
            text(f"""
                SELECT * FROM cerebro_memory_nodes
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        )
        rows = result.mappings().all()
        return [self._row_to_memory_node(row) for row in rows]

    async def get_links_for_graph(
        self,
        user_id: UUID,
        node_ids: list[str],
    ) -> list[dict]:
        """Get all links between a set of nodes."""
        if not node_ids:
            return []
        result = await self.db.execute(
            text("""
                SELECT id, source_id, target_id, link_type, weight, activation_count
                FROM cerebro_associative_links
                WHERE user_id = :user_id
                  AND source_id = ANY(:node_ids)
                  AND target_id = ANY(:node_ids)
            """),
            {"user_id": str(user_id), "node_ids": node_ids},
        )
        rows = result.mappings().all()
        return [dict(row) for row in rows]

    # =========================================================================
    # Episode queries (dream engine)
    # =========================================================================

    async def get_unconsolidated_episodes(self, user_id: UUID) -> list[Episode]:
        """Get episodes that haven't been consolidated by the dream engine."""
        result = await self.db.execute(
            text("""
                SELECT * FROM cerebro_episodes
                WHERE user_id = :user_id AND consolidated = FALSE
                ORDER BY created_at ASC
            """),
            {"user_id": str(user_id)},
        )
        rows = result.mappings().all()
        return [self._row_to_episode(row) for row in rows]

    async def mark_episode_consolidated(self, user_id: UUID, episode_id: str) -> bool:
        """Mark an episode as consolidated by the dream engine."""
        result = await self.db.execute(
            text("""
                UPDATE cerebro_episodes
                SET consolidated = TRUE
                WHERE id = :id AND user_id = :user_id
            """),
            {"id": episode_id, "user_id": str(user_id)},
        )
        await self.db.commit()
        return result.rowcount > 0

    async def get_episode_memory_ids(self, user_id: UUID, episode_id: str) -> list[str]:
        """Get ordered memory IDs for an episode."""
        result = await self.db.execute(
            text("""
                SELECT memory_id FROM cerebro_episode_steps
                WHERE episode_id = :episode_id AND user_id = :user_id
                ORDER BY position ASC
            """),
            {"episode_id": episode_id, "user_id": str(user_id)},
        )
        return [row.memory_id for row in result]

    async def get_episode(self, user_id: UUID, episode_id: str) -> Optional[Episode]:
        """Get a single episode by ID."""
        result = await self.db.execute(
            text("SELECT * FROM cerebro_episodes WHERE id = :id AND user_id = :user_id"),
            {"id": episode_id, "user_id": str(user_id)},
        )
        row = result.mappings().first()
        if not row:
            return None
        return self._row_to_episode(row)

    async def update_episode(self, user_id: UUID, episode_id: str, **kwargs) -> bool:
        """Update episode fields."""
        allowed = {
            "title", "ended_at", "overall_valence", "peak_arousal",
            "tags", "consolidated", "schema_extracted",
        }
        updates = []
        params = {"id": episode_id, "user_id": str(user_id)}
        for key, val in kwargs.items():
            if key in allowed:
                if key == "tags":
                    updates.append(f"{key} = CAST(:{key} AS jsonb)")
                    params[key] = json.dumps(val) if isinstance(val, list) else val
                elif key == "overall_valence" and isinstance(val, EmotionalValence):
                    updates.append(f"{key} = :{key}")
                    params[key] = val.value
                else:
                    updates.append(f"{key} = :{key}")
                    params[key] = val
        if not updates:
            return False
        sql = text(f"UPDATE cerebro_episodes SET {', '.join(updates)} WHERE id = :id AND user_id = :user_id")
        result = await self.db.execute(sql, params)
        await self.db.commit()
        return result.rowcount > 0

    async def list_episodes(self, user_id: UUID, limit: int = 20) -> list[Episode]:
        """List recent episodes for a user."""
        result = await self.db.execute(
            text("""
                SELECT * FROM cerebro_episodes
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"user_id": str(user_id), "limit": limit},
        )
        rows = result.mappings().all()
        return [self._row_to_episode(row) for row in rows]

    # =========================================================================
    # Batch graph operations (dream engine)
    # =========================================================================

    async def get_all_node_ids(self, user_id: UUID, layer: Optional[str] = None) -> list[str]:
        """Get all memory node IDs for a user, optionally filtered by layer."""
        params: dict = {"user_id": str(user_id)}
        where = "user_id = :user_id"
        if layer:
            where += " AND layer = :layer"
            params["layer"] = layer
        result = await self.db.execute(
            text(f"SELECT id FROM cerebro_memory_nodes WHERE {where}"),
            params,
        )
        return [row.id for row in result]

    async def delete_node(self, user_id: UUID, node_id: str) -> bool:
        """Delete a memory node and its links."""
        await self.db.execute(
            text("""
                DELETE FROM cerebro_associative_links
                WHERE user_id = :user_id AND (source_id = :id OR target_id = :id)
            """),
            {"user_id": str(user_id), "id": node_id},
        )
        result = await self.db.execute(
            text("DELETE FROM cerebro_memory_nodes WHERE id = :id AND user_id = :user_id"),
            {"id": node_id, "user_id": str(user_id)},
        )
        await self.db.commit()
        return result.rowcount > 0

    async def has_link(self, user_id: UUID, source_id: str, target_id: str) -> bool:
        """Check if a link exists between two nodes (either direction)."""
        result = await self.db.execute(
            text("""
                SELECT 1 FROM cerebro_associative_links
                WHERE user_id = :user_id
                  AND ((source_id = :a AND target_id = :b) OR (source_id = :b AND target_id = :a))
                LIMIT 1
            """),
            {"user_id": str(user_id), "a": source_id, "b": target_id},
        )
        return result.first() is not None

    async def batch_strengthen_co_activated(
        self, user_id: UUID, node_ids: list[str], boost: float = 0.08,
    ) -> int:
        """Hebbian learning: strengthen all links between a set of co-activated nodes."""
        if len(node_ids) < 2:
            return 0
        result = await self.db.execute(
            text("""
                UPDATE cerebro_associative_links
                SET weight = LEAST(weight + :boost, 1.0),
                    last_activated = NOW(),
                    activation_count = activation_count + 1
                WHERE user_id = :user_id
                  AND source_id = ANY(:ids) AND target_id = ANY(:ids)
            """),
            {"user_id": str(user_id), "ids": node_ids, "boost": boost},
        )
        await self.db.commit()
        return result.rowcount

    async def prune_isolated_sensory(
        self, user_id: UUID, max_salience: float, cutoff: datetime,
    ) -> int:
        """Delete isolated, low-salience sensory memories older than cutoff.

        Single efficient SQL instead of N+1 loop.
        """
        result = await self.db.execute(
            text("""
                DELETE FROM cerebro_memory_nodes n
                WHERE n.user_id = :user_id
                  AND n.layer = 'sensory'
                  AND n.salience < :max_sal
                  AND n.created_at < :cutoff
                  AND NOT EXISTS (
                      SELECT 1 FROM cerebro_associative_links l
                      WHERE l.user_id = :user_id
                        AND (l.source_id = n.id OR l.target_id = n.id)
                  )
            """),
            {"user_id": str(user_id), "max_sal": max_salience, "cutoff": cutoff},
        )
        await self.db.commit()
        return result.rowcount

    # =========================================================================
    # Dream log
    # =========================================================================

    async def log_dream_phase(
        self,
        user_id: UUID,
        cycle_id: str,
        phase: str,
        memories_processed: int = 0,
        links_created: int = 0,
        links_strengthened: int = 0,
        memories_pruned: int = 0,
        schemas_extracted: int = 0,
        procedures_extracted: int = 0,
        total_llm_calls: int = 0,
        total_input_tokens: int = 0,
        total_output_tokens: int = 0,
        duration_seconds: float = 0,
        notes: str = "",
        success: bool = True,
        provider: str = "anthropic",
        model_used: str = "",
    ) -> None:
        """Log a dream phase to the dream log."""
        await self.db.execute(
            text("""
                INSERT INTO cerebro_dream_log (
                    user_id, cycle_id, phase, started_at, completed_at,
                    memories_processed, links_created, links_strengthened,
                    memories_pruned, schemas_extracted, procedures_extracted,
                    total_llm_calls, total_input_tokens, total_output_tokens,
                    duration_seconds, notes, success,
                    provider, model_used
                ) VALUES (
                    :user_id, :cycle_id, :phase, NOW() - INTERVAL '1 second' * :duration, NOW(),
                    :mem_proc, :links_c, :links_s,
                    :mem_pruned, :schemas, :procedures,
                    :llm_calls, :in_tokens, :out_tokens,
                    :duration, :notes, :success,
                    :provider, :model_used
                )
            """),
            {
                "user_id": str(user_id),
                "cycle_id": cycle_id,
                "phase": phase,
                "duration": duration_seconds,
                "mem_proc": memories_processed,
                "links_c": links_created,
                "links_s": links_strengthened,
                "mem_pruned": memories_pruned,
                "schemas": schemas_extracted,
                "procedures": procedures_extracted,
                "llm_calls": total_llm_calls,
                "in_tokens": total_input_tokens,
                "out_tokens": total_output_tokens,
                "notes": notes,
                "success": success,
                "provider": provider,
                "model_used": model_used,
            },
        )
        await self.db.commit()

    async def get_dream_log(self, user_id: UUID, limit: int = 10) -> list[dict]:
        """Get recent dream log entries."""
        result = await self.db.execute(
            text("""
                SELECT * FROM cerebro_dream_log
                WHERE user_id = :user_id
                ORDER BY completed_at DESC NULLS LAST
                LIMIT :limit
            """),
            {"user_id": str(user_id), "limit": limit},
        )
        return [dict(row) for row in result.mappings().all()]

    async def count_dream_cycles_since(self, user_id: UUID, since: datetime) -> int:
        """Count distinct dream cycles since a given date (for tier gating)."""
        result = await self.db.execute(
            text("""
                SELECT COUNT(DISTINCT cycle_id) as c
                FROM cerebro_dream_log
                WHERE user_id = :user_id AND completed_at >= :since
            """),
            {"user_id": str(user_id), "since": since},
        )
        row = result.mappings().first()
        return row["c"] if row else 0

    # =========================================================================
    # Row mapping
    # =========================================================================

    @staticmethod
    def _row_to_episode(row) -> Episode:
        """Convert a DB row to an Episode."""
        tags = row.get("tags", [])
        if isinstance(tags, str):
            tags = json.loads(tags)
        return Episode(
            id=row["id"],
            title=row.get("title", ""),
            agent_id=row.get("agent_id"),
            session_id=row.get("session_id"),
            started_at=row.get("started_at") or row.get("created_at"),
            ended_at=row.get("ended_at"),
            overall_valence=row.get("overall_valence", "neutral"),
            peak_arousal=float(row.get("peak_arousal", 0.5)) if row.get("peak_arousal") else 0.5,
            tags=tags,
            consolidated=bool(row.get("consolidated", False)),
            schema_extracted=bool(row.get("schema_extracted", False)),
        )

    @staticmethod
    def _row_to_memory_node(row) -> MemoryNode:
        """Convert a DB row to a MemoryNode."""
        tags = row.get("tags", [])
        if isinstance(tags, str):
            tags = json.loads(tags)
        concepts = row.get("concepts", [])
        if isinstance(concepts, str):
            concepts = json.loads(concepts)
        responding_to = row.get("responding_to", [])
        if isinstance(responding_to, str):
            responding_to = json.loads(responding_to)
        related_agents = row.get("related_agents", [])
        if isinstance(related_agents, str):
            related_agents = json.loads(related_agents)
        derived_from = row.get("derived_from", [])
        if isinstance(derived_from, str):
            derived_from = json.loads(derived_from)
        access_timestamps = row.get("access_timestamps_json", [])
        if isinstance(access_timestamps, str):
            access_timestamps = json.loads(access_timestamps)

        created_at = row.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        last_accessed = row.get("last_accessed_at")
        if isinstance(last_accessed, str):
            last_accessed = datetime.fromisoformat(last_accessed)

        promoted = row.get("promoted_at")
        if isinstance(promoted, str):
            promoted = datetime.fromisoformat(promoted)

        return MemoryNode(
            id=row["id"],
            content=row["content"],
            metadata=MemoryMetadata(
                agent_id=row.get("agent_id") or "AZOTH",
                visibility=row.get("visibility", "shared"),
                layer=MemoryLayer(row.get("layer", "working")),
                memory_type=MemoryType(row.get("memory_type", "semantic")),
                tags=tags,
                concepts=concepts,
                session_id=row.get("session_id"),
                conversation_thread=row.get("conversation_thread"),
                episode_id=row.get("episode_id"),
                responding_to=responding_to,
                related_agents=related_agents,
                valence=row.get("valence", "neutral"),
                arousal=float(row.get("arousal", 0.5)),
                salience=float(row.get("salience", 0.5)),
                source=row.get("source", "user_input"),
                derived_from=derived_from,
            ),
            strength=StrengthState(
                stability=float(row.get("stability", 1.0)),
                difficulty=float(row.get("difficulty", 5.0)),
                access_count=int(row.get("access_count", 0)),
                access_timestamps=access_timestamps,
                compressed_count=int(row.get("compressed_count", 0)),
                compressed_avg_interval=float(row.get("compressed_avg_interval", 0.0)),
                last_retrievability=float(row.get("last_retrievability", 1.0)),
                last_activation=float(row.get("last_activation", 0.0)),
                last_computed_at=row.get("last_computed_at"),
            ),
            created_at=created_at or datetime.now(),
            last_accessed_at=last_accessed,
            promoted_at=promoted,
        )

    # =========================================================================
    # Dream Queue (Targeted Dream Cycles)
    # =========================================================================

    async def add_to_dream_queue(
        self, user_id: UUID, memory_ids: list[str], source: str = "manual"
    ) -> int:
        """Add memory IDs to the dream queue. Returns count added."""
        if not memory_ids:
            return 0
        added = 0
        for mid in memory_ids:
            result = await self.db.execute(
                text("""
                    INSERT INTO cerebro_dream_queue (user_id, memory_id, source)
                    VALUES (:uid, :mid, :src)
                    ON CONFLICT (user_id, memory_id) DO NOTHING
                """),
                {"uid": str(user_id), "mid": mid, "src": source},
            )
            added += result.rowcount
        await self.db.commit()
        return added

    async def remove_from_dream_queue(
        self, user_id: UUID, memory_ids: list[str]
    ) -> int:
        """Remove memory IDs from the dream queue. Returns count removed."""
        if not memory_ids:
            return 0
        result = await self.db.execute(
            text("""
                DELETE FROM cerebro_dream_queue
                WHERE user_id = :uid AND memory_id = ANY(:mids)
            """),
            {"uid": str(user_id), "mids": memory_ids},
        )
        await self.db.commit()
        return result.rowcount

    async def get_dream_queue(self, user_id: UUID) -> list[dict]:
        """Get all queued memories with content preview."""
        result = await self.db.execute(
            text("""
                SELECT q.memory_id, q.queued_at, q.source,
                       LEFT(m.content, 100) as content_preview
                FROM cerebro_dream_queue q
                LEFT JOIN cerebro_memory_nodes m
                    ON m.id = q.memory_id AND m.user_id = q.user_id
                WHERE q.user_id = :uid
                ORDER BY q.queued_at DESC
            """),
            {"uid": str(user_id)},
        )
        return [
            {
                "memory_id": row[0],
                "queued_at": row[1].isoformat() if row[1] else None,
                "source": row[2],
                "content_preview": row[3] or "(deleted)",
            }
            for row in result.fetchall()
        ]

    async def clear_dream_queue(self, user_id: UUID) -> int:
        """Clear the entire dream queue for a user."""
        result = await self.db.execute(
            text("DELETE FROM cerebro_dream_queue WHERE user_id = :uid"),
            {"uid": str(user_id)},
        )
        await self.db.commit()
        return result.rowcount

    async def get_dream_queue_ids(self, user_id: UUID) -> list[str]:
        """Get just the memory_ids from the queue."""
        result = await self.db.execute(
            text("SELECT memory_id FROM cerebro_dream_queue WHERE user_id = :uid"),
            {"uid": str(user_id)},
        )
        return [row[0] for row in result.fetchall()]

    async def get_neighbor_ids(
        self, user_id: UUID, node_ids: list[str], max_hops: int = 1
    ) -> list[str]:
        """Get unique neighbor IDs for a set of nodes (1-hop expansion)."""
        if not node_ids:
            return []
        result = await self.db.execute(
            text("""
                SELECT DISTINCT
                    CASE WHEN source_id = ANY(:nids) THEN target_id ELSE source_id END as neighbor
                FROM cerebro_associative_links
                WHERE user_id = :uid
                  AND (source_id = ANY(:nids) OR target_id = ANY(:nids))
            """),
            {"uid": str(user_id), "nids": node_ids},
        )
        # Return neighbors that aren't already in the input set
        input_set = set(node_ids)
        return [row[0] for row in result.fetchall() if row[0] not in input_set]
