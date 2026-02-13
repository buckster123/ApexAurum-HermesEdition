"""Targeted Dream Engine — Scoped consolidation for queued memories.

Subclass of AsyncDreamEngine that operates only on a user-provided set
of memory IDs plus their 1-hop graph neighbors. All 6 phases are scoped,
and pruning is skipped (don't delete what the user explicitly queued).

"The alchemist selects the ore, and the Athanor transmutes it."
"""

import logging
import random
import time
import uuid
from datetime import datetime
from typing import Optional

from app.cerebro.config import (
    DREAM_CLUSTER_MIN_SIZE,
    DREAM_LLM_BUDGET_PATTERN,
    DREAM_LLM_BUDGET_REM,
    DREAM_LLM_BUDGET_SCHEMA,
    DREAM_REM_MIN_CONNECTION_STRENGTH,
    DREAM_REM_PAIR_CHECKS,
)
from app.cerebro.types import DreamPhase, LinkType
from app.services.cerebro.dream import AsyncDreamEngine, DreamReport, PhaseReport

logger = logging.getLogger("cerebro-targeted-dream")


class TargetedDreamEngine(AsyncDreamEngine):
    """Dream engine that operates on a specific set of memories.

    Extends AsyncDreamEngine with scoped memory selection. The target set
    is expanded by 1 hop via associative links to provide context.
    """

    def __init__(
        self,
        user_id,
        memory_ids: list[str],
        llm=None,
        model: str = "claude-haiku-4-5-20251001",
        max_llm_calls: int = 20,
    ):
        super().__init__(user_id, llm, model, max_llm_calls)
        self._target_ids = set(memory_ids)
        self._expanded_ids: set[str] = set()

    async def run_cycle(self) -> DreamReport:
        """Run a targeted dream cycle scoped to queued memories + neighbors."""
        if self._running:
            raise RuntimeError("Dream cycle already in progress")

        self._running = True
        self._llm_calls_remaining = self._max_llm_calls
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        cycle_id = f"dream_t_{uuid.uuid4().hex[:10]}"
        report = DreamReport(cycle_id=cycle_id)
        report.scope = "targeted"
        report.target_count = len(self._target_ids)
        cycle_start = time.time()

        try:
            # Expand scope: target + 1-hop neighbors
            from app.database import get_db_context
            async with get_db_context() as db:
                store = self._store(db)
                neighbors = await store.get_neighbor_ids(
                    self._user_id, list(self._target_ids)
                )
                self._expanded_ids = self._target_ids | set(neighbors)

            logger.info(
                f"Targeted dream {cycle_id} for user {self._user_id}: "
                f"{len(self._target_ids)} targets, "
                f"{len(self._expanded_ids)} expanded scope"
            )

            # Run all 6 phases (scoped)
            report.phases.append(await self._phase_sws_replay(cycle_id))
            report.phases.append(await self._phase_pattern_extraction(cycle_id))
            report.phases.append(await self._phase_schema_formation(cycle_id))
            report.phases.append(await self._phase_emotional_reprocessing(cycle_id))
            report.phases.append(await self._phase_pruning(cycle_id))
            report.phases.append(await self._phase_rem_recombination(cycle_id))

            # Mark target episodes consolidated
            async with get_db_context() as db:
                store = self._store(db)
                episodes = await store.get_unconsolidated_episodes(self._user_id)
                consolidated = 0
                for ep in episodes:
                    mem_ids = await store.get_episode_memory_ids(self._user_id, ep.id)
                    if any(mid in self._target_ids for mid in mem_ids):
                        await store.mark_episode_consolidated(self._user_id, ep.id)
                        consolidated += 1
                report.episodes_consolidated = consolidated

            report.success = all(p.success for p in report.phases)
            logger.info(
                f"Targeted dream {cycle_id} complete: "
                f"{consolidated} episodes consolidated"
            )

        except Exception as e:
            logger.error(f"Targeted dream {cycle_id} failed: {e}", exc_info=True)
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
    # Phase overrides (scoped to expanded_ids)
    # =========================================================================

    async def _phase_sws_replay(self, cycle_id: str) -> PhaseReport:
        """SWS Replay scoped to episodes containing target memories."""
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
                targeted_episodes = 0

                for ep in episodes:
                    mem_ids = await store.get_episode_memory_ids(self._user_id, ep.id)
                    # Only process episodes with at least one target memory
                    if not any(mid in self._expanded_ids for mid in mem_ids):
                        continue
                    targeted_episodes += 1

                    if len(mem_ids) < 2:
                        continue

                    total_processed += len(mem_ids)
                    n = await store.batch_strengthen_co_activated(
                        self._user_id, mem_ids, boost=0.08,
                    )
                    total_strengthened += n

                report.memories_processed = total_processed
                report.links_strengthened = total_strengthened
                report.notes = f"Replayed {targeted_episodes} targeted episodes"
                await self._log_phase(store, cycle_id, report)

        except Exception as e:
            logger.error(f"Targeted SWS Replay failed: {e}", exc_info=True)
            report.success = False
            report.notes = str(e)

        report.duration_seconds = time.time() - start
        return report

    async def _phase_pattern_extraction(self, cycle_id: str) -> PhaseReport:
        """Pattern Extraction scoped to expanded_ids cluster."""
        report = PhaseReport(phase=DreamPhase.PATTERN_EXTRACTION)
        start = time.time()

        try:
            from app.database import get_db_context
            async with get_db_context() as db:
                store = self._store(db)

                # Cluster only within expanded scope
                clusters = await self._cluster_by_concepts_scoped(store)
                if not clusters:
                    report.notes = "No clusters found in targeted scope"
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

                    from app.services.cerebro.service import get_cerebro_service
                    svc = get_cerebro_service()
                    for pattern in patterns:
                        content = pattern.get("content") or pattern.get("pattern") or pattern.get("procedure")
                        if not content:
                            continue
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
                report.notes = f"Extracted {total_procedures} procedures from {len(clusters)} clusters (targeted)"
                await self._log_phase(store, cycle_id, report)

        except Exception as e:
            logger.error(f"Targeted Pattern Extraction failed: {e}", exc_info=True)
            report.success = False
            report.notes = str(e)

        report.duration_seconds = time.time() - start
        return report

    async def _phase_schema_formation(self, cycle_id: str) -> PhaseReport:
        """Schema Formation scoped to episodes with target memories."""
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
                    # Only episodes with target memories
                    if not any(mid in self._expanded_ids for mid in mem_ids):
                        continue
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
                report.notes = f"Formed {total_schemas} schemas (targeted)"
                await self._log_phase(store, cycle_id, report)

        except Exception as e:
            logger.error(f"Targeted Schema Formation failed: {e}", exc_info=True)
            report.success = False
            report.notes = str(e)

        report.duration_seconds = time.time() - start
        return report

    async def _phase_emotional_reprocessing(self, cycle_id: str) -> PhaseReport:
        """Emotional Reprocessing scoped to episodes with target memories."""
        report = PhaseReport(phase=DreamPhase.EMOTIONAL_REPROCESSING)
        start = time.time()

        try:
            from app.database import get_db_context
            async with get_db_context() as db:
                store = self._store(db)
                episodes = await store.get_unconsolidated_episodes(self._user_id)

                for ep in episodes:
                    mem_ids = await store.get_episode_memory_ids(self._user_id, ep.id)
                    if not any(mid in self._expanded_ids for mid in mem_ids):
                        continue

                    valence_str = ep.overall_valence
                    if hasattr(valence_str, "value"):
                        valence_str = valence_str.value
                    if valence_str != "negative":
                        continue

                    for mid in mem_ids:
                        node = await store.get_node(self._user_id, mid)
                        if not node:
                            continue
                        new_salience = min(node.metadata.salience + 0.15, 1.0)
                        if new_salience != node.metadata.salience:
                            from sqlalchemy import text as sa_text
                            await db.execute(
                                sa_text(
                                    "UPDATE cerebro_memory_nodes SET salience = :sal WHERE id = :id AND user_id = :uid"
                                ),
                                {"sal": new_salience, "id": mid, "uid": str(self._user_id)},
                            )
                            report.memories_processed += 1
                    await db.commit()

                report.notes = f"Reprocessed emotions for {report.memories_processed} memories (targeted)"
                await self._log_phase(store, cycle_id, report)

        except Exception as e:
            logger.error(f"Targeted Emotional Reprocessing failed: {e}", exc_info=True)
            report.success = False
            report.notes = str(e)

        report.duration_seconds = time.time() - start
        return report

    async def _phase_pruning(self, cycle_id: str) -> PhaseReport:
        """Pruning SKIPPED in targeted mode — don't delete what user queued."""
        report = PhaseReport(phase=DreamPhase.PRUNING)
        report.notes = "Pruning skipped in targeted mode"
        report.duration_seconds = 0.0

        try:
            from app.database import get_db_context
            async with get_db_context() as db:
                store = self._store(db)
                await self._log_phase(store, cycle_id, report)
        except Exception:
            pass

        return report

    async def _phase_rem_recombination(self, cycle_id: str) -> PhaseReport:
        """REM Recombination scoped to expanded_ids."""
        report = PhaseReport(phase=DreamPhase.REM_RECOMBINATION)
        start = time.time()

        try:
            from app.database import get_db_context
            async with get_db_context() as db:
                store = self._store(db)

                pool_ids = list(self._expanded_ids)
                if len(pool_ids) < 4:
                    report.notes = "Not enough memories in targeted scope for REM"
                    report.duration_seconds = time.time() - start
                    await self._log_phase(store, cycle_id, report)
                    return report

                # Load content
                sample_nodes = {}
                for mid in pool_ids:
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

                    if await store.has_link(self._user_id, id_a, id_b):
                        continue

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
                                source="dream_rem_targeted",
                                evidence=connection.get("reason", "Targeted REM recombination"),
                            )
                            links_created += 1

                report.memories_processed = len(sample_nodes)
                report.links_created = links_created
                report.notes = f"Checked {pairs_checked} pairs, created {links_created} connections (targeted)"
                await self._log_phase(store, cycle_id, report)

        except Exception as e:
            logger.error(f"Targeted REM Recombination failed: {e}", exc_info=True)
            report.success = False
            report.notes = str(e)

        report.duration_seconds = time.time() - start
        return report

    # =========================================================================
    # Scoped clustering helper
    # =========================================================================

    async def _cluster_by_concepts_scoped(self, store) -> dict[str, list[str]]:
        """Cluster memories by concepts, scoped to expanded_ids."""
        concept_map: dict[str, list[str]] = {}

        for mid in self._expanded_ids:
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
