# rpg_stats.py
"""
RPG-Style Stat Bars & Archetype Detection for Beyblade Analytics

This module calculates 5 RPG-style stat bars (0.0-5.0) for each Beyblade:
1. Attack - Offensive pressure and high-impact scoring potential
2. Defense - Ability to avoid high-impact losses
3. Stamina - Endurance and spin finish performance
4. Control - Consistency, stability, and match flow management
5. Meta Impact - Overall competitive relevance and influence on the meta

Each stat is derived from multiple sub-metrics combined via weighted formulas.
"""

import csv
import json
import statistics
from collections import defaultdict
from typing import Any
import os

# Initialize Windows terminal for ANSI color support (no-op on Unix systems)
os.system("")

# Colors for terminal output
RESET = "\033[0m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"

# File paths
MATCHES_FILE = "./docs/data/matches/matches.csv"
ROUNDS_FILE = "./docs/data/matches/rounds.csv"
ELO_HISTORY_FILE = "./docs/data/elo/elo_history.csv"
ADVANCED_LEADERBOARD_FILE = "./docs/data/leaderboard/advanced_leaderboard.csv"
BEYS_DATA_FILE = "./docs/data/beys/beys_data.json"
RPG_STATS_JSON = "./docs/data/analytics/rpg_stats.json"
RPG_STATS_CSV = "./docs/data/analytics/rpg_stats.csv"

# Minimum matches against an opponent type to use the real win rate.
# Below this threshold the neutral value (0.5) is imputed.
TYPE_VERSATILITY_MIN_MATCHES = 2
TYPE_VERSATILITY_NEUTRAL = 0.5

# Minimum matches threshold to compute reliable stats
# Set to 1 to include all beys in the leaderboard even with limited data
# Consider increasing to 3-5 for larger datasets with more statistical significance
MIN_MATCHES_FOR_STATS = 1


# ============================================
# STAT WEIGHTS
# ============================================

ATTACK_WEIGHTS = {
    "aggressive_finish_rate": 0.50,  # Combined KO finish rate (burst+pocket+stadium_exit+extreme) / rounds_won
    "offensive_point_efficiency": 0.30,  # Average points per round won
    "opening_dominance": 0.20,  # First-round win rate
}

DEFENSE_WEIGHTS = {
    "impact_resistance": 0.50,   # Aggregated KO resistance (burst+pocket+stadium_exit+extreme)
    "defensive_conversion": 0.30,  # Comeback win rate after losing a round
    "round_survival_rate": 0.20,  # Proportion of rounds NOT lost
}

# Non-linear scaling exponent applied to all stat calculations.
# alpha < 1 compresses the low end and stretches the upper range so that
# exceptional beys realistically reach 20–25 total points (5 stats × 0–5).
STAT_SCALE_ALPHA = 0.65

STAMINA_WEIGHTS = {
    "spin_finish_win_rate": 0.50,
    "spin_differential_index": 0.30,
    "long_round_win_rate": 0.20,
}

CONTROL_WEIGHTS = {
    "volatility_inverse": 0.30,
    "first_contact_advantage": 0.30,
    "type_versatility": 0.40,  # Cross-type win rate consistency (pre-set bey types)
}

META_IMPACT_WEIGHTS = {
    "elo_normalized": 0.30,
    "elo_per_match": 0.15,
    "upset_rate": 0.20,
    "matchup_spread": 0.15,
    "anti_meta_score": 0.20,
}


# ============================================
# ARCHETYPE DEFINITIONS
# ============================================

ARCHETYPE_DEFINITIONS = {
    # Offense-focused archetypes
    "glass_cannon": {
        "name": "Glass Cannon",
        "description": "Very high Attack, low Defense & low Burst Resistance",
        "category": "offense",
        "icon": "💥",
        "color": "#ef4444",  # Red
    },
    "berserker": {
        "name": "Berserker",
        "description": "High Attack + high volatility, KO-heavy style",
        "category": "offense",
        "icon": "⚔️",
        "color": "#dc2626",  # Dark red
    },
    "chaser": {
        "name": "Chaser",
        "description": "Fast, Pocket/Extreme-focused finish bias",
        "category": "offense",
        "icon": "🎯",
        "color": "#f97316",  # Orange
    },
    # Defense-focused archetypes
    "iron_wall": {
        "name": "Iron Wall",
        "description": "Extremely high Defense, high Burst Resistance, low volatility",
        "category": "defense",
        "icon": "🛡️",
        "color": "#3b82f6",  # Blue
    },
    "counter_shield": {
        "name": "Counter Shield",
        "description": "Defensive tendencies but with strong reversal potential",
        "category": "defense",
        "icon": "🔄",
        "color": "#6366f1",  # Indigo
    },
    # Stamina-focused archetypes
    "endurance_core": {
        "name": "Endurance Core",
        "description": "Stable, low volatility, high Spin Finish bias",
        "category": "stamina",
        "icon": "💪",
        "color": "#10b981",  # Teal/Emerald
    },
    "spin_tank": {
        "name": "Spin Tank",
        "description": "High stamina + high defense, wins long rounds consistently",
        "category": "stamina",
        "icon": "🔋",
        "color": "#14b8a6",  # Teal
    },
    # Balance/Control archetypes
    "tempo_controller": {
        "name": "Tempo Controller",
        "description": "High Control, stable flow, consistency-focused",
        "category": "control",
        "icon": "🎼",
        "color": "#f59e0b",  # Amber
    },
    "adaptive_fighter": {
        "name": "Adaptive Fighter",
        "description": "Moderate in all stats, excels in matchup spread",
        "category": "balance",
        "icon": "⚡",
        "color": "#8b5cf6",  # Violet
    },
    "meta_anchor": {
        "name": "Meta Anchor",
        "description": "Above-average Meta Impact despite mixed stat profile",
        "category": "balance",
        "icon": "⭐",
        "color": "#eab308",  # Yellow
    },
    # Fallback
    "unknown": {
        "name": "Unknown",
        "description": "Insufficient data or no clear archetype match",
        "category": "unknown",
        "icon": "❓",
        "color": "#6b7280",  # Gray
    },
}

# Minimum matches required for reliable archetype classification
MIN_MATCHES_FOR_ARCHETYPE = 3

# Archetype confidence calculation constants
# Max stat balance divisor: 3 stat differences × 5.0 max stat value
MAX_STAT_BALANCE_DIVISOR = 15.0
# Confidence score weights: base score weight and gap multiplier
CONFIDENCE_BASE_WEIGHT = 0.6
CONFIDENCE_GAP_MULTIPLIER = 2.0

