"""Async Dream Engine - Default Mode Network for CerebroCortex (Cloud).

Ported from CerebroCore's cerebro_future branch. Runs as an ARQ background job
or on-demand via API. Consolidates memories through 6 biologically-inspired phases:

1. SWS Replay      - Replay episodes, strengthen temporal links (algorithmic)
2. Pattern Extract  - Cluster similar memories, extract procedures (LLM)
3. Schema Formation - Abstract episodes into principles (LLM)
4. Emotional Reproc - Adjust salience based on outcomes (algorithmic)
5. Pruning          - Decay, promote, prune isolated noise (algorithmic)
6. REM Recombine    - Sample diverse memories, find connections (LLM)

Cloud adaptations:
- All DB ops are async via PgGraphStore
- LLM calls via MultiProviderLLM.chat() (supports Anthropic, BYOK, Bridge)
- Multi-tenant: every query scoped by user_id
- Token tracking for billing
- Single SQL pruning instead of N+1 loop
"""

import json
import logging
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from app.cerebro.config import (
    DREAM_CLUSTER_MIN_SIZE,
    DREAM_LLM_BUDGET_PATTERN,
    DREAM_LLM_BUDGET_REM,
    DREAM_LLM_BUDGET_SCHEMA,
    DREAM_MAX_LLM_CALLS,
    DREAM_PRUNING_MAX_SALIENCE,
    DREAM_PRUNING_MIN_AGE_HOURS,
    DREAM_REM_MIN_CONNECTION_STRENGTH,
    DREAM_REM_PAIR_CHECKS,
    DREAM_REM_SAMPLE_SIZE,
)
from app.cerebro.types import DreamPhase, LinkType
from app.services.cerebro.dream_prompts import (
    PROMPT_EXTRACT_PATTERNS,
    PROMPT_FORM_SCHEMA,
    PROMPT_REM_CONNECT,
    SYSTEM_DREAM,
)

logger = logging.getLogger("cerebro-dream")


# =============================================================================
# Dream report data
# =============================================================================

@dataclass
class PhaseReport:
    """Report from a single dream phase."""
    phase: DreamPhase
    memories_processed: int = 0
    links_created: int = 0
    links_strengthened: int = 0
    memories_pruned: int = 0
    schemas_extracted: int = 0
    procedures_extracted: int = 0
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    duration_seconds: float = 0.0
    notes: str = ""
    success: bool = True


@dataclass
class DreamReport:
    """Report from a full dream cycle."""
    cycle_id: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    scope: str = "natural"       # "natural" or "targeted"
    target_count: int = 0        # Number of targeted memories (0 for natural)
    phases: list[PhaseReport] = field(default_factory=list)
    episodes_consolidated: int = 0
    total_llm_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_duration_seconds: float = 0.0
    success: bool = True
    provider: str = "anthropic"
    model_used: str = ""

    def to_dict(self) -> dict:
        return {
            "cycle_id": self.cycle_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "scope": self.scope,
            "target_count": self.target_count,
            "episodes_consolidated": self.episodes_consolidated,
            "total_llm_calls": self.total_llm_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_duration_seconds": round(self.total_duration_seconds, 2),
            "success": self.success,
            "provider": self.provider,
            "model_used": self.model_used,
            "phases": [
                {
                    "phase": p.phase.value,
                    "memories_processed": p.memories_processed,
                    "links_created": p.links_created,
                    "links_strengthened": p.links_strengthened,
                    "memories_pruned": p.memories_pruned,
                    "schemas_extracted": p.schemas_extracted,
                    "procedures_extracted": p.procedures_extracted,
                    "llm_calls": p.llm_calls,
                    "duration_seconds": round(p.duration_seconds, 2),
                    "notes": p.notes,
                    "success": p.success,
                }
                for p in self.phases
            ],
        }


# =============================================================================
# Async Dream Engine
# =============================================================================

