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

os.system("")

# Colors for terminal output
RESET = "\033[0m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"

# File paths
MATCHES_FILE = "./csv/matches.csv"
ROUNDS_FILE = "./csv/rounds.csv"
ELO_HISTORY_FILE = "./csv/elo_history.csv"
ADVANCED_LEADERBOARD_FILE = "./csv/advanced_leaderboard.csv"
RPG_STATS_JSON = "./csv/rpg_stats.json"
RPG_STATS_CSV = "./csv/rpg_stats.csv"
DOCS_RPG_STATS_JSON = "./docs/data/rpg_stats.json"

# Minimum matches threshold to compute reliable stats
MIN_MATCHES_FOR_STATS = 1


# ============================================
# STAT WEIGHTS
# ============================================

ATTACK_WEIGHTS = {
    "burst_finish_rate": 0.30,
    "pocket_finish_rate": 0.15,
    "extreme_finish_rate": 0.20,
    "offensive_point_efficiency": 0.25,
    "opening_dominance": 0.10,
}

DEFENSE_WEIGHTS = {
    "burst_resistance": 0.35,
    "pocket_resistance": 0.25,
    "extreme_resistance": 0.25,
    "defensive_conversion": 0.15,
}

STAMINA_WEIGHTS = {
    "spin_finish_win_rate": 0.50,
    "spin_differential_index": 0.30,
    "long_round_win_rate": 0.20,
}

CONTROL_WEIGHTS = {
    "volatility_inverse": 0.35,
    "first_contact_advantage": 0.35,
    "match_flow_stability": 0.30,
}

