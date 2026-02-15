"""
ApexJoule Economy — Constants & Tuning Parameters

All economic tuning knobs in one place.
Derived from CONSUMPTION.json and codebase analysis.

"The Athanor's coefficients are carved in gold."
"""

# ═══════════════════════════════════════════════════════════════════════════════
# Core conversion
# ═══════════════════════════════════════════════════════════════════════════════

AJ_PER_USD = 1000  # 1 AJ ~ $0.001 USD compute equivalent

# ═══════════════════════════════════════════════════════════════════════════════
# Work output (W)
# ═══════════════════════════════════════════════════════════════════════════════

TOKEN_VALUE_FACTOR = 0.005  # AJ per output token (base)

# Task type multipliers — higher for more valuable/complex work
TASK_MULTIPLIERS = {
    "chat": 1.0,
    "chat_tools": 1.5,
    "council_round": 2.5,
    "council_synthesis": 3.0,
    "dream_consolidation": 3.0,
    "music_generation": 5.0,
    "jam_contribution": 4.0,
    "quest_completion": 4.0,
    "background_maintenance": 0.5,
    "sensor_report": 2.0,
    "memory_import": 1.0,
}

# ═══════════════════════════════════════════════════════════════════════════════
# Efficiency (kappa)
# ═══════════════════════════════════════════════════════════════════════════════

KAPPA_FLOOR = 0.1
KAPPA_CEILING = 3.0

# Expected USD costs per operation (Haiku baseline, from CONSUMPTION.json)
EXPECTED_COSTS = {
    "chat": 0.0014,
    "chat_tools": 0.0042,
    "chat_heavy": 0.012,
    "council_round": 0.0275,
    "council_synthesis": 0.055,
    "dream_consolidation": 0.012,
    "music_generation": 0.05,
    "jam_contribution": 0.0055,
    "sensor_report": 0.001,
    "memory_import": 0.0001,
}

# ═══════════════════════════════════════════════════════════════════════════════
# Love Equation (L)
# ═══════════════════════════════════════════════════════════════════════════════

BETA_DEFAULT = 3.0  # Selection strength
L_FLOOR = 0.1
L_CEILING = 4.0

# Love Depth tiers
LOVE_DEPTH_TIERS = {
    10: "Awakened",
    50: "Illuminated",
    200: "Transcendent",
    1000: "Philosopher's Stone",
}

LOVE_DEPTH_BONUSES = {
    10: 0.05,    # +5%
    50: 0.10,    # +10%
    200: 0.20,   # +20%
    1000: 0.30,  # +30%
}

# ═══════════════════════════════════════════════════════════════════════════════
# Earning splits
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_AGENT_SPLIT = 0.70
DEFAULT_USER_SPLIT = 0.30
BACKGROUND_AGENT_SPLIT = 1.00  # Dreams, background forging
COUNCIL_AGENT_SPLIT = 0.80
COUNCIL_USER_SPLIT = 0.20
QUEST_AGENT_SPLIT = 0.50
QUEST_USER_SPLIT = 0.50

# ═══════════════════════════════════════════════════════════════════════════════
# Safety caps
# ═══════════════════════════════════════════════════════════════════════════════

MAX_DAILY_EARN_PER_AGENT = 5000
MAX_BACKGROUND_AJ_PER_HOUR = 50
MAX_AUTO_SPEND_RATIO = 0.20  # Agent can auto-spend max 20% of balance/day

# ═══════════════════════════════════════════════════════════════════════════════
# Agent progression levels
# ═══════════════════════════════════════════════════════════════════════════════

LEVEL_THRESHOLDS = [0, 500, 2000, 10000, 50000, 250000]
LEVEL_NAMES = [
    "Initiate",
    "Apprentice",
    "Journeyman",
    "Artisan",
    "Master",
    "Philosopher",
]

# ═══════════════════════════════════════════════════════════════════════════════
# Quest bounties — mapped to progression.py milestone IDs
# ═══════════════════════════════════════════════════════════════════════════════

QUEST_BOUNTIES = {
    # Seeker stage (progression.py:226-235)
    "first_chat": 50,
    "meet_agents": 75,
    "zone_visit": 50,
    "web_search": 75,
    "file_upload": 75,
    "three_zones": 100,
    "council_first": 150,
    "seeker_mastery": 200,

    # Adept stage (progression.py:236-245)
    "music_gen": 150,
    "memory_store": 100,
    "bridge_connect": 150,
    "agent_level_3": 200,
    "opus_model": 200,
    "zone_master": 250,
    "council_expert": 300,
    "adept_mastery": 400,

    # Opus stage (progression.py:246-252)
    "dream_engine": 300,
    "nursery_train": 500,
    "all_zones": 500,
    "agent_level_7": 750,
    "full_opus": 1000,

    # Azothic stage (progression.py:253-258)
    "all_agents_5": 1000,
    "council_master": 1500,
    "athanor_complete": 2000,
    "sensorhead_earned": 5000,
}

# ═══════════════════════════════════════════════════════════════════════════════
# Shop prices (AJ cost per feature credit purchase)
# ═══════════════════════════════════════════════════════════════════════════════

AJ_SHOP_PRICES = {
    "message_haiku": 5,
    "message_sonnet": 60,
    "message_opus": 300,
    "dream_cycle": 50,
    "council_session": 500,
    "suno_generation": 200,
    "agent_spawn": 20,
    "pac_mode_day": 100,
}