# Archetype threshold constants
# Glass Cannon thresholds
GLASS_CANNON_MIN_ATTACK = 3.0
GLASS_CANNON_MAX_DEFENSE = 3.0

# Berserker thresholds
BERSERKER_MIN_ATTACK = 3.0
BERSERKER_MAX_VOLATILITY_INVERSE = 0.6

# Chaser thresholds
CHASER_MIN_ATTACK = 2.5
CHASER_MIN_POCKET_FINISH = 0.15
CHASER_MIN_EXTREME_FINISH = 0.15

# Iron Wall thresholds
IRON_WALL_MIN_DEFENSE = 2.5
IRON_WALL_MIN_IMPACT_RESISTANCE = 0.40  # Minimum impact_resistance: at least 40% of losses must be non-KO (spin)
IRON_WALL_MAX_ATTACK = 3.5
IRON_WALL_MAX_STAMINA = 3.5

# Counter Shield thresholds
COUNTER_SHIELD_MIN_DEFENSE = 2.3
COUNTER_SHIELD_MIN_DEFENSIVE_CONVERSION = 0.5
COUNTER_SHIELD_MAX_STAMINA = 3.5

# Endurance Core thresholds
ENDURANCE_CORE_MIN_STAMINA = 3.0
ENDURANCE_CORE_MIN_SPIN_FINISH_WIN_RATE = 0.3
ENDURANCE_CORE_MAX_DEFENSE = 3.0

# Spin Tank thresholds
SPIN_TANK_MIN_STAMINA = 2.8
SPIN_TANK_MIN_DEFENSE = 2.5

# Tempo Controller thresholds
TEMPO_CONTROLLER_MIN_CONTROL = 3.0

# Adaptive Fighter thresholds
ADAPTIVE_FIGHTER_MIN_STAT = 2.0
ADAPTIVE_FIGHTER_MAX_STAT = 4.0
ADAPTIVE_FIGHTER_MIN_STAT_BALANCE = 0.6

# Meta Anchor thresholds
META_ANCHOR_MIN_META_IMPACT = 3.0


