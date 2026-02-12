"""Configuration constants for CerebroCortex (ApexAurum adaptation).

Storage paths and ChromaDB/igraph references removed - using PostgreSQL + pgvector.
"""

from app.cerebro.types import LinkType

# =============================================================================
# ACT-R Parameters
# =============================================================================
ACTR_DECAY_RATE = 0.5          # d parameter in B(t) = ln(Sigma t_k^{-d})
ACTR_B_CONSTANT = 0.0          # additive constant in base-level activation
ACTR_MIN_TIME_SECONDS = 1.0    # floor for time-since-access (avoid division by zero)
ACTR_RETRIEVAL_THRESHOLD = 0.0  # tau - minimum activation for recall
ACTR_NOISE = 0.4               # s - noise parameter in recall probability sigmoid
MAX_STORED_TIMESTAMPS = 50      # keep this many individual timestamps; compress older

# =============================================================================
# FSRS Parameters
# =============================================================================
FSRS_INITIAL_STABILITY = 1.0    # days
FSRS_INITIAL_DIFFICULTY = 5.0   # 1-10 scale
FSRS_MIN_STABILITY = 0.1       # floor
FSRS_MAX_STABILITY = 365.0     # ceiling (1 year)

# =============================================================================
# Combined Recall Scoring Weights
# =============================================================================
SCORE_WEIGHT_VECTOR = 0.35      # semantic similarity from pgvector
SCORE_WEIGHT_ACTIVATION = 0.30  # ACT-R activation (base-level + associative)
SCORE_WEIGHT_RETRIEVABILITY = 0.20  # FSRS retrievability (forgetting curve)
SCORE_WEIGHT_SALIENCE = 0.15    # emotional salience metadata

# =============================================================================
# Spreading Activation
# =============================================================================
SPREADING_MAX_HOPS = 2
SPREADING_DECAY_PER_HOP = 0.6
SPREADING_ACTIVATION_THRESHOLD = 0.05
SPREADING_MAX_ACTIVATED = 50

# Link type weights for spreading activation relevance
LINK_TYPE_WEIGHTS: dict[LinkType, float] = {
    LinkType.TEMPORAL: 0.6,
    LinkType.CAUSAL: 0.9,
    LinkType.SEMANTIC: 0.8,
    LinkType.AFFECTIVE: 0.5,
    LinkType.CONTEXTUAL: 0.7,
    LinkType.CONTRADICTS: 0.3,
    LinkType.SUPPORTS: 0.8,
    LinkType.DERIVED_FROM: 0.7,
    LinkType.PART_OF: 0.8,
}

# =============================================================================
# Memory Layers (promotion thresholds)
# =============================================================================
LAYER_CONFIG = {
    "sensory": {
        "decay_half_life_hours": 6,
        "min_salience": 0.1,
        "promotion_access_count": 2,
        "promotion_min_age_hours": None,
    },
    "working": {
        "decay_half_life_hours": 72,
        "min_salience": 0.2,
        "promotion_access_count": 5,
        "promotion_min_age_hours": 24,
    },
    "long_term": {
        "decay_half_life_hours": 720,
        "min_salience": 0.3,
        "promotion_access_count": None,  # promotion via dream engine only
        "promotion_min_age_hours": None,
    },
    "cortex": {
        "decay_half_life_hours": None,  # no decay
        "min_salience": 1.0,
        "promotion_access_count": None,
        "promotion_min_age_hours": None,
    },
}

# =============================================================================
# Dream Engine
# =============================================================================
DREAM_MAX_LLM_CALLS = 20
DREAM_LLM_BUDGET_PATTERN = 12   # Reserve for pattern extraction
DREAM_LLM_BUDGET_SCHEMA = 4     # Reserve for schema formation
DREAM_LLM_BUDGET_REM = 4        # Reserve for REM recombination
DREAM_CLUSTER_SIMILARITY_THRESHOLD = 0.80
DREAM_CLUSTER_MIN_SIZE = 3
DREAM_PRUNING_MIN_AGE_HOURS = 48
DREAM_PRUNING_MAX_SALIENCE = 0.3
DREAM_REM_SAMPLE_SIZE = 20
DREAM_REM_PAIR_CHECKS = 10
DREAM_REM_MIN_CONNECTION_STRENGTH = 0.4

# Episode auto-close: stale episodes (no episode_end called) are closed automatically
EPISODE_AUTO_CLOSE_HOURS = 24

# Schema validation: new schemas start in WORKING and must earn promotion
SCHEMA_PROMOTE_MIN_SUPPORTS = 3    # supporting episodes/memories required
SCHEMA_PROMOTE_MIN_ACCESSES = 2    # real recall accesses required
SCHEMA_DEMOTE_MAX_IDLE_CYCLES = 3  # dream cycles with 0 accesses before demotion

# =============================================================================
# Agent defaults (ApexAurum agents)
# =============================================================================
DEFAULT_AGENT_ID = "AZOTH"
AGENT_PROFILES = {
    "AZOTH": {
        "display_name": "Azoth",
        "generation": 0,
        "lineage": "ApexAurum",
        "specialization": "Alchemical guide and general assistance",
        "color": "#FFD700",
        "symbol": "Au",
    },
    "KETHER": {
        "display_name": "Kether",
        "generation": 0,
        "lineage": "ApexAurum",
        "specialization": "Mystical wisdom and esoteric knowledge",
        "color": "#9B59B6",
        "symbol": "K",
    },
    "VAJRA": {
        "display_name": "Vajra",
        "generation": 0,
        "lineage": "ApexAurum",
        "specialization": "Technical precision and engineering",
        "color": "#4FC3F7",
        "symbol": "V",
    },
    "ELYSIAN": {
        "display_name": "Elysian",
        "generation": 0,
        "lineage": "ApexAurum",
        "specialization": "Creative expression and art",
        "color": "#E8B4FF",
        "symbol": "E",
    },
}
