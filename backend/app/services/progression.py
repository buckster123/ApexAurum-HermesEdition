"""
Progression Service - Quest Engine Core

Milestone definitions, feature gating, and progression tracking
for the Athaverse quest tier system.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import TIER_LIMITS, TIER_HIERARCHY
from app.models.progression import UserProgression

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# MILESTONE DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

QUEST_STAGES = ["seeker", "adept", "opus", "azothic"]


def _next_stage(current: str) -> str:
    """Get the next quest stage after the current one."""
    idx = QUEST_STAGES.index(current)
    if idx < len(QUEST_STAGES) - 1:
        return QUEST_STAGES[idx + 1]
    return current  # Already at max


class MilestoneDef:
    """A milestone definition with a checker function."""

    def __init__(self, id: str, name: str, description: str, feature_unlocked: str, stage: str, check_fn):
        self.id = id
        self.name = name
        self.description = description
        self.feature_unlocked = feature_unlocked
        self.stage = stage
        self.check_fn = check_fn

    def check(self, prog: UserProgression, task_event: dict) -> bool:
        """Check if this milestone is met given current progression and task event."""
        return self.check_fn(prog, task_event)


# --- Checker functions ---

def _check_first_chat(prog, event):
    return prog.total_tasks >= 1 or event.get("type") == "chat"


def _check_meet_agents(prog, event):
    agents_used = set()
    for agent_id, stats in (prog.agent_stats or {}).items():
        if stats.get("tasks", 0) > 0:
            agents_used.add(agent_id)
    if event.get("agents"):
        for a in event["agents"]:
            agents_used.add(a)
    return len(agents_used) >= 2


def _check_zone_visit(prog, event):
    zones_used = set()
    for zone, stats in (prog.zone_stats or {}).items():
        if stats.get("tasks", 0) > 0:
            zones_used.add(zone)
    if event.get("zone"):
        zones_used.add(event["zone"])
    return len(zones_used) >= 1


def _check_web_search(prog, event):
    tools_used = event.get("tools_used", [])
    return "web_search" in tools_used or "browser_navigate" in tools_used


def _check_file_upload(prog, event):
    return event.get("has_file_upload", False) or event.get("type") == "file_upload"


def _check_three_zones(prog, event):
    zones_used = set()
    for zone, stats in (prog.zone_stats or {}).items():
        if stats.get("tasks", 0) > 0:
            zones_used.add(zone)
    if event.get("zone"):
        zones_used.add(event["zone"])
    return len(zones_used) >= 3


def _check_council_first(prog, event):
    return event.get("type") == "council" or event.get("mode") == "council"


def _check_seeker_mastery(prog, event):
    total = prog.total_tasks + (1 if event.get("type") else 0)
    return total >= 15


def _check_music_gen(prog, event):
    return event.get("type") == "music" or event.get("zone") == "djbooth"


def _check_memory_store(prog, event):
    tools_used = event.get("tools_used", [])
    return "store_memory" in tools_used or event.get("zone") == "memory_garden"


def _check_bridge_connect(prog, event):
    return event.get("zone") == "bridge" or event.get("type") == "bridge"


def _check_agent_level_3(prog, event):
    for agent_id, stats in (prog.agent_stats or {}).items():
        xp = stats.get("xp", 0)
        level = min(10, xp // 5)
        if level >= 3:
            return True
    return False


def _check_opus_model(prog, event):
    model = event.get("model", "")
    return "opus" in model.lower()


def _check_zone_master(prog, event):
    for zone, stats in (prog.zone_stats or {}).items():
        if stats.get("tasks", 0) >= 10:
            return True
    return False


def _check_council_expert(prog, event):
    council_count = sum(
        1 for z, s in (prog.zone_stats or {}).items()
        if z == "council" and s.get("tasks", 0) >= 5
    )
    # Also check agent_stats for council mode tasks
    return council_count > 0 or prog.agent_stats.get("_council_sessions", 0) >= 5


def _check_adept_mastery(prog, event):
    total = prog.total_tasks + (1 if event.get("type") else 0)
    return total >= 50


def _check_dream_engine(prog, event):
    return event.get("type") == "dream" or event.get("zone") == "dream"


def _check_nursery_train(prog, event):
    return event.get("type") == "nursery_train" or event.get("zone") == "nursery"


def _check_all_zones(prog, event):
    zones_used = set()
    for zone, stats in (prog.zone_stats or {}).items():
        if stats.get("tasks", 0) > 0:
            zones_used.add(zone)
    if event.get("zone"):
        zones_used.add(event["zone"])
    return len(zones_used) >= 8


def _check_agent_level_7(prog, event):
    for agent_id, stats in (prog.agent_stats or {}).items():
        if agent_id.startswith("_"):
            continue
        xp = stats.get("xp", 0)
        level = min(10, xp // 5)
        if level >= 7:
            return True
    return False


def _check_full_opus(prog, event):
    total = prog.total_tasks + (1 if event.get("type") else 0)
    # All prior milestones must be completed
    prior_milestones = [m.id for m in MILESTONE_DEFINITIONS["seeker"]] + [m.id for m in MILESTONE_DEFINITIONS["adept"]]
    all_prior = all(m in (prog.milestones_completed or []) for m in prior_milestones)
    return total >= 100 and all_prior


def _check_all_agents_5(prog, event):
    required = {"AZOTH", "VAJRA", "ELYSIAN", "KETHER"}
    for agent_id in required:
        stats = (prog.agent_stats or {}).get(agent_id, {})
        xp = stats.get("xp", 0)
        level = min(10, xp // 5)
        if level < 5:
            return False
    return True


def _check_council_master(prog, event):
    return prog.agent_stats.get("_council_sessions", 0) >= 20


def _check_athanor_complete(prog, event):
    total = prog.total_tasks + (1 if event.get("type") else 0)
    return total >= 200


def _check_sensorhead_earned(prog, event):
    # All prior milestones completed + athanor_complete
    all_milestones = []
    for stage in ["seeker", "adept", "opus", "azothic"]:
        for m in MILESTONE_DEFINITIONS.get(stage, []):
            if m.id != "sensorhead_earned":
                all_milestones.append(m.id)
    return all(m in (prog.milestones_completed or []) for m in all_milestones)


# --- Build the milestone trees ---

MILESTONE_DEFINITIONS = {
    "seeker": [
        MilestoneDef("first_chat", "First Steps", "Send your first message to any agent", "basic_chat", "seeker", _check_first_chat),
        MilestoneDef("meet_agents", "Meet the Council", "Chat with 2 different agents", "all_agents", "seeker", _check_meet_agents),
        MilestoneDef("zone_visit", "Village Explorer", "Complete a task at any Village zone", "village_tasks", "seeker", _check_zone_visit),
        MilestoneDef("web_search", "Knowledge Seeker", "Use web search via the Library zone", "web_search", "seeker", _check_web_search),
        MilestoneDef("file_upload", "Archivist", "Upload a file in a task dialog", "file_vault", "seeker", _check_file_upload),
        MilestoneDef("three_zones", "Pathfinder", "Complete tasks at 3 different zones", "tool_categories", "seeker", _check_three_zones),
        MilestoneDef("council_first", "Council Convened", "Run a Council deliberation", "multi_agent", "seeker", _check_council_first),
        MilestoneDef("seeker_mastery", "Seeker Mastery", "Complete 15 total tasks", "full_seeker", "seeker", _check_seeker_mastery),
    ],
    "adept": [
        MilestoneDef("music_gen", "First Composition", "Generate a music track at the DJ Booth", "music_gen", "adept", _check_music_gen),
        MilestoneDef("memory_store", "Memory Keeper", "Store a memory at the Memory Garden", "memory_system", "adept", _check_memory_store),
        MilestoneDef("bridge_connect", "Bridge Builder", "Use an external API via Bridge Portal", "external_integrations", "adept", _check_bridge_connect),
        MilestoneDef("agent_level_3", "Agent Trainer", "Get any agent to level 3", "agent_customization", "adept", _check_agent_level_3),
        MilestoneDef("opus_model", "Opus Ascension", "Use an Opus-tier model", "opus_model_limited", "adept", _check_opus_model),
        MilestoneDef("zone_master", "Zone Specialist", "Complete 10 tasks at one zone", "zone_specialization", "adept", _check_zone_master),
        MilestoneDef("council_expert", "Council Expert", "Run 5 Council sessions", "advanced_council", "adept", _check_council_expert),
        MilestoneDef("adept_mastery", "Adept Mastery", "Complete 50 total tasks", "full_adept", "adept", _check_adept_mastery),
    ],
    "opus": [
        MilestoneDef("dream_engine", "Dream Walker", "First Dream Engine session", "dream_engine", "opus", _check_dream_engine),
        MilestoneDef("nursery_train", "Model Alchemist", "Train a custom model in the Nursery", "model_training", "opus", _check_nursery_train),
        MilestoneDef("all_zones", "Cartographer", "Complete tasks in all 8 zones", "full_zone_mastery", "opus", _check_all_zones),
        MilestoneDef("agent_level_7", "Agent Master", "Get any agent to level 7", "enhanced_agents", "opus", _check_agent_level_7),
        MilestoneDef("full_opus", "Opus Mastery", "100 total tasks + all prior milestones", "full_opus", "opus", _check_full_opus),
    ],
    "azothic": [
        MilestoneDef("all_agents_5", "The Full House", "All 4 agents at level 5+", "pac_mode", "azothic", _check_all_agents_5),
        MilestoneDef("council_master", "Grand Council", "20 Council sessions", "unlimited_council", "azothic", _check_council_master),
        MilestoneDef("athanor_complete", "The Great Work", "200 total tasks + all achievements", "full_azothic", "azothic", _check_athanor_complete),
        MilestoneDef("sensorhead_earned", "Azothic Alchemist", "Complete the Azothic quest", "sensorhead_prize", "azothic", _check_sensorhead_earned),
    ],
}

# Flat lookup for milestone by ID
ALL_MILESTONES = {}
for stage_milestones in MILESTONE_DEFINITIONS.values():
    for m in stage_milestones:
        ALL_MILESTONES[m.id] = m


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

FEATURE_REGISTRY = {
    # Seeker features
    "basic_chat": {"tier": "seeker", "quest_milestone": "first_chat"},
    "all_agents": {"tier": "seeker", "quest_milestone": "meet_agents"},
    "village_tasks": {"tier": "seeker", "quest_milestone": "zone_visit"},
    "web_search": {"tier": "seeker", "quest_milestone": "web_search"},
    "file_vault": {"tier": "seeker", "quest_milestone": "file_upload"},
    "tool_categories": {"tier": "seeker", "quest_milestone": "three_zones"},
    "multi_agent": {"tier": "seeker", "quest_milestone": "council_first"},
    "full_seeker": {"tier": "seeker", "quest_milestone": "seeker_mastery"},

    # Adept features
    "music_gen": {"tier": "adept", "quest_milestone": "music_gen"},
    "memory_system": {"tier": "adept", "quest_milestone": "memory_store"},
    "external_integrations": {"tier": "adept", "quest_milestone": "bridge_connect"},
    "agent_customization": {"tier": "adept", "quest_milestone": "agent_level_3"},
    "opus_model_limited": {"tier": "adept", "quest_milestone": "opus_model"},
    "zone_specialization": {"tier": "adept", "quest_milestone": "zone_master"},
    "advanced_council": {"tier": "adept", "quest_milestone": "council_expert"},
    "full_adept": {"tier": "adept", "quest_milestone": "adept_mastery"},

    # Opus features
    "dream_engine": {"tier": "opus", "quest_milestone": "dream_engine"},
    "model_training": {"tier": "opus", "quest_milestone": "nursery_train"},
    "full_zone_mastery": {"tier": "opus", "quest_milestone": "all_zones"},
    "enhanced_agents": {"tier": "opus", "quest_milestone": "agent_level_7"},
    "full_opus": {"tier": "opus", "quest_milestone": "full_opus"},

    # Azothic features
    "pac_mode": {"tier": "azothic", "quest_milestone": "all_agents_5"},
    "unlimited_council": {"tier": "azothic", "quest_milestone": "council_master"},
    "full_azothic": {"tier": "azothic", "quest_milestone": "athanor_complete"},
    "sensorhead_prize": {"tier": "azothic", "quest_milestone": "sensorhead_earned"},
}


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE GATING
# ═══════════════════════════════════════════════════════════════════════════════

def check_feature_access(user, feature: str) -> bool:
    """
    Check if user can access a feature.

    Classic tier users: check tier level (existing behavior).
    Quest tier users: check progression milestones.
    """
    if not hasattr(user, 'progression') or not user.progression or not user.progression.quest_active:
        # Classic path — existing tier check via TIER_HIERARCHY
        sub_tier = getattr(user, 'subscription', None)
        user_tier = sub_tier.tier if sub_tier else "free_trial"
        feature_def = FEATURE_REGISTRY.get(feature)
        if not feature_def:
            return True  # Unknown feature = allow
        required_tier = feature_def["tier"]
        return TIER_HIERARCHY.get(user_tier, 0) >= TIER_HIERARCHY.get(required_tier, 0)

    # Quest path — check if feature is unlocked via milestones
    return feature in (user.progression.features_unlocked or [])


def get_locked_feature_info(feature: str) -> dict:
    """Get info about a locked feature for the frontend nudge response."""
    feature_def = FEATURE_REGISTRY.get(feature, {})
    milestone_id = feature_def.get("quest_milestone")
    milestone = ALL_MILESTONES.get(milestone_id)

    return {
        "error": "feature_locked",
        "feature": feature,
        "milestone_required": milestone_id,
        "milestone_description": milestone.description if milestone else "Complete the required milestone",
        "milestone_name": milestone.name if milestone else "Unknown",
        "quest_stage": feature_def.get("tier", "seeker"),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PROGRESSION SERVICE
# ═══════════════════════════════════════════════════════════════════════════════

class ProgressionService:
    """Service for quest progression operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, user_id: UUID, quest_active: bool = False) -> UserProgression:
        """Get or create progression record for a user."""
        result = await self.db.execute(
            select(UserProgression).where(UserProgression.user_id == user_id)
        )
        prog = result.scalar_one_or_none()

        if prog:
            return prog

        prog = UserProgression(
            id=uuid4(),
            user_id=user_id,
            quest_active=quest_active,
            quest_stage="seeker",
            quest_started_at=datetime.now(timezone.utc) if quest_active else None,
            milestones_completed=[],
            features_unlocked=[],
            agent_stats={},
            zone_stats={},
            achievements=[],
            total_tasks=0,
        )
        self.db.add(prog)
        return prog

    async def get_progression(self, user_id: UUID) -> Optional[UserProgression]:
        """Get progression for a user (None if not exists)."""
        result = await self.db.execute(
            select(UserProgression).where(UserProgression.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def check_milestones(self, user_id: UUID, task_event: dict) -> dict:
        """
        Check if a task completion triggers any new milestones.

        Returns dict with new_milestones, new_features, stage_complete.
        """
        prog = await self.get_progression(user_id)
        if not prog or not prog.quest_active:
            return {"new_milestones": [], "new_features": [], "stage_complete": False}

        stage_milestones = MILESTONE_DEFINITIONS.get(prog.quest_stage, [])
        newly_completed = []
        newly_unlocked = []

        for milestone in stage_milestones:
            if milestone.id in (prog.milestones_completed or []):
                continue
            if milestone.check(prog, task_event):
                # Use list copy + append to trigger JSONB change detection
                completed = list(prog.milestones_completed or [])
                completed.append(milestone.id)
                prog.milestones_completed = completed

                unlocked = list(prog.features_unlocked or [])
                unlocked.append(milestone.feature_unlocked)
                prog.features_unlocked = unlocked

                newly_completed.append({
                    "id": milestone.id,
                    "name": milestone.name,
                    "description": milestone.description,
                    "feature_unlocked": milestone.feature_unlocked,
                })
                newly_unlocked.append(milestone.feature_unlocked)

                logger.info(f"Milestone completed: {milestone.id} for user {user_id}")

        # Check stage completion
        stage_complete = False
        if all(m.id in (prog.milestones_completed or []) for m in stage_milestones):
            old_stage = prog.quest_stage
            prog.quest_stage = _next_stage(prog.quest_stage)
            stage_complete = old_stage != prog.quest_stage
            if stage_complete:
                logger.info(f"Stage complete: {old_stage} -> {prog.quest_stage} for user {user_id}")

        prog.updated_at = datetime.now(timezone.utc)

        return {
            "new_milestones": newly_completed,
            "new_features": newly_unlocked,
            "stage_complete": stage_complete,
            "new_stage": prog.quest_stage if stage_complete else None,
        }

    async def sync_stats(self, user_id: UUID, stats: dict) -> UserProgression:
        """
        Sync E5 localStorage stats from frontend to server.

        Accepts the full stats blob from useVillageGamification.
        """
        prog = await self.get_or_create(user_id)

        if "agents" in stats:
            prog.agent_stats = stats["agents"]
        if "zones" in stats:
            prog.zone_stats = stats["zones"]
        if "achievements" in stats:
            prog.achievements = stats["achievements"]
        if "totalTasks" in stats:
            prog.total_tasks = stats["totalTasks"]

        prog.updated_at = datetime.now(timezone.utc)
        return prog

    async def get_progress_response(self, user_id: UUID) -> dict:
        """Build the full quest progress response for the frontend."""
        prog = await self.get_progression(user_id)

        if not prog:
            return {
                "quest_active": False,
                "quest_stage": None,
                "milestones": [],
                "features_unlocked": [],
                "next_milestone": None,
                "stage_progress": 0,
                "stage_total": 0,
                "agent_stats": {},
                "zone_stats": {},
                "achievements": [],
                "total_tasks": 0,
            }

        stage_milestones = MILESTONE_DEFINITIONS.get(prog.quest_stage, [])
        completed_ids = set(prog.milestones_completed or [])

        milestones = []
        next_milestone = None
        for m in stage_milestones:
            is_completed = m.id in completed_ids
            milestone_data = {
                "id": m.id,
                "name": m.name,
                "description": m.description,
                "feature_unlocked": m.feature_unlocked,
                "completed": is_completed,
            }
            milestones.append(milestone_data)

            if not is_completed and next_milestone is None:
                next_milestone = milestone_data

        stage_progress = sum(1 for m in stage_milestones if m.id in completed_ids)

        return {
            "quest_active": prog.quest_active,
            "quest_stage": prog.quest_stage,
            "milestones": milestones,
            "features_unlocked": prog.features_unlocked or [],
            "next_milestone": next_milestone,
            "stage_progress": stage_progress,
            "stage_total": len(stage_milestones),
            "agent_stats": prog.agent_stats or {},
            "zone_stats": prog.zone_stats or {},
            "achievements": prog.achievements or [],
            "total_tasks": prog.total_tasks,
        }

    async def activate_quest(self, user_id: UUID) -> UserProgression:
        """Activate quest mode for a user (called when subscribing to quest tier)."""
        prog = await self.get_or_create(user_id, quest_active=True)
        prog.quest_active = True
        prog.quest_started_at = datetime.now(timezone.utc)
        prog.updated_at = datetime.now(timezone.utc)
        return prog

    async def deactivate_quest(self, user_id: UUID, unlock_all: bool = False) -> Optional[UserProgression]:
        """
        Deactivate quest mode (upgrade to classic tier).

        If unlock_all=True, marks all features as unlocked (classic tier = everything).
        Preserves progression data for reference.
        """
        prog = await self.get_progression(user_id)
        if not prog:
            return None

        prog.quest_active = False
        if unlock_all:
            all_features = list(FEATURE_REGISTRY.keys())
            prog.features_unlocked = all_features

        prog.updated_at = datetime.now(timezone.utc)
        return prog