class AsyncDreamEngine:
    """Async cloud dream engine. Consolidates memories through 6 phases.

    Uses get_db_context() for its own DB sessions and any object with an
    async chat() method for LLM calls (MultiProviderLLM, BridgeInferenceRelay,
    or BYOK provider).
    """

    def __init__(
        self,
        user_id,
        llm=None,
        model: str = "claude-haiku-4-5-20251001",
        max_llm_calls: int = DREAM_MAX_LLM_CALLS,
        provider: str = "anthropic",
    ):
        """Initialize async dream engine.

        Args:
            user_id: UUID of the user whose memories to consolidate.
            llm: Any object with async chat(messages, system, model, max_tokens).
                 If None, LLM phases are skipped (algorithmic only).
            model: Model ID for LLM calls.
            max_llm_calls: Total LLM call budget for this cycle.
            provider: LLM provider ID for tracking.
        """
        from uuid import UUID as UUIDType
        self._user_id = user_id if isinstance(user_id, UUIDType) else UUIDType(str(user_id))
        self._llm = llm
        self._model = model
        self._provider = provider
        self._max_llm_calls = max_llm_calls
        self._llm_calls_remaining = max_llm_calls
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._running = False
        self._last_report: Optional[DreamReport] = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_report(self) -> Optional[DreamReport]:
        return self._last_report

    def _store(self, db):
        """Create a PgGraphStore bound to a session."""
        from app.services.cerebro.pg_graph_store import PgGraphStore
        return PgGraphStore(db)

    # =========================================================================
    # Main cycle
    # =========================================================================

    async def run_cycle(self) -> DreamReport:
        """Run a full dream consolidation cycle (all 6 phases).

        Uses its own DB sessions via get_db_context().

        Returns:
            DreamReport with details of each phase.
        """
        if self._running:
            raise RuntimeError("Dream cycle already in progress")

        self._running = True
        self._llm_calls_remaining = self._max_llm_calls
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        cycle_id = f"dream_{uuid.uuid4().hex[:12]}"
        report = DreamReport(cycle_id=cycle_id, provider=self._provider, model_used=self._model)
        cycle_start = time.time()

        try:
            logger.info(f"Dream cycle {cycle_id} starting for user {self._user_id}...")

            # Run all 6 phases sequentially
            report.phases.append(await self._phase_sws_replay(cycle_id))
            report.phases.append(await self._phase_pattern_extraction(cycle_id))
            report.phases.append(await self._phase_schema_formation(cycle_id))
            report.phases.append(await self._phase_emotional_reprocessing(cycle_id))
            report.phases.append(await self._phase_pruning(cycle_id))
            report.phases.append(await self._phase_rem_recombination(cycle_id))

            # Mark episodes consolidated
            from app.database import get_db_context
            async with get_db_context() as db:
                store = self._store(db)
                episodes = await store.get_unconsolidated_episodes(self._user_id)
                for ep in episodes:
                    await store.mark_episode_consolidated(self._user_id, ep.id)
                report.episodes_consolidated = len(episodes)

            report.success = all(p.success for p in report.phases)
            logger.info(
                f"Dream cycle {cycle_id} complete: "
                f"{len(report.phases)} phases, "
                f"{report.episodes_consolidated} episodes consolidated, "
                f"{self._total_input_tokens + self._total_output_tokens} total tokens"
            )

        except Exception as e:
            logger.error(f"Dream cycle {cycle_id} failed: {e}", exc_info=True)
            report.success = False

        finally:
            self._running = False
            report.ended_at = datetime.now()
            report.total_duration_seconds = time.time() - cycle_start
            report.total_llm_calls = sum(p.llm_calls for p in report.phases)
            report.total_input_tokens = self._total_input_tokens
            report.total_output_tokens = self._total_output_tokens
            self._last_report = report

        return report

    # =========================================================================
    # Phase 1: SWS Replay (algorithmic)
    # =========================================================================

    async def _phase_sws_replay(self, cycle_id: str) -> PhaseReport:
        """Slow-Wave Sleep: replay episodes, Hebbian strengthen co-activated links."""
        report = PhaseReport(phase=DreamPhase.SWS_REPLAY)
        start = time.time()

        try:
            from app.database import get_db_context
            async with get_db_context() as db:
                store = self._store(db)
                episodes = await store.get_unconsolidated_episodes(self._user_id)
                if not episodes:
                    report.notes = "No unconsolidated episodes"
                    report.duration_seconds = time.time() - start
                    await self._log_phase(store, cycle_id, report)
                    return report

                total_strengthened = 0
                total_processed = 0

                for ep in episodes:
                    mem_ids = await store.get_episode_memory_ids(self._user_id, ep.id)
                    if len(mem_ids) < 2:
                        continue

                    total_processed += len(mem_ids)

                    # Hebbian: strengthen all existing links between episode memories
                    n = await store.batch_strengthen_co_activated(
                        self._user_id, mem_ids, boost=0.08,
                    )
                    total_strengthened += n

                report.memories_processed = total_processed
                report.links_strengthened = total_strengthened
                report.notes = f"Replayed {len(episodes)} episodes"
                await self._log_phase(store, cycle_id, report)

        except Exception as e:
            logger.error(f"SWS Replay failed: {e}", exc_info=True)
            report.success = False
            report.notes = str(e)

        report.duration_seconds = time.time() - start
        return report

    # =========================================================================
    # Phase 2: Pattern Extraction (LLM)
    # =========================================================================

    async def _phase_pattern_extraction(self, cycle_id: str) -> PhaseReport:
        """Cluster memories by shared concepts/tags, extract procedures via LLM."""
        report = PhaseReport(phase=DreamPhase.PATTERN_EXTRACTION)
        start = time.time()

        try:
            from app.database import get_db_context
            async with get_db_context() as db:
                store = self._store(db)

                # Cluster memories by concepts
                clusters = await self._cluster_by_concepts(store)
                if not clusters:
                    report.notes = "No clusters found for pattern extraction"
                    report.duration_seconds = time.time() - start
                    await self._log_phase(store, cycle_id, report)
                    return report

                total_procedures = 0
                phase_budget = min(DREAM_LLM_BUDGET_PATTERN, self._llm_calls_remaining)

                for concept, mem_ids in clusters.items():
                    if phase_budget <= 0 or self._llm_calls_remaining <= 0:
                        break

                    memories_text = await self._format_memories_for_llm(store, mem_ids[:10])
                    if not memories_text:
                        continue

                    patterns, called, in_tok, out_tok = await self._llm_extract_patterns(memories_text)
                    if called:
                        report.llm_calls += 1
                        report.input_tokens += in_tok
                        report.output_tokens += out_tok
                        phase_budget -= 1
                    report.memories_processed += len(mem_ids)

                    # Store extracted procedures
                    from app.services.cerebro.service import get_cerebro_service
                    svc = get_cerebro_service()
                    for pattern in patterns:
                        content = pattern.get("content") or pattern.get("pattern") or pattern.get("procedure")
                        if not content:
                            continue

                        # Dedup check
                        existing = await store.find_duplicate_content(self._user_id, content)
                        if existing:
                            continue

                        source_indices = pattern.get("source_indices", [])
                        source_ids = [mem_ids[i] for i in source_indices if i < len(mem_ids)]

                        result = await svc.store_procedure(
                            db, self._user_id, content,
                            tags=pattern.get("tags", [concept]),
                            derived_from=source_ids or mem_ids[:3],
                        )
                        if result and not result.get("error"):
                            total_procedures += 1
                            report.links_created += len(source_ids) or 3

                report.procedures_extracted = total_procedures
                report.notes = f"Extracted {total_procedures} procedures from {len(clusters)} clusters"
                await self._log_phase(store, cycle_id, report)

        except Exception as e:
            logger.error(f"Pattern Extraction failed: {e}", exc_info=True)
            report.success = False
            report.notes = str(e)

        report.duration_seconds = time.time() - start
        return report

    # =========================================================================
    # Phase 3: Schema Formation (LLM)
    # =========================================================================

    async def _phase_schema_formation(self, cycle_id: str) -> PhaseReport:
        """Abstract episodes into general principles via LLM."""
        report = PhaseReport(phase=DreamPhase.SCHEMA_FORMATION)
        start = time.time()

        try:
            from app.database import get_db_context
            async with get_db_context() as db:
                store = self._store(db)
                episodes = await store.get_unconsolidated_episodes(self._user_id)
                total_schemas = 0
                phase_budget = min(DREAM_LLM_BUDGET_SCHEMA, self._llm_calls_remaining)

                for ep in episodes:
                    if phase_budget <= 0 or self._llm_calls_remaining <= 0:
                        break

                    mem_ids = await store.get_episode_memory_ids(self._user_id, ep.id)
                    if len(mem_ids) < 2:
                        continue

                    memories_text = await self._format_memories_for_llm(store, mem_ids)
                    if not memories_text:
                        continue

                    schema_data, called, in_tok, out_tok = await self._llm_form_schema(memories_text)
                    if called:
                        report.llm_calls += 1
                        report.input_tokens += in_tok
                        report.output_tokens += out_tok
                        phase_budget -= 1

                    if schema_data and schema_data.get("content"):
                        # Get tags from first episode memory
                        first_node = await store.get_node(self._user_id, mem_ids[0]) if mem_ids else None
                        existing_tags = first_node.metadata.tags if first_node else []
                        episode_tags = list(set(
                            existing_tags + schema_data.get("tags", [])
                        ))

                        from app.services.cerebro.service import get_cerebro_service
                        svc = get_cerebro_service()
                        result = await svc.create_schema(
                            db, self._user_id, schema_data["content"],
                            source_ids=mem_ids,
                            tags=episode_tags,
                        )
                        if result and not result.get("error"):
                            total_schemas += 1
                            report.links_created += len(mem_ids)

                    report.memories_processed += len(mem_ids)

                report.schemas_extracted = total_schemas
                report.notes = f"Formed {total_schemas} schemas from {len(episodes)} episodes"
                await self._log_phase(store, cycle_id, report)

        except Exception as e:
            logger.error(f"Schema Formation failed: {e}", exc_info=True)
            report.success = False
            report.notes = str(e)

        report.duration_seconds = time.time() - start
        return report

    # =========================================================================
    # Phase 4: Emotional Reprocessing (algorithmic)
    # =========================================================================

    async def _phase_emotional_reprocessing(self, cycle_id: str) -> PhaseReport:
        """Adjust salience for negative outcomes (learn from mistakes)."""
        report = PhaseReport(phase=DreamPhase.EMOTIONAL_REPROCESSING)
        start = time.time()

        try:
            from app.database import get_db_context
            async with get_db_context() as db:
                store = self._store(db)
                episodes = await store.get_unconsolidated_episodes(self._user_id)

                for ep in episodes:
                    # Boost salience for memories in negative-valence episodes
                    valence_str = ep.overall_valence
                    if hasattr(valence_str, "value"):
                        valence_str = valence_str.value

                    if valence_str != "negative":
                        continue

                    mem_ids = await store.get_episode_memory_ids(self._user_id, ep.id)
                    for mid in mem_ids:
                        node = await store.get_node(self._user_id, mid)
                        if not node:
                            continue
                        # Boost salience by 0.15 for negative outcomes, capped at 1.0
                        new_salience = min(node.metadata.salience + 0.15, 1.0)
                        if new_salience != node.metadata.salience:
                            await db.execute(
                                __import__("sqlalchemy", fromlist=["text"]).text(
                                    "UPDATE cerebro_memory_nodes SET salience = :sal WHERE id = :id AND user_id = :uid"
                                ),
                                {"sal": new_salience, "id": mid, "uid": str(self._user_id)},
                            )
                            report.memories_processed += 1
                    await db.commit()

                report.notes = f"Reprocessed emotions for {report.memories_processed} memories"
                await self._log_phase(store, cycle_id, report)

        except Exception as e:
            logger.error(f"Emotional Reprocessing failed: {e}", exc_info=True)
            report.success = False
            report.notes = str(e)

        report.duration_seconds = time.time() - start
        return report

    # =========================================================================
    # Phase 5: Pruning (algorithmic)
    # =========================================================================

    async def _phase_pruning(self, cycle_id: str) -> PhaseReport:
        """Synaptic homeostasis: prune isolated, low-salience sensory memories."""
        report = PhaseReport(phase=DreamPhase.PRUNING)
        start = time.time()

        try:
            from app.database import get_db_context
            async with get_db_context() as db:
                store = self._store(db)

                cutoff = datetime.now() - timedelta(hours=DREAM_PRUNING_MIN_AGE_HOURS)

                # Single efficient SQL (cloud advantage over N+1 loop)
                pruned = await store.prune_isolated_sensory(
                    self._user_id,
                    max_salience=DREAM_PRUNING_MAX_SALIENCE,
                    cutoff=cutoff,
                )

                report.memories_pruned = pruned
                report.notes = f"Pruned {pruned} isolated sensory memories older than {DREAM_PRUNING_MIN_AGE_HOURS}h"
                await self._log_phase(store, cycle_id, report)

        except Exception as e:
            logger.error(f"Pruning failed: {e}", exc_info=True)
            report.success = False
            report.notes = str(e)

        report.duration_seconds = time.time() - start
        return report

    # =========================================================================
    # Phase 6: REM Recombination (LLM)
    # =========================================================================

    async def _phase_rem_recombination(self, cycle_id: str) -> PhaseReport:
        """REM dreaming: sample diverse memories, find unexpected connections."""
        report = PhaseReport(phase=DreamPhase.REM_RECOMBINATION)
        start = time.time()

        try:
            from app.database import get_db_context
            async with get_db_context() as db:
                store = self._store(db)

                all_ids = await store.get_all_node_ids(self._user_id)
                if len(all_ids) < 4:
                    report.notes = "Not enough memories for REM recombination"
                    report.duration_seconds = time.time() - start
                    await self._log_phase(store, cycle_id, report)
                    return report

                # Sample diverse memories
                sample_size = min(DREAM_REM_SAMPLE_SIZE, len(all_ids))
                sample = random.sample(all_ids, sample_size)

                # Load content
                sample_nodes = {}
                for mid in sample:
                    node = await store.get_node(self._user_id, mid)
                    if node and len(node.content) > 20:
                        sample_nodes[mid] = node

                pairs_checked = 0
                links_created = 0
                node_list = list(sample_nodes.items())
                phase_budget = min(DREAM_LLM_BUDGET_REM, self._llm_calls_remaining)

                max_pairs = min(DREAM_REM_PAIR_CHECKS, len(node_list) * (len(node_list) - 1) // 2)
                for _ in range(max_pairs):
                    if phase_budget <= 0 or self._llm_calls_remaining <= 0:
                        break
                    if len(node_list) < 2:
                        break

                    idx_a, idx_b = random.sample(range(len(node_list)), 2)
                    id_a, node_a = node_list[idx_a]
                    id_b, node_b = node_list[idx_b]

                    # Skip if already connected
                    if await store.has_link(self._user_id, id_a, id_b):
                        continue

                    # Prefer pairs from different types
                    if node_a.metadata.memory_type == node_b.metadata.memory_type:
                        if random.random() > 0.3:
                            continue

                    connection, called, in_tok, out_tok = await self._llm_rem_connect(
                        node_a.content, node_b.content,
                    )
                    if called:
                        report.llm_calls += 1
                        report.input_tokens += in_tok
                        report.output_tokens += out_tok
                        phase_budget -= 1
                    pairs_checked += 1

                    if connection and connection.get("connected"):
                        weight = min(max(connection.get("weight", 0.4), 0.1), 0.9)
                        if weight >= DREAM_REM_MIN_CONNECTION_STRENGTH:
                            link_type_str = connection.get("link_type", "semantic")
                            try:
                                lt = LinkType(link_type_str)
                            except ValueError:
                                lt = LinkType.SEMANTIC

                            await store.ensure_link(
                                self._user_id,
                                source_id=id_a,
                                target_id=id_b,
                                link_type=lt,
                                weight=weight,
                                source="dream_rem",
                                evidence=connection.get("reason", "REM recombination"),
                            )
                            links_created += 1

                report.memories_processed = len(sample_nodes)
                report.links_created = links_created
                report.notes = f"Checked {pairs_checked} pairs, created {links_created} new connections"
                await self._log_phase(store, cycle_id, report)

        except Exception as e:
            logger.error(f"REM Recombination failed: {e}", exc_info=True)
            report.success = False
            report.notes = str(e)

        report.duration_seconds = time.time() - start
        return report

    # =========================================================================
    # LLM helpers
    # =========================================================================

    async def _llm_call(self, prompt: str, system: str = SYSTEM_DREAM) -> tuple[Optional[str], bool, int, int]:
        """Make an async LLM call with budget + token tracking.

        Returns: (response_text, was_called, input_tokens, output_tokens)
        """
        if not self._llm:
            return None, False, 0, 0
        if self._llm_calls_remaining <= 0:
            logger.warning("LLM call budget exhausted")
            return None, False, 0, 0

        self._llm_calls_remaining -= 1
        try:
            messages = [{"role": "user", "content": prompt}]
            resp = await self._llm.chat(
                messages=messages,
                system=system,
                model=self._model,
                max_tokens=1024,
            )
            # Extract text from response
            text = ""
            if isinstance(resp, dict):
                content = resp.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = block.get("text", "")
                            break
                elif isinstance(content, str):
                    text = content

                # Track tokens
                usage = resp.get("usage", {})
                in_tok = usage.get("input_tokens", 0)
                out_tok = usage.get("output_tokens", 0)
                self._total_input_tokens += in_tok
                self._total_output_tokens += out_tok
                return text, True, in_tok, out_tok

            return str(resp), True, 0, 0

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return None, True, 0, 0

    def _parse_json(self, text: Optional[str]) -> Optional[any]:
        """Parse JSON from LLM response, handling markdown fences and preamble."""
        if not text:
            return None
        cleaned = text.strip()

        # Strip markdown code fences
        if "```" in cleaned:
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines).strip()

        # Try direct parse first
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Find JSON object or array in mixed text
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            s = cleaned.find(start_char)
            if s == -1:
                continue
            e = cleaned.rfind(end_char)
            if e <= s:
                continue
            try:
                return json.loads(cleaned[s:e + 1])
            except json.JSONDecodeError:
                continue

        logger.warning(f"Failed to parse LLM JSON: {cleaned[:100]}...")
        return None

    async def _llm_extract_patterns(self, memories_text: str) -> tuple[list[dict], bool, int, int]:
        """Ask LLM to extract patterns from memory cluster."""
        prompt = PROMPT_EXTRACT_PATTERNS.format(memories=memories_text)
        raw, called, in_tok, out_tok = await self._llm_call(prompt)
        parsed = self._parse_json(raw)
        if isinstance(parsed, list):
            return parsed, called, in_tok, out_tok
        return [], called, in_tok, out_tok

    async def _llm_form_schema(self, memories_text: str) -> tuple[Optional[dict], bool, int, int]:
        """Ask LLM to form an abstract schema from memories."""
        prompt = PROMPT_FORM_SCHEMA.format(memories=memories_text)
        raw, called, in_tok, out_tok = await self._llm_call(prompt)
        parsed = self._parse_json(raw) if raw else None
        return parsed, called, in_tok, out_tok

    async def _llm_rem_connect(self, content_a: str, content_b: str) -> tuple[Optional[dict], bool, int, int]:
        """Ask LLM to find unexpected connection between two memories."""
        prompt = PROMPT_REM_CONNECT.format(
            memory_a=content_a[:300],
            memory_b=content_b[:300],
        )
        raw, called, in_tok, out_tok = await self._llm_call(prompt)
        parsed = self._parse_json(raw) if raw else None
        return parsed, called, in_tok, out_tok

    # =========================================================================
    # Clustering helpers
    # =========================================================================

    async def _cluster_by_concepts(self, store) -> dict[str, list[str]]:
        """Cluster memories by shared concepts/tags (async)."""
        concept_map: dict[str, list[str]] = {}
        all_ids = await store.get_all_node_ids(self._user_id)

        for mid in all_ids:
            node = await store.get_node(self._user_id, mid)
            if not node:
                continue
            keys = set(node.metadata.concepts[:5] + node.metadata.tags)
            for key in keys:
                if key not in concept_map:
                    concept_map[key] = []
                concept_map[key].append(mid)

        return {
            k: v for k, v in concept_map.items()
            if len(v) >= DREAM_CLUSTER_MIN_SIZE
        }

    async def _format_memories_for_llm(self, store, mem_ids: list[str]) -> str:
        """Format memory contents for LLM prompt."""
        lines = []
        for i, mid in enumerate(mem_ids[:10]):
            node = await store.get_node(self._user_id, mid)
            if node:
                content = node.content[:200]
                lines.append(f"[{i}] {content}")
        return "\n".join(lines)

    # =========================================================================
    # Logging
    # =========================================================================

    async def _log_phase(self, store, cycle_id: str, report: PhaseReport) -> None:
        """Log a dream phase to the database."""
        try:
            await store.log_dream_phase(
                user_id=self._user_id,
                cycle_id=cycle_id,
                phase=report.phase.value,
                memories_processed=report.memories_processed,
                links_created=report.links_created,
                links_strengthened=report.links_strengthened,
                memories_pruned=report.memories_pruned,
                schemas_extracted=report.schemas_extracted,
                procedures_extracted=report.procedures_extracted,
                total_llm_calls=report.llm_calls,
                total_input_tokens=report.input_tokens,
                total_output_tokens=report.output_tokens,
                duration_seconds=report.duration_seconds,
                notes=report.notes,
                success=report.success,
                provider=self._provider,
                model_used=self._model,
            )
        except Exception as e:
            logger.error(f"Failed to log dream phase: {e}")