def detect_archetype(
    stats: dict[str, float],
    sub_metrics: dict[str, dict[str, float]],
    leaderboard_data: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Detect the archetype of a Beyblade based on its statistical profile.

    Uses weighted scoring based on stat values and sub-metric patterns to
    classify a Bey into one of the defined archetypes.

    Args:
        stats: Dictionary of stat values (attack, defense, stamina, control, meta_impact)
        sub_metrics: Dictionary of sub-metrics for each stat category
        leaderboard_data: Optional leaderboard data for additional context

    Returns:
        Dictionary containing:
        - archetype: string key of the detected archetype
        - archetype_data: full archetype definition
        - confidence: confidence score (0.0-1.0)
        - candidates: list of candidate archetypes with scores
    """
    # Check for minimum data requirements
    matches = leaderboard_data.get("matches", 0) if leaderboard_data else 0
    if matches < MIN_MATCHES_FOR_ARCHETYPE:
        return {
            "archetype": "unknown",
            "archetype_data": ARCHETYPE_DEFINITIONS["unknown"],
            "confidence": 0.0,
            "candidates": [],
            "reason": "Insufficient match data",
        }

    # Extract stat values
    attack = stats.get("attack", 2.5)
    defense = stats.get("defense", 2.5)
    stamina = stats.get("stamina", 2.5)
    control = stats.get("control", 2.5)
    meta_impact = stats.get("meta_impact", 2.5)

    # Extract key sub-metrics
    attack_metrics = sub_metrics.get("attack", {})
    defense_metrics = sub_metrics.get("defense", {})
    stamina_metrics = sub_metrics.get("stamina", {})
    control_metrics = sub_metrics.get("control", {})
    meta_metrics = sub_metrics.get("meta_impact", {})

    burst_finish_rate = attack_metrics.get("burst_finish_rate", 0)
    pocket_finish_rate = attack_metrics.get("pocket_finish_rate", 0)
    stadium_exit_finish_rate = attack_metrics.get("stadium_exit_finish_rate", 0)
    extreme_finish_rate = attack_metrics.get("extreme_finish_rate", 0)
    impact_resistance = defense_metrics.get("impact_resistance", 0.5)
    defensive_conversion = defense_metrics.get("defensive_conversion", 0.5)
    spin_finish_win_rate = stamina_metrics.get("spin_finish_win_rate", 0)
    volatility_inverse = control_metrics.get("volatility_inverse", 0.5)
    matchup_spread = meta_metrics.get("matchup_spread", 0.5)
    anti_meta_score = meta_metrics.get("anti_meta_score", 0.5)

    # Calculate archetype scores
    archetype_scores: dict[str, float] = {}

    # Glass Cannon: High attack, low defense & low impact resistance
    # Require: attack > threshold, defense < threshold
    if attack > GLASS_CANNON_MIN_ATTACK and defense < GLASS_CANNON_MAX_DEFENSE:
        archetype_scores["glass_cannon"] = (
            (attack / 5.0) * 0.5
            + ((5.0 - defense) / 5.0) * 0.35
            + ((1.0 - impact_resistance) * 0.15)
        )
    else:
        archetype_scores["glass_cannon"] = 0.0

    # Berserker: High attack + high volatility (low control)
    # Require: attack > threshold, volatility_inverse < threshold
    if attack > BERSERKER_MIN_ATTACK and volatility_inverse < BERSERKER_MAX_VOLATILITY_INVERSE:
        archetype_scores["berserker"] = (
            (attack / 5.0) * 0.4
            + (burst_finish_rate * 0.35)
            + ((1.0 - volatility_inverse) * 0.25)
        )
    else:
        archetype_scores["berserker"] = 0.0

    # Chaser: Fast finisher, pocket/extreme/stadium_exit focused
    # Require: attack > threshold AND (pocket_finish OR extreme_finish OR stadium_exit_finish > threshold)
    if (attack > CHASER_MIN_ATTACK and
            (pocket_finish_rate > CHASER_MIN_POCKET_FINISH or
             stadium_exit_finish_rate > CHASER_MIN_POCKET_FINISH or  # Use same threshold as pocket
             extreme_finish_rate > CHASER_MIN_EXTREME_FINISH)):
        archetype_scores["chaser"] = (
            (attack / 5.0) * 0.25
            + (pocket_finish_rate * 0.35)
            + (stadium_exit_finish_rate * 0.10)  # Lower weight due to rarity
            + (extreme_finish_rate * 0.30)
        )
    else:
        archetype_scores["chaser"] = 0.0

    # Iron Wall: High defense, high impact resistance, low volatility
    # Require: defense, impact_resistance above threshold, attack and stamina below threshold
    if (defense > IRON_WALL_MIN_DEFENSE and
            impact_resistance > IRON_WALL_MIN_IMPACT_RESISTANCE and
            attack < IRON_WALL_MAX_ATTACK and
            stamina < IRON_WALL_MAX_STAMINA):
        archetype_scores["iron_wall"] = (
            (defense / 5.0) * 0.45
            + (impact_resistance * 0.35)
            + (volatility_inverse * 0.20)
        )
    else:
        archetype_scores["iron_wall"] = 0.0

    # Counter Shield: Defensive but with reversal potential
    # Require: defense, defensive_conversion above threshold, stamina below threshold
    if (defense > COUNTER_SHIELD_MIN_DEFENSE and
            defensive_conversion > COUNTER_SHIELD_MIN_DEFENSIVE_CONVERSION and
            stamina < COUNTER_SHIELD_MAX_STAMINA):
        archetype_scores["counter_shield"] = (
            (defense / 5.0) * 0.35
            + (defensive_conversion * 0.45)
            + (impact_resistance * 0.20)
        )
    else:
        archetype_scores["counter_shield"] = 0.0

    # Endurance Core: High stamina, stable, spin finish focused
    # Require: stamina, spin_finish_win_rate above threshold, defense below threshold
    if (stamina > ENDURANCE_CORE_MIN_STAMINA and
            spin_finish_win_rate > ENDURANCE_CORE_MIN_SPIN_FINISH_WIN_RATE and
            defense < ENDURANCE_CORE_MAX_DEFENSE):
        archetype_scores["endurance_core"] = (
            (stamina / 5.0) * 0.45
            + (spin_finish_win_rate * 0.35)
            + (volatility_inverse * 0.20)
        )
    else:
        archetype_scores["endurance_core"] = 0.0

    # Spin Tank: High stamina + high defense, long match winner
    # Require: stamina and defense above threshold (prioritize dual high stats)
    if stamina > SPIN_TANK_MIN_STAMINA and defense > SPIN_TANK_MIN_DEFENSE:
        archetype_scores["spin_tank"] = (
            (stamina / 5.0) * 0.45
            + (defense / 5.0) * 0.35
            + (stamina_metrics.get("long_round_win_rate", 0.5) * 0.20)
        )
    else:
        archetype_scores["spin_tank"] = 0.0

    # Tempo Controller: High control, stable performance
    # Require: control > threshold
    if control > TEMPO_CONTROLLER_MIN_CONTROL:
        archetype_scores["tempo_controller"] = (
            (control / 5.0) * 0.55
            + (volatility_inverse * 0.25)
            + (control_metrics.get("first_contact_advantage", 0.5) * 0.20)
        )
    else:
        archetype_scores["tempo_controller"] = 0.0

    # Adaptive Fighter: Balanced stats, good matchup spread
    # Require: all main stats in range, no stat dominates
    stat_balance = 1.0 - (
        abs(attack - defense) + abs(defense - stamina) + abs(stamina - control)
    ) / MAX_STAT_BALANCE_DIVISOR
    min_stat = min(attack, defense, stamina, control)
    max_stat = max(attack, defense, stamina, control)
    is_balanced = (min_stat >= ADAPTIVE_FIGHTER_MIN_STAT and
                   max_stat <= ADAPTIVE_FIGHTER_MAX_STAT and
                   stat_balance > ADAPTIVE_FIGHTER_MIN_STAT_BALANCE)

    if is_balanced:
        archetype_scores["adaptive_fighter"] = (
            stat_balance * 0.5
            + (matchup_spread * 0.3)
            + (min_stat / 5.0) * 0.20
        )
    else:
        archetype_scores["adaptive_fighter"] = 0.0

    # Meta Anchor: High meta impact despite balanced/mixed profile
    # Require: meta_impact > threshold
    if meta_impact > META_ANCHOR_MIN_META_IMPACT:
        archetype_scores["meta_anchor"] = (
            (meta_impact / 5.0) * 0.55
            + (anti_meta_score * 0.25)
            + (matchup_spread * 0.20)
        )
    else:
        archetype_scores["meta_anchor"] = 0.0

    # Find top candidates
    sorted_archetypes = sorted(
        archetype_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    top_archetype = sorted_archetypes[0][0]
    top_score = sorted_archetypes[0][1]

    # If no archetype has a score > 0, return unknown
    if top_score == 0.0:
        return {
            "archetype": "unknown",
            "archetype_data": ARCHETYPE_DEFINITIONS["unknown"],
            "confidence": 0.0,
            "candidates": [],
            "reason": "No archetype criteria met",
        }

    # Calculate confidence based on score gap
    # Confidence formula combines base score contribution with gap bonus
    if len(sorted_archetypes) > 1:
        score_gap = top_score - sorted_archetypes[1][1]
        confidence = min(
            1.0,
            top_score * CONFIDENCE_BASE_WEIGHT + score_gap * CONFIDENCE_GAP_MULTIPLIER
        )
    else:
        confidence = top_score

    # Prepare candidates list (top 3)
    candidates = [
        {
            "archetype": arch,
            "score": round(score, 3),
            "name": ARCHETYPE_DEFINITIONS[arch]["name"],
        }
        for arch, score in sorted_archetypes[:3]
    ]

    return {
        "archetype": top_archetype,
        "archetype_data": ARCHETYPE_DEFINITIONS[top_archetype],
        "confidence": round(confidence, 3),
        "candidates": candidates,
    }


# ============================================
# NORMALIZATION FUNCTIONS
# ============================================

def percentile_normalize(value: float, all_values: list[float]) -> float:
    """
    Normalize a value using percentile ranking within the dataset.

    Returns a value between 0.0 and 1.0 representing the percentile.

    Args:
        value: The value to normalize
        all_values: All values in the dataset for comparison

    Returns:
        float: Normalized value between 0.0 and 1.0
    """
    if not all_values or len(all_values) == 0:
        return 0.5

    sorted_values = sorted(all_values)
    n = len(sorted_values)

    if n == 1:
        return 0.5

    # Count how many values are less than the given value
    count_below = sum(1 for v in sorted_values if v < value)

    # Percentile = (count below) / (n - 1)
    return count_below / (n - 1) if n > 1 else 0.5


def minmax_normalize(value: float, min_val: float, max_val: float) -> float:
    """
    Normalize a value using min-max scaling.

    Args:
        value: The value to normalize
        min_val: Minimum value in range
        max_val: Maximum value in range

    Returns:
        float: Normalized value between 0.0 and 1.0
    """
    if max_val == min_val:
        return 0.5
    return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))


def clamp(value: float, min_val: float = 0.0, max_val: float = 5.0) -> float:
    """Clamp a value to a specified range."""
    return max(min_val, min(max_val, value))


# ============================================
# DATA COLLECTION FUNCTIONS
# ============================================

def load_matches() -> list[dict[str, Any]]:
    """Load match data from CSV file."""
    matches = []
    with open(MATCHES_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            matches.append({
                "match_id": row["MatchID"],
                "date": row["Date"],
                "bey_a": row["BeyA"],
                "bey_b": row["BeyB"],
                "score_a": int(row["ScoreA"]),
                "score_b": int(row["ScoreB"]),
            })
    return matches


def load_rounds() -> list[dict[str, Any]]:
    """Load round data from CSV file."""
    rounds = []
    with open(ROUNDS_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rounds.append({
                "match_id": row["match_id"],
                "round_number": int(row["round_number"]),
                "winner": row["winner"],
                "finish_type": row["finish_type"].strip().lower(),
                "points_awarded": int(row["points_awarded"]),
            })
    return rounds


def load_elo_history() -> list[dict[str, Any]]:
    """Load ELO history from CSV file."""
    history = []
    with open(ELO_HISTORY_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            history.append({
                "match_id": row["MatchID"],
                "date": row["Date"],
                "bey_a": row["BeyA"],
                "bey_b": row["BeyB"],
                "score_a": int(row["ScoreA"]),
                "score_b": int(row["ScoreB"]),
                "pre_a": float(row["PreA"]),
                "pre_b": float(row["PreB"]),
                "post_a": float(row["PostA"]),
                "post_b": float(row["PostB"]),
            })
    return history


def load_advanced_leaderboard() -> dict[str, dict[str, Any]]:
    """Load advanced leaderboard data."""
    leaderboard = {}
    with open(ADVANCED_LEADERBOARD_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            leaderboard[row["Bey"]] = {
                "rank": int(row["Platz"]),
                "elo": int(row["ELO"]),
                "power_index": float(row["PowerIndex"]),
                "matches": int(row["Matches"]),
                "wins": int(row["Wins"]),
                "losses": int(row["Losses"]),
                "winrate": float(row["Winrate"].rstrip("%")) / 100,
                "volatility": float(row["Volatility"]),
                "elo_trend": float(row["ELOTrend"]),
                "upset_wins": int(row["UpsetWins"]),
                "upset_losses": int(row["UpsetLosses"]),
            }
    return leaderboard


def load_bey_types(beys_data_path: str = BEYS_DATA_FILE) -> dict[str, str]:
    """
    Load pre-set bey types from beys_data.json.

    Each Beyblade is assigned a type (Attack / Defense / Stamina / Balance)
    based on its parts design.  This classification is static and does not
    depend on match results.

    Returns:
        Dictionary mapping blade name → type string, e.g. {"ImpactDrake": "Attack"}.
        Returns an empty dict if the file cannot be read.
    """
    try:
        with open(beys_data_path, encoding="utf-8") as f:
            data = json.load(f)
        return {entry["blade"]: entry["type"] for entry in data}
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return {}


# ============================================
# SUB-METRIC CALCULATION FUNCTIONS
# ============================================

def calculate_type_matchup_stats(
    matches: list,
    bey_types: dict[str, str],
    all_beys: list[str]
) -> dict[str, dict]:
    """
    Calculate per-bey win/loss records broken down by pre-set opponent type.

    For each bey and each of the four standard types (Attack, Defense, Stamina,
    Balance) this returns the number of matches played against that type and the
    number of those matches won.  The results feed the ``type_versatility``
    sub-metric used in the Control stat calculation.

    Args:
        matches: List of match dicts as returned by load_matches().
        bey_types: Dict mapping blade name → type string (from load_bey_types()).
        all_beys: List of all bey names to include in the output.

    Returns:
        Dict mapping bey name → stats dict with keys:
        ``wins_vs_Attack``, ``matches_vs_Attack``, … (one pair per type).
    """
    _TYPES = ("Attack", "Defense", "Stamina", "Balance")
    stats: dict[str, dict] = {
        bey: {
            f"wins_vs_{t}": 0
            for t in _TYPES
        } | {
            f"matches_vs_{t}": 0
            for t in _TYPES
        }
        for bey in all_beys
    }

    for m in matches:
        a = m["bey_a"]
        b = m["bey_b"]
        sa = m["score_a"]
        sb = m["score_b"]
        type_a = bey_types.get(a)
        type_b = bey_types.get(b)

        if a in stats and type_b in _TYPES:
            stats[a][f"matches_vs_{type_b}"] += 1
            if sa > sb:
                stats[a][f"wins_vs_{type_b}"] += 1

        if b in stats and type_a in _TYPES:
            stats[b][f"matches_vs_{type_a}"] += 1
            if sb > sa:
                stats[b][f"wins_vs_{type_a}"] += 1

    return stats


def calculate_bey_round_stats(matches: list, rounds: list) -> dict[str, dict]:
    """
    Calculate round-level statistics for each Beyblade.

    Returns a dictionary mapping bey names to their round statistics.
    """
    # Create a mapping of match_id to match data
    match_map = {}
    for m in matches:
        match_map[m["match_id"]] = m

    # Initialize stats for each bey
    bey_stats: dict[str, dict] = defaultdict(lambda: {
        "rounds_won": 0,
        "rounds_lost": 0,
        "burst_wins": 0,
        "pocket_wins": 0,
        "stadium_exit_wins": 0,
        "extreme_wins": 0,
        "spin_wins": 0,
        "burst_losses": 0,
        "pocket_losses": 0,
        "stadium_exit_losses": 0,
        "extreme_losses": 0,
        "spin_losses": 0,
        "points_from_wins": 0,
        "points_against": 0,
        "matches_won_first_round": 0,
        "total_matches": 0,
        "first_round_wins": 0,
        "match_round_counts": [],  # List of round counts per match
        "long_rounds_won": 0,  # Rounds won in matches with 5+ rounds
        "long_rounds_played": 0,  # Total rounds played in long matches
        "opponents": set(),  # Set of unique opponents
        "comeback_wins": 0,  # Wins after losing the previous round
        "lost_previous_round": 0,  # Times bey lost a round
    })

    # Group rounds by match
    rounds_by_match: dict[str, list] = defaultdict(list)
    for r in rounds:
        rounds_by_match[r["match_id"]].append(r)

    # Process each match
    for match_id, match_rounds in rounds_by_match.items():
        if match_id not in match_map:
            continue

        match = match_map[match_id]
        bey_a = match["bey_a"]
        bey_b = match["bey_b"]
        score_a = match["score_a"]
        score_b = match["score_b"]

        # Track opponents
        bey_stats[bey_a]["opponents"].add(bey_b)
        bey_stats[bey_b]["opponents"].add(bey_a)
        bey_stats[bey_a]["total_matches"] += 1
        bey_stats[bey_b]["total_matches"] += 1

        # Track rounds per match
        num_rounds = len(match_rounds)
        bey_stats[bey_a]["match_round_counts"].append(num_rounds)
        bey_stats[bey_b]["match_round_counts"].append(num_rounds)

        is_long_match = num_rounds >= 5

        # Sort rounds by round number
        sorted_rounds = sorted(match_rounds, key=lambda r: r["round_number"])

        # Track first round winner
        if sorted_rounds:
            first_round_winner = sorted_rounds[0]["winner"]
            bey_stats[first_round_winner]["first_round_wins"] += 1

            # Check if first round winner won the match
            match_winner = bey_a if score_a > score_b else bey_b
            if first_round_winner == match_winner:
                bey_stats[first_round_winner]["matches_won_first_round"] += 1

        # Track comebacks (win after losing previous round)
        previous_loser = None
        for rnd in sorted_rounds:
            winner = rnd["winner"]
            loser = bey_a if winner == bey_b else bey_b

            if previous_loser is not None and previous_loser == winner:
                bey_stats[winner]["comeback_wins"] += 1

            bey_stats[loser]["lost_previous_round"] += 1
            previous_loser = loser

        # Process each round
        for rnd in sorted_rounds:
            winner = rnd["winner"]
            loser = bey_a if winner == bey_b else bey_b
            finish_type = rnd["finish_type"]
            points = rnd["points_awarded"]

            # Update winner stats
            bey_stats[winner]["rounds_won"] += 1
            bey_stats[winner]["points_from_wins"] += points

            # Update loser stats
            bey_stats[loser]["rounds_lost"] += 1
            bey_stats[loser]["points_against"] += points

            # Track finish type wins
            if finish_type == "burst":
                bey_stats[winner]["burst_wins"] += 1
                bey_stats[loser]["burst_losses"] += 1
            elif finish_type == "pocket":
                bey_stats[winner]["pocket_wins"] += 1
                bey_stats[loser]["pocket_losses"] += 1
            elif finish_type == "stadium_exit":
                bey_stats[winner]["stadium_exit_wins"] += 1
                bey_stats[loser]["stadium_exit_losses"] += 1
            elif finish_type == "extreme":
                bey_stats[winner]["extreme_wins"] += 1
                bey_stats[loser]["extreme_losses"] += 1
            else:  # spin
                bey_stats[winner]["spin_wins"] += 1
                bey_stats[loser]["spin_losses"] += 1

            # Track long match performance
            if is_long_match:
                bey_stats[winner]["long_rounds_won"] += 1
                bey_stats[winner]["long_rounds_played"] += 1
                bey_stats[loser]["long_rounds_played"] += 1

    return dict(bey_stats)


def calculate_attack_metrics(bey_stats: dict, all_beys: list[str]) -> dict[str, dict]:
    """
    Calculate Attack sub-metrics for each Beyblade.

    Metrics:
    - aggressive_finish_rate: % of round wins that are any KO-type finish
      (burst + pocket + stadium_exit + extreme) / rounds_won. Aggregates all
      high-impact finishes into a single orthogonal signal so that a burst
      specialist is not penalised for having zero pocket/extreme rates.
    - offensive_point_efficiency: Average points per round won
    - opening_dominance: % of first rounds won

    Individual finish-type rates (burst, pocket, stadium_exit, extreme) are also
    stored in the returned dict so that downstream modules (matchup predictor,
    archetype detection) can still access them, but they are not used in the
    weighted attack stat calculation.
    """
    metrics: dict[str, dict] = {}

    for bey in all_beys:
        stats = bey_stats.get(bey, {})
        rounds_won = stats.get("rounds_won", 0)
        total_matches = stats.get("total_matches", 0)

        if rounds_won > 0:
            burst_rate = stats.get("burst_wins", 0) / rounds_won
            pocket_rate = stats.get("pocket_wins", 0) / rounds_won
            stadium_exit_rate = stats.get("stadium_exit_wins", 0) / rounds_won
            extreme_rate = stats.get("extreme_wins", 0) / rounds_won
            # Aggregate all KO-type finishes into one metric so that a bey
            # specialising in a single finish type is not penalised.
            aggressive_finish_rate = burst_rate + pocket_rate + stadium_exit_rate + extreme_rate
            point_efficiency = stats.get("points_from_wins", 0) / rounds_won
        else:
            burst_rate = 0.0
            pocket_rate = 0.0
            stadium_exit_rate = 0.0
            extreme_rate = 0.0
            aggressive_finish_rate = 0.0
            point_efficiency = 0.0

        if total_matches > 0:
            opening_dominance = stats.get("first_round_wins", 0) / total_matches
        else:
            opening_dominance = 0.0

        metrics[bey] = {
            "aggressive_finish_rate": aggressive_finish_rate,
            "offensive_point_efficiency": point_efficiency,
            "opening_dominance": opening_dominance,
            # Individual rates kept for archetype detection and matchup predictor
            "burst_finish_rate": burst_rate,
            "pocket_finish_rate": pocket_rate,
            "stadium_exit_finish_rate": stadium_exit_rate,
            "extreme_finish_rate": extreme_rate,
        }

    return metrics


def calculate_defense_metrics(bey_stats: dict, all_beys: list[str]) -> dict[str, dict]:
    """
    Calculate Defense sub-metrics for each Beyblade.

    Metrics:
    - impact_resistance: 1 - (all KO losses / total rounds lost). Aggregates
      burst, pocket, stadium_exit and extreme resistances into one orthogonal signal.
    - defensive_conversion: Win rate after losing a round (comeback ability)
    - round_survival_rate: 1 - (rounds_lost / total rounds played). Measures
      how often the bey avoids losing a round (frequency, not type).
    """
    metrics: dict[str, dict] = {}

    for bey in all_beys:
        stats = bey_stats.get(bey, {})
        rounds_won = stats.get("rounds_won", 0)
        rounds_lost = stats.get("rounds_lost", 0)

        if rounds_lost > 0:
            ko_losses = (
                stats.get("burst_losses", 0)
                + stats.get("pocket_losses", 0)
                + stats.get("stadium_exit_losses", 0)
                + stats.get("extreme_losses", 0)
            )
            impact_resistance = 1.0 - (ko_losses / rounds_lost)
        else:
            # No losses means perfect resistance
            impact_resistance = 1.0

        # Round survival rate: proportion of rounds NOT lost
        total_rounds = rounds_won + rounds_lost
        if total_rounds > 0:
            round_survival_rate = 1.0 - (rounds_lost / total_rounds)
        else:
            round_survival_rate = 0.5  # Neutral if no rounds played

        # Defensive conversion: ability to win the next round after losing one
        lost_previous = stats.get("lost_previous_round", 0)
        if lost_previous > 0:
            defensive_conversion = stats.get("comeback_wins", 0) / lost_previous
        else:
            defensive_conversion = 0.5  # Neutral if never lost a round

        metrics[bey] = {
            "impact_resistance": impact_resistance,
            "defensive_conversion": defensive_conversion,
            "round_survival_rate": round_survival_rate,
        }

    return metrics


def calculate_stamina_metrics(bey_stats: dict, all_beys: list[str]) -> dict[str, dict]:
    """
    Calculate Stamina sub-metrics for each Beyblade.

    Metrics:
    - spin_finish_win_rate: % of round wins that are spin finishes
    - spin_differential_index: Ratio of spin wins to spin losses
    - long_round_win_rate: Win rate in matches with 5+ rounds
    """
    metrics: dict[str, dict] = {}

    for bey in all_beys:
        stats = bey_stats.get(bey, {})
        rounds_won = stats.get("rounds_won", 0)
        spin_wins = stats.get("spin_wins", 0)
        spin_losses = stats.get("spin_losses", 0)

        if rounds_won > 0:
            spin_win_rate = spin_wins / rounds_won
        else:
            spin_win_rate = 0.0

        # Spin differential: ratio of spin wins to (spin wins + spin losses)
        total_spin = spin_wins + spin_losses
        if total_spin > 0:
            spin_differential = spin_wins / total_spin
        else:
            spin_differential = 0.5

        # Long match win rate
        long_played = stats.get("long_rounds_played", 0)
        if long_played > 0:
            long_win_rate = stats.get("long_rounds_won", 0) / long_played
        else:
            long_win_rate = 0.5  # Neutral if no long matches

        metrics[bey] = {
            "spin_finish_win_rate": spin_win_rate,
            "spin_differential_index": spin_differential,
            "long_round_win_rate": long_win_rate,
        }

    return metrics


def calculate_control_metrics(
    bey_stats: dict,
    advanced_lb: dict,
    type_matchup_stats: dict,
    all_beys: list[str]
) -> dict[str, dict]:
    """
    Calculate Control sub-metrics for each Beyblade.

    Metrics:
    - volatility_inverse: 1 - normalized volatility (higher = more consistent ELO)
    - first_contact_advantage: Match win rate when winning first round (closing ability)
    - type_versatility: Cross-type win rate quality, using pre-set bey types.
      Computed as mean_win_rate × (1 - stdev(win_rates)) across all four types
      (Attack, Defense, Stamina, Balance).  Types with fewer than
      TYPE_VERSATILITY_MIN_MATCHES matches are imputed with TYPE_VERSATILITY_NEUTRAL
      so that sparse beys fall back to a neutral mid-range score.
      High value → wins consistently against every type (true "control" behavior).
    """
    metrics: dict[str, dict] = {}

    # Collect all volatility values for normalization
    all_volatilities = [
        advanced_lb[bey]["volatility"]
        for bey in all_beys
        if bey in advanced_lb
    ]
    max_volatility = max(all_volatilities) if all_volatilities else 1.0

    for bey in all_beys:
        stats = bey_stats.get(bey, {})
        lb_data = advanced_lb.get(bey, {})

        # Volatility inverse (lower volatility = higher control)
        volatility = lb_data.get("volatility", 0.0)
        if max_volatility > 0:
            volatility_inverse = 1.0 - (volatility / max_volatility)
        else:
            volatility_inverse = 1.0

        # First contact advantage
        first_round_wins = stats.get("first_round_wins", 0)
        matches_won_first = stats.get("matches_won_first_round", 0)
        if first_round_wins > 0:
            first_contact_advantage = matches_won_first / first_round_wins
        else:
            first_contact_advantage = 0.5

        # Type versatility: how consistently the bey wins against all pre-set types.
        # For each type, compute win rate if enough matches exist, else impute neutral.
        bey_type_stats = type_matchup_stats.get(bey, {})
        type_rates = []
        for bey_type in ("Attack", "Defense", "Stamina", "Balance"):
            n = bey_type_stats.get(f"matches_vs_{bey_type}", 0)
            if n >= TYPE_VERSATILITY_MIN_MATCHES:
                w = bey_type_stats.get(f"wins_vs_{bey_type}", 0)
                type_rates.append(w / n)
            else:
                type_rates.append(TYPE_VERSATILITY_NEUTRAL)
        mean_type_rate = sum(type_rates) / 4
        std_type_rate = statistics.stdev(type_rates)
        type_versatility = mean_type_rate * (1.0 - std_type_rate)

        metrics[bey] = {
            "volatility_inverse": volatility_inverse,
            "first_contact_advantage": first_contact_advantage,
            "type_versatility": type_versatility,
        }

    return metrics


def calculate_meta_impact_metrics(
    bey_stats: dict,
    advanced_lb: dict,
    elo_history: list,
    all_beys: list[str]
) -> dict[str, dict]:
    """
    Calculate Meta Impact sub-metrics for each Beyblade.

    Metrics:
    - elo_normalized: Normalized ELO rating
    - elo_per_match: Rate of ELO gain per match
    - upset_rate: Frequency of wins against higher-ranked opponents
    - matchup_spread: Breadth of performance across different opponent types
    - anti_meta_score: Effectiveness against top 5 beyblades
    """
    metrics: dict[str, dict] = {}

    # Get top 5 beys by power index
    sorted_beys = sorted(
        [b for b in all_beys if b in advanced_lb],
        key=lambda b: advanced_lb[b].get("power_index", 0),
        reverse=True
    )
    top5_beys = set(sorted_beys[:5])

    # Collect ELO values for normalization
    all_elos = [advanced_lb[bey]["elo"] for bey in all_beys if bey in advanced_lb]
    min_elo = min(all_elos) if all_elos else 1000
    max_elo = max(all_elos) if all_elos else 1000

    # Calculate wins against top 5 for each bey
    wins_vs_top5: dict[str, int] = defaultdict(int)
    matches_vs_top5: dict[str, int] = defaultdict(int)

    for match in elo_history:
        bey_a = match["bey_a"]
        bey_b = match["bey_b"]
        score_a = match["score_a"]
        score_b = match["score_b"]

        # Check if playing against a top 5 bey
        if bey_b in top5_beys:
            matches_vs_top5[bey_a] += 1
            if score_a > score_b:
                wins_vs_top5[bey_a] += 1

        if bey_a in top5_beys:
            matches_vs_top5[bey_b] += 1
            if score_b > score_a:
                wins_vs_top5[bey_b] += 1

    for bey in all_beys:
        stats = bey_stats.get(bey, {})
        lb_data = advanced_lb.get(bey, {})

        # Normalized ELO
        elo = lb_data.get("elo", 1000)
        elo_normalized = minmax_normalize(elo, min_elo, max_elo)

        # ELO per match
        matches = lb_data.get("matches", 1)
        elo_trend = lb_data.get("elo_trend", 0)
        if matches > 0:
            elo_per_match = elo_trend / matches
        else:
            elo_per_match = 0.0

        # Upset rate
        wins = lb_data.get("wins", 0)
        upset_wins = lb_data.get("upset_wins", 0)
        if wins > 0:
            upset_rate = upset_wins / wins
        else:
            upset_rate = 0.0

        # Matchup spread (number of unique opponents / max possible)
        opponents = stats.get("opponents", set())
        total_beys = len(all_beys)
        if total_beys > 1:
            matchup_spread = len(opponents) / (total_beys - 1)
        else:
            matchup_spread = 0.0

        # Anti-meta score (win rate against top 5)
        matches_top5 = matches_vs_top5.get(bey, 0)
        if matches_top5 > 0:
            anti_meta_score = wins_vs_top5.get(bey, 0) / matches_top5
        else:
            anti_meta_score = 0.5  # Neutral if no matches vs top 5

        metrics[bey] = {
            "elo_normalized": elo_normalized,
            "elo_per_match": elo_per_match,
            "upset_rate": upset_rate,
            "matchup_spread": matchup_spread,
            "anti_meta_score": anti_meta_score,
        }

    return metrics


# ============================================
# STAT CALCULATION FUNCTIONS
# ============================================

def calculate_attack_stat(metrics: dict, all_metrics: list[dict]) -> float:
    """Calculate the Attack stat (0-5) from attack metrics."""
    # Collect all values for percentile normalization
    all_aggressive = [m["aggressive_finish_rate"] for m in all_metrics]
    all_efficiency = [m["offensive_point_efficiency"] for m in all_metrics]
    all_opening = [m["opening_dominance"] for m in all_metrics]

    # Normalize each metric
    norm_aggressive = percentile_normalize(metrics["aggressive_finish_rate"], all_aggressive)
    norm_efficiency = percentile_normalize(
        metrics["offensive_point_efficiency"], all_efficiency
    )
    norm_opening = percentile_normalize(metrics["opening_dominance"], all_opening)

    # Weighted combination
    raw_score = (
        ATTACK_WEIGHTS["aggressive_finish_rate"] * norm_aggressive
        + ATTACK_WEIGHTS["offensive_point_efficiency"] * norm_efficiency
        + ATTACK_WEIGHTS["opening_dominance"] * norm_opening
    )

    return clamp(5.0 * (raw_score ** STAT_SCALE_ALPHA))


def calculate_defense_stat(metrics: dict, all_metrics: list[dict]) -> float:
    """Calculate the Defense stat (0-5) from defense metrics."""
    all_impact = [m["impact_resistance"] for m in all_metrics]
    all_conversion = [m["defensive_conversion"] for m in all_metrics]
    all_survival = [m["round_survival_rate"] for m in all_metrics]

    norm_impact = percentile_normalize(metrics["impact_resistance"], all_impact)
    norm_conversion = percentile_normalize(
        metrics["defensive_conversion"], all_conversion
    )
    norm_survival = percentile_normalize(metrics["round_survival_rate"], all_survival)

    raw_score = (
        DEFENSE_WEIGHTS["impact_resistance"] * norm_impact
        + DEFENSE_WEIGHTS["defensive_conversion"] * norm_conversion
        + DEFENSE_WEIGHTS["round_survival_rate"] * norm_survival
    )

    return clamp(5.0 * (raw_score ** STAT_SCALE_ALPHA))


def calculate_stamina_stat(metrics: dict, all_metrics: list[dict]) -> float:
    """Calculate the Stamina stat (0-5) from stamina metrics."""
    all_spin_rate = [m["spin_finish_win_rate"] for m in all_metrics]
    all_spin_diff = [m["spin_differential_index"] for m in all_metrics]
    all_long_win = [m["long_round_win_rate"] for m in all_metrics]

    norm_spin_rate = percentile_normalize(
        metrics["spin_finish_win_rate"], all_spin_rate
    )
    norm_spin_diff = percentile_normalize(
        metrics["spin_differential_index"], all_spin_diff
    )
    norm_long = percentile_normalize(metrics["long_round_win_rate"], all_long_win)

    raw_score = (
        STAMINA_WEIGHTS["spin_finish_win_rate"] * norm_spin_rate
        + STAMINA_WEIGHTS["spin_differential_index"] * norm_spin_diff
        + STAMINA_WEIGHTS["long_round_win_rate"] * norm_long
    )

    return clamp(5.0 * (raw_score ** STAT_SCALE_ALPHA))


def calculate_control_stat(metrics: dict, all_metrics: list[dict]) -> float:
    """Calculate the Control stat (0-5) from control metrics."""
    all_vol_inv = [m["volatility_inverse"] for m in all_metrics]
    all_first = [m["first_contact_advantage"] for m in all_metrics]
    all_versatility = [m["type_versatility"] for m in all_metrics]

    norm_vol = percentile_normalize(metrics["volatility_inverse"], all_vol_inv)
    norm_first = percentile_normalize(metrics["first_contact_advantage"], all_first)
    norm_versatility = percentile_normalize(metrics["type_versatility"], all_versatility)

    raw_score = (
        CONTROL_WEIGHTS["volatility_inverse"] * norm_vol
        + CONTROL_WEIGHTS["first_contact_advantage"] * norm_first
        + CONTROL_WEIGHTS["type_versatility"] * norm_versatility
    )

    return clamp(5.0 * (raw_score ** STAT_SCALE_ALPHA))


def calculate_meta_impact_stat(metrics: dict, all_metrics: list[dict]) -> float:
    """Calculate the Meta Impact stat (0-5) from meta impact metrics."""
    all_elo = [m["elo_normalized"] for m in all_metrics]
    all_elo_pm = [m["elo_per_match"] for m in all_metrics]
    all_upset = [m["upset_rate"] for m in all_metrics]
    all_spread = [m["matchup_spread"] for m in all_metrics]
    all_anti = [m["anti_meta_score"] for m in all_metrics]

    norm_elo = percentile_normalize(metrics["elo_normalized"], all_elo)
    norm_elo_pm = percentile_normalize(metrics["elo_per_match"], all_elo_pm)
    norm_upset = percentile_normalize(metrics["upset_rate"], all_upset)
    norm_spread = percentile_normalize(metrics["matchup_spread"], all_spread)
    norm_anti = percentile_normalize(metrics["anti_meta_score"], all_anti)

    raw_score = (
        META_IMPACT_WEIGHTS["elo_normalized"] * norm_elo
        + META_IMPACT_WEIGHTS["elo_per_match"] * norm_elo_pm
        + META_IMPACT_WEIGHTS["upset_rate"] * norm_upset
        + META_IMPACT_WEIGHTS["matchup_spread"] * norm_spread
        + META_IMPACT_WEIGHTS["anti_meta_score"] * norm_anti
    )

    return clamp(5.0 * (raw_score ** STAT_SCALE_ALPHA))


# ============================================
# MAIN CALCULATION PIPELINE
# ============================================

def calculate_rpg_stats() -> dict[str, dict]:
    """
    Calculate all RPG stats for every Beyblade.

    Returns a dictionary mapping bey names to their stats and sub-metrics.
    """
    print(f"{CYAN}Loading data...{RESET}")

    # Load data
    matches = load_matches()
    rounds = load_rounds()
    elo_history = load_elo_history()
    advanced_lb = load_advanced_leaderboard()
    bey_types = load_bey_types()

    # Get all beys
    all_beys = list(advanced_lb.keys())

    print(f"{CYAN}Calculating round statistics for {len(all_beys)} beys...{RESET}")

    # Calculate round-level stats
    bey_round_stats = calculate_bey_round_stats(matches, rounds)

    # Calculate per-type matchup records (used for type_versatility in Control)
    type_matchup_stats = calculate_type_matchup_stats(matches, bey_types, all_beys)

    print(f"{CYAN}Calculating sub-metrics...{RESET}")

    # Calculate sub-metrics for each category
    attack_metrics = calculate_attack_metrics(bey_round_stats, all_beys)
    defense_metrics = calculate_defense_metrics(bey_round_stats, all_beys)
    stamina_metrics = calculate_stamina_metrics(bey_round_stats, all_beys)
    control_metrics = calculate_control_metrics(
        bey_round_stats, advanced_lb, type_matchup_stats, all_beys
    )
    meta_impact_metrics = calculate_meta_impact_metrics(
        bey_round_stats, advanced_lb, elo_history, all_beys
    )

    print(f"{CYAN}Calculating final stats...{RESET}")

    # Collect all metrics for normalization
    all_attack = [attack_metrics[bey] for bey in all_beys]
    all_defense = [defense_metrics[bey] for bey in all_beys]
    all_stamina = [stamina_metrics[bey] for bey in all_beys]
    all_control = [control_metrics[bey] for bey in all_beys]
    all_meta = [meta_impact_metrics[bey] for bey in all_beys]

    # Calculate final stats for each bey
    results: dict[str, dict] = {}

    for bey in all_beys:
        lb_data = advanced_lb.get(bey, {})

        # Skip beys with too few matches for reliable stats
        if lb_data.get("matches", 0) < MIN_MATCHES_FOR_STATS:
            continue

        # Calculate final stats
        attack = calculate_attack_stat(attack_metrics[bey], all_attack)
        defense = calculate_defense_stat(defense_metrics[bey], all_defense)
        stamina = calculate_stamina_stat(stamina_metrics[bey], all_stamina)
        control = calculate_control_stat(control_metrics[bey], all_control)
        meta_impact = calculate_meta_impact_stat(meta_impact_metrics[bey], all_meta)

        # Build stats and sub_metrics dictionaries
        stats_dict = {
            "attack": round(attack, 2),
            "defense": round(defense, 2),
            "stamina": round(stamina, 2),
            "control": round(control, 2),
            "meta_impact": round(meta_impact, 2),
        }

        sub_metrics_dict = {
            "attack": {
                k: round(v, 4) for k, v in attack_metrics[bey].items()
            },
            "defense": {
                k: round(v, 4) for k, v in defense_metrics[bey].items()
            },
            "stamina": {
                k: round(v, 4) for k, v in stamina_metrics[bey].items()
            },
            "control": {
                k: round(v, 4) for k, v in control_metrics[bey].items()
            },
            "meta_impact": {
                k: round(v, 4) for k, v in meta_impact_metrics[bey].items()
            },
        }

        leaderboard_dict = {
            "rank": lb_data.get("rank", 0),
            "elo": lb_data.get("elo", 1000),
            "matches": lb_data.get("matches", 0),
        }

        # Detect archetype
        archetype_result = detect_archetype(
            stats_dict,
            sub_metrics_dict,
            leaderboard_dict
        )

        results[bey] = {
            "stats": stats_dict,
            "sub_metrics": sub_metrics_dict,
            "leaderboard": leaderboard_dict,
            "archetype": {
                "id": archetype_result["archetype"],
                "name": archetype_result["archetype_data"]["name"],
                "description": archetype_result["archetype_data"]["description"],
                "category": archetype_result["archetype_data"]["category"],
                "icon": archetype_result["archetype_data"]["icon"],
                "color": archetype_result["archetype_data"]["color"],
                "confidence": archetype_result["confidence"],
                "candidates": archetype_result["candidates"],
            },
        }

    print(f"{CYAN}Detecting archetypes...{RESET}")

    return results


def save_rpg_stats(stats: dict[str, dict]) -> None:
    """Save RPG stats to JSON and CSV files."""
    # Save JSON
    with open(RPG_STATS_JSON, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"{GREEN}RPG stats saved to {RPG_STATS_JSON}{RESET}")

    # Save CSV for easy viewing
    header = [
        "Bey", "Rank", "ELO", "Attack", "Defense", "Stamina", "Control", "Meta",
        "Archetype", "Archetype_Category", "Archetype_Confidence"
    ]
    with open(RPG_STATS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        # Sort by rank
        sorted_beys = sorted(
            stats.items(),
            key=lambda x: x[1]["leaderboard"]["rank"]
        )

        for bey, data in sorted_beys:
            archetype_data = data.get("archetype", {})
            writer.writerow([
                bey,
                data["leaderboard"]["rank"],
                data["leaderboard"]["elo"],
                data["stats"]["attack"],
                data["stats"]["defense"],
                data["stats"]["stamina"],
                data["stats"]["control"],
                data["stats"]["meta_impact"],
                archetype_data.get("name", "Unknown"),
                archetype_data.get("category", "unknown"),
                archetype_data.get("confidence", 0.0),
            ])

    print(f"{GREEN}RPG stats CSV saved to {RPG_STATS_CSV}{RESET}")


# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == "__main__":
    print(f"{CYAN}=== RPG Stats Calculator ==={RESET}")
    stats = calculate_rpg_stats()
    save_rpg_stats(stats)
    print(f"{GREEN}=== Done! ==={RESET}")