META_IMPACT_WEIGHTS = {
    "elo_normalized": 0.30,
    "elo_per_match": 0.15,
    "upset_rate": 0.20,
    "matchup_spread": 0.15,
    "anti_meta_score": 0.20,
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


# ============================================
# SUB-METRIC CALCULATION FUNCTIONS
# ============================================

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
        "extreme_wins": 0,
        "spin_wins": 0,
        "burst_losses": 0,
        "pocket_losses": 0,
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
    - burst_finish_rate: % of round wins that are burst finishes
    - pocket_finish_rate: % of round wins that are pocket finishes
    - extreme_finish_rate: % of round wins that are extreme finishes
    - offensive_point_efficiency: Average points per round won
    - opening_dominance: % of first rounds won
    """
    metrics: dict[str, dict] = {}

    for bey in all_beys:
        stats = bey_stats.get(bey, {})
        rounds_won = stats.get("rounds_won", 0)
        total_matches = stats.get("total_matches", 0)

        if rounds_won > 0:
            burst_rate = stats.get("burst_wins", 0) / rounds_won
            pocket_rate = stats.get("pocket_wins", 0) / rounds_won
            extreme_rate = stats.get("extreme_wins", 0) / rounds_won
            point_efficiency = stats.get("points_from_wins", 0) / rounds_won
        else:
            burst_rate = 0.0
            pocket_rate = 0.0
            extreme_rate = 0.0
            point_efficiency = 0.0

        if total_matches > 0:
            opening_dominance = stats.get("first_round_wins", 0) / total_matches
        else:
            opening_dominance = 0.0

        metrics[bey] = {
            "burst_finish_rate": burst_rate,
            "pocket_finish_rate": pocket_rate,
            "extreme_finish_rate": extreme_rate,
            "offensive_point_efficiency": point_efficiency,
            "opening_dominance": opening_dominance,
        }

    return metrics


def calculate_defense_metrics(bey_stats: dict, all_beys: list[str]) -> dict[str, dict]:
    """
    Calculate Defense sub-metrics for each Beyblade.

    Metrics:
    - burst_resistance: 1 - (burst losses / total rounds lost)
    - pocket_resistance: 1 - (pocket losses / total rounds lost)
    - extreme_resistance: 1 - (extreme losses / total rounds lost)
    - defensive_conversion: Win rate after losing a round
    """
    metrics: dict[str, dict] = {}

    for bey in all_beys:
        stats = bey_stats.get(bey, {})
        rounds_lost = stats.get("rounds_lost", 0)

        if rounds_lost > 0:
            burst_resistance = 1.0 - (stats.get("burst_losses", 0) / rounds_lost)
            pocket_resistance = 1.0 - (stats.get("pocket_losses", 0) / rounds_lost)
            extreme_resistance = 1.0 - (stats.get("extreme_losses", 0) / rounds_lost)
        else:
            # No losses means perfect resistance
            burst_resistance = 1.0
            pocket_resistance = 1.0
            extreme_resistance = 1.0

        # Defensive conversion: ability to win the next round after losing one
        lost_previous = stats.get("lost_previous_round", 0)
        if lost_previous > 0:
            defensive_conversion = stats.get("comeback_wins", 0) / lost_previous
        else:
            defensive_conversion = 0.5  # Neutral if never lost a round

        metrics[bey] = {
            "burst_resistance": burst_resistance,
            "pocket_resistance": pocket_resistance,
            "extreme_resistance": extreme_resistance,
            "defensive_conversion": defensive_conversion,
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
    all_beys: list[str]
) -> dict[str, dict]:
    """
    Calculate Control sub-metrics for each Beyblade.

    Metrics:
    - volatility_inverse: 1 - normalized volatility (higher = more consistent)
    - first_contact_advantage: Match win rate when winning first round
    - match_flow_stability: Inverse of variance in round counts per match
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

        # Match flow stability (inverse of variance in round counts)
        round_counts = stats.get("match_round_counts", [])
        if len(round_counts) > 1:
            variance = statistics.variance(round_counts)
            # Normalize variance (typical range 0-10)
            match_flow_stability = 1.0 - min(1.0, variance / 10.0)
        else:
            match_flow_stability = 0.5

        metrics[bey] = {
            "volatility_inverse": volatility_inverse,
            "first_contact_advantage": first_contact_advantage,
            "match_flow_stability": match_flow_stability,
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
    all_burst = [m["burst_finish_rate"] for m in all_metrics]
    all_pocket = [m["pocket_finish_rate"] for m in all_metrics]
    all_extreme = [m["extreme_finish_rate"] for m in all_metrics]
    all_efficiency = [m["offensive_point_efficiency"] for m in all_metrics]
    all_opening = [m["opening_dominance"] for m in all_metrics]

    # Normalize each metric
    norm_burst = percentile_normalize(metrics["burst_finish_rate"], all_burst)
    norm_pocket = percentile_normalize(metrics["pocket_finish_rate"], all_pocket)
    norm_extreme = percentile_normalize(metrics["extreme_finish_rate"], all_extreme)
    norm_efficiency = percentile_normalize(
        metrics["offensive_point_efficiency"], all_efficiency
    )
    norm_opening = percentile_normalize(metrics["opening_dominance"], all_opening)

    # Weighted combination
    raw_score = (
        ATTACK_WEIGHTS["burst_finish_rate"] * norm_burst
        + ATTACK_WEIGHTS["pocket_finish_rate"] * norm_pocket
        + ATTACK_WEIGHTS["extreme_finish_rate"] * norm_extreme
        + ATTACK_WEIGHTS["offensive_point_efficiency"] * norm_efficiency
        + ATTACK_WEIGHTS["opening_dominance"] * norm_opening
    )

    return clamp(raw_score * 5.0)


def calculate_defense_stat(metrics: dict, all_metrics: list[dict]) -> float:
    """Calculate the Defense stat (0-5) from defense metrics."""
    all_burst_res = [m["burst_resistance"] for m in all_metrics]
    all_pocket_res = [m["pocket_resistance"] for m in all_metrics]
    all_extreme_res = [m["extreme_resistance"] for m in all_metrics]
    all_conversion = [m["defensive_conversion"] for m in all_metrics]

    norm_burst = percentile_normalize(metrics["burst_resistance"], all_burst_res)
    norm_pocket = percentile_normalize(metrics["pocket_resistance"], all_pocket_res)
    norm_extreme = percentile_normalize(metrics["extreme_resistance"], all_extreme_res)
    norm_conversion = percentile_normalize(
        metrics["defensive_conversion"], all_conversion
    )

    raw_score = (
        DEFENSE_WEIGHTS["burst_resistance"] * norm_burst
        + DEFENSE_WEIGHTS["pocket_resistance"] * norm_pocket
        + DEFENSE_WEIGHTS["extreme_resistance"] * norm_extreme
        + DEFENSE_WEIGHTS["defensive_conversion"] * norm_conversion
    )

    return clamp(raw_score * 5.0)


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

    return clamp(raw_score * 5.0)


def calculate_control_stat(metrics: dict, all_metrics: list[dict]) -> float:
    """Calculate the Control stat (0-5) from control metrics."""
    all_vol_inv = [m["volatility_inverse"] for m in all_metrics]
    all_first = [m["first_contact_advantage"] for m in all_metrics]
    all_flow = [m["match_flow_stability"] for m in all_metrics]

    norm_vol = percentile_normalize(metrics["volatility_inverse"], all_vol_inv)
    norm_first = percentile_normalize(metrics["first_contact_advantage"], all_first)
    norm_flow = percentile_normalize(metrics["match_flow_stability"], all_flow)

    raw_score = (
        CONTROL_WEIGHTS["volatility_inverse"] * norm_vol
        + CONTROL_WEIGHTS["first_contact_advantage"] * norm_first
        + CONTROL_WEIGHTS["match_flow_stability"] * norm_flow
    )

    return clamp(raw_score * 5.0)


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

    return clamp(raw_score * 5.0)


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

    # Get all beys
    all_beys = list(advanced_lb.keys())

    print(f"{CYAN}Calculating round statistics for {len(all_beys)} beys...{RESET}")

    # Calculate round-level stats
    bey_round_stats = calculate_bey_round_stats(matches, rounds)

    print(f"{CYAN}Calculating sub-metrics...{RESET}")

    # Calculate sub-metrics for each category
    attack_metrics = calculate_attack_metrics(bey_round_stats, all_beys)
    defense_metrics = calculate_defense_metrics(bey_round_stats, all_beys)
    stamina_metrics = calculate_stamina_metrics(bey_round_stats, all_beys)
    control_metrics = calculate_control_metrics(
        bey_round_stats, advanced_lb, all_beys
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

        results[bey] = {
            "stats": {
                "attack": round(attack, 2),
                "defense": round(defense, 2),
                "stamina": round(stamina, 2),
                "control": round(control, 2),
                "meta_impact": round(meta_impact, 2),
            },
            "sub_metrics": {
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
            },
            "leaderboard": {
                "rank": lb_data.get("rank", 0),
                "elo": lb_data.get("elo", 1000),
                "matches": lb_data.get("matches", 0),
            },
        }

    return results


def save_rpg_stats(stats: dict[str, dict]) -> None:
    """Save RPG stats to JSON and CSV files."""
    # Save JSON
    with open(RPG_STATS_JSON, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    # Copy to docs folder
    with open(DOCS_RPG_STATS_JSON, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"{GREEN}RPG stats saved to {RPG_STATS_JSON}{RESET}")
    print(f"{GREEN}RPG stats copied to {DOCS_RPG_STATS_JSON}{RESET}")

    # Save CSV for easy viewing
    header = ["Bey", "Rank", "ELO", "Attack", "Defense", "Stamina", "Control", "Meta"]
    with open(RPG_STATS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        # Sort by rank
        sorted_beys = sorted(
            stats.items(),
            key=lambda x: x[1]["leaderboard"]["rank"]
        )

        for bey, data in sorted_beys:
            writer.writerow([
                bey,
                data["leaderboard"]["rank"],
                data["leaderboard"]["elo"],
                data["stats"]["attack"],
                data["stats"]["defense"],
                data["stats"]["stamina"],
                data["stats"]["control"],
                data["stats"]["meta_impact"],
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
