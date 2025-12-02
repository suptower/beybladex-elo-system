# meta_balance.py
"""
Meta Balance Analyzer Module for Beyblade ELO Rating System

This module evaluates how healthy, diverse, and fair the current competitive meta is.
It provides quantitative indicators of meta health, detects overperforming or
underperforming parts and combinations, and identifies trends.

Key Metrics:
- Usage Diversity Index: Shannon entropy across Blades/Ratchets/Bits
- Win Rate Deviation Score: Variance of win rates across top-used parts
- ELO Compression Ratio: Spread vs. clustering of ELO across the field
- Top-3 Dominance Share: Percentage of matches represented by top 3 combos/parts
- Matchup Polarization Index: Frequency of >70/30 matchup splits

Output:
- meta_balance.json: All meta health metrics and outlier analysis
"""
import csv
import json
import math
import os
import statistics
from collections import defaultdict

# Colors for terminal output
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"

# File paths
ELO_HISTORY_CSV = "./data/elo_history.csv"
BEYS_DATA_JSON = "./docs/data/beys_data.json"
PARTS_STATS_JSON = "./data/parts_stats.json"
ADVANCED_LEADERBOARD_CSV = "./data/advanced_leaderboard.csv"
META_BALANCE_OUTPUT_JSON = "./docs/data/meta_balance.json"

# Metric weights for overall meta health score
META_HEALTH_WEIGHTS = {
    "usage_diversity": 0.25,        # Higher diversity = healthier meta
    "win_rate_balance": 0.25,       # Lower variance = healthier meta
    "elo_spread": 0.20,             # Moderate spread = healthier meta
    "dominance_penalty": 0.15,      # Lower dominance = healthier meta
    "polarization_penalty": 0.15    # Lower polarization = healthier meta
}

# Thresholds for outlier detection
OUTLIER_THRESHOLDS = {
    "overcentralizing_usage_percentile": 0.90,   # Top 10% usage
    "overcentralizing_win_rate": 0.60,           # >60% win rate
    "underpowered_usage_percentile": 0.30,       # Bottom 30% usage
    "underpowered_win_rate": 0.40,               # <40% win rate
    "problematic_matchup_threshold": 0.70,       # >70% win rate in matchup
    "min_matches_for_analysis": 3                # Min matches for inclusion
}

# ELO Compression scoring constants
# These define the optimal range for ELO compression ratio
# Ratio = std_dev / range
# - Below 0.20: Too compressed (not enough skill differentiation)
# - 0.25-0.35: Optimal range (healthy differentiation)
# - Above 0.40: Too spread (extreme imbalances)
ELO_COMPRESSION_CONFIG = {
    "low_threshold": 0.20,          # Below this = too compressed
    "optimal_center": 0.30,         # Center of optimal range
    "optimal_tolerance": 0.10,      # Distance from center for optimal
    "high_threshold": 0.40,         # Above this = too spread
    "high_upper_bound": 0.60,       # Upper bound for normalization
    "suboptimal_penalty": 0.70      # Max score when outside optimal range
}


def shannon_entropy(probabilities):
    """
    Calculate Shannon entropy for a probability distribution.

    Shannon entropy measures the uncertainty or diversity in a distribution.
    Higher entropy indicates more uniform/diverse usage across options.

    Args:
        probabilities: List of probability values (should sum to ~1)

    Returns:
        float: Entropy value (0 = completely concentrated, log2(n) = uniform)
    """
    if not probabilities:
        return 0.0

    entropy = 0.0
    for p in probabilities:
        if p > 0:
            entropy -= p * math.log2(p)

    return entropy


def normalize_to_0_100(value, min_val, max_val, invert=False):
    """
    Normalize a value to a 0-100 scale.

    Args:
        value: Value to normalize
        min_val: Minimum expected value
        max_val: Maximum expected value
        invert: If True, higher input = lower output (for penalty metrics)

    Returns:
        float: Normalized value between 0 and 100
    """
    if max_val == min_val:
        return 50.0

    normalized = (value - min_val) / (max_val - min_val)
    normalized = max(0.0, min(1.0, normalized))

    if invert:
        normalized = 1.0 - normalized

    return round(normalized * 100, 1)


def load_elo_history():
    """Load and parse ELO history data."""
    matches = []
    with open(ELO_HISTORY_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if int(row["ScoreA"]) + int(row["ScoreB"]) > 0:
                matches.append({
                    "date": row["Date"],
                    "bey_a": row["BeyA"],
                    "bey_b": row["BeyB"],
                    "score_a": int(row["ScoreA"]),
                    "score_b": int(row["ScoreB"]),
                    "pre_a": float(row["PreA"]),
                    "pre_b": float(row["PreB"]),
                    "post_a": float(row["PostA"]),
                    "post_b": float(row["PostB"])
                })
    return matches


def load_beys_data():
    """Load Beyblade component data."""
    if not os.path.exists(BEYS_DATA_JSON):
        return []
    with open(BEYS_DATA_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def load_advanced_leaderboard():
    """Load advanced leaderboard data."""
    data = []
    if not os.path.exists(ADVANCED_LEADERBOARD_CSV):
        return data
    with open(ADVANCED_LEADERBOARD_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                "bey": row["Bey"],
                "elo": int(row["ELO"]),
                "matches": int(row["Matches"]),
                "wins": int(row["Wins"]),
                "losses": int(row["Losses"]),
                "winrate": float(row["Winrate"].replace("%", "")) / 100,
                "power_index": float(row["PowerIndex"])
            })
    return data


def calculate_usage_diversity(matches, beys_data):
    """
    Calculate the Usage Diversity Index using Shannon entropy.

    Measures how evenly usage is distributed across blades, ratchets, and bits.
    Higher diversity indicates a healthier meta where more options are viable.

    Args:
        matches: List of match data
        beys_data: List of bey component data

    Returns:
        dict: Diversity scores for each part type and overall
    """
    # Build component mapping
    bey_components = {}
    for bey in beys_data:
        blade = bey.get("blade", "")
        if blade:
            normalized = blade.replace(" ", "")
            bey_components[normalized] = {
                "blade": blade,
                "ratchet": bey.get("ratchet", ""),
                "bit": bey.get("bit", "")
            }

    # Count usage of each component type
    blade_usage = defaultdict(int)
    ratchet_usage = defaultdict(int)
    bit_usage = defaultdict(int)
    bey_usage = defaultdict(int)

    for match in matches:
        for bey_name in [match["bey_a"], match["bey_b"]]:
            bey_usage[bey_name] += 1
            normalized = bey_name.replace(" ", "")
            if normalized in bey_components:
                components = bey_components[normalized]
                if components["blade"]:
                    blade_usage[components["blade"]] += 1
                if components["ratchet"]:
                    ratchet_usage[components["ratchet"]] += 1
                if components["bit"]:
                    bit_usage[components["bit"]] += 1

    def calculate_diversity_score(usage_dict):
        """Calculate diversity from usage counts."""
        if not usage_dict:
            return {"entropy": 0, "max_entropy": 0, "score": 50.0, "unique_count": 0}

        total = sum(usage_dict.values())
        if total == 0:
            return {"entropy": 0, "max_entropy": 0, "score": 50.0, "unique_count": 0}

        probabilities = [count / total for count in usage_dict.values()]
        entropy = shannon_entropy(probabilities)
        max_entropy = math.log2(len(usage_dict)) if len(usage_dict) > 1 else 1

        # Normalize to 0-100 (100 = perfectly uniform)
        score = (entropy / max_entropy * 100) if max_entropy > 0 else 50.0

        return {
            "entropy": round(entropy, 3),
            "max_entropy": round(max_entropy, 3),
            "score": round(score, 1),
            "unique_count": len(usage_dict)
        }

    blade_diversity = calculate_diversity_score(blade_usage)
    ratchet_diversity = calculate_diversity_score(ratchet_usage)
    bit_diversity = calculate_diversity_score(bit_usage)
    bey_diversity = calculate_diversity_score(bey_usage)

    # Overall diversity is weighted average
    overall_score = (
        blade_diversity["score"] * 0.35
        + ratchet_diversity["score"] * 0.25
        + bit_diversity["score"] * 0.25
        + bey_diversity["score"] * 0.15
    )

    return {
        "overall_score": round(overall_score, 1),
        "blade": blade_diversity,
        "ratchet": ratchet_diversity,
        "bit": bit_diversity,
        "bey": bey_diversity,
        "top_used_blades": sorted(blade_usage.items(), key=lambda x: -x[1])[:5],
        "top_used_ratchets": sorted(ratchet_usage.items(), key=lambda x: -x[1])[:5],
        "top_used_bits": sorted(bit_usage.items(), key=lambda x: -x[1])[:5]
    }


def calculate_win_rate_deviation(leaderboard_data):
    """
    Calculate the Win Rate Deviation Score.

    Measures the variance in win rates among active Beyblades.
    Lower variance indicates more balanced matchups and healthier meta.

    Args:
        leaderboard_data: List of leaderboard entries

    Returns:
        dict: Win rate statistics and balance score
    """
    min_matches = OUTLIER_THRESHOLDS["min_matches_for_analysis"]
    filtered_data = [d for d in leaderboard_data if d["matches"] >= min_matches]

    if len(filtered_data) < 2:
        return {
            "score": 50.0,
            "std_deviation": 0,
            "variance": 0,
            "mean_winrate": 0.5,
            "min_winrate": 0.5,
            "max_winrate": 0.5,
            "range": 0,
            "beys_analyzed": len(filtered_data)
        }

    win_rates = [d["winrate"] for d in filtered_data]

    mean_wr = statistics.mean(win_rates)
    std_dev = statistics.stdev(win_rates)
    variance = statistics.variance(win_rates)
    min_wr = min(win_rates)
    max_wr = max(win_rates)
    wr_range = max_wr - min_wr

    # Score: Lower variance = higher score (healthier)
    # Expected std dev range: 0 (perfect balance) to 0.3 (highly imbalanced)
    score = normalize_to_0_100(std_dev, 0, 0.3, invert=True)

    return {
        "score": score,
        "std_deviation": round(std_dev, 4),
        "variance": round(variance, 4),
        "mean_winrate": round(mean_wr, 4),
        "min_winrate": round(min_wr, 4),
        "max_winrate": round(max_wr, 4),
        "range": round(wr_range, 4),
        "beys_analyzed": len(filtered_data)
    }


def calculate_elo_compression_ratio(leaderboard_data):
    """
    Calculate the ELO Compression Ratio.

    Measures the spread and clustering of ELO ratings.
    A healthy meta has moderate spread - not too compressed (no differentiation)
    and not too spread (extreme imbalances).

    Args:
        leaderboard_data: List of leaderboard entries

    Returns:
        dict: ELO distribution statistics and health score
    """
    min_matches = OUTLIER_THRESHOLDS["min_matches_for_analysis"]
    filtered_data = [d for d in leaderboard_data if d["matches"] >= min_matches]

    if len(filtered_data) < 2:
        return {
            "score": 50.0,
            "mean_elo": 1000,
            "std_deviation": 0,
            "min_elo": 1000,
            "max_elo": 1000,
            "range": 0,
            "compression_ratio": 0,
            "beys_analyzed": len(filtered_data)
        }

    elos = [d["elo"] for d in filtered_data]

    mean_elo = statistics.mean(elos)
    std_dev = statistics.stdev(elos)
    min_elo = min(elos)
    max_elo = max(elos)
    elo_range = max_elo - min_elo

    # Compression ratio: std_dev relative to range
    compression_ratio = std_dev / elo_range if elo_range > 0 else 0

    # Score: Moderate compression is healthy
    # Use configuration constants for scoring thresholds
    config = ELO_COMPRESSION_CONFIG
    if compression_ratio < config["low_threshold"]:
        # Too compressed - penalize with max score of suboptimal_penalty
        score = normalize_to_0_100(
            compression_ratio, 0, config["low_threshold"]
        ) * config["suboptimal_penalty"]
    elif compression_ratio > config["high_threshold"]:
        # Too spread - penalize with max score of suboptimal_penalty
        score = normalize_to_0_100(
            compression_ratio, config["high_threshold"],
            config["high_upper_bound"], invert=True
        ) * config["suboptimal_penalty"]
    else:
        # Optimal range - score 70-100 based on distance from optimal center
        base_score = config["suboptimal_penalty"] * 100
        deviation = abs(compression_ratio - config["optimal_center"])
        bonus = normalize_to_0_100(
            deviation, 0, config["optimal_tolerance"], invert=True
        ) * (100 - base_score) / 100
        score = base_score + bonus

    return {
        "score": round(score, 1),
        "mean_elo": round(mean_elo, 1),
        "std_deviation": round(std_dev, 1),
        "min_elo": round(min_elo, 1),
        "max_elo": round(max_elo, 1),
        "range": round(elo_range, 1),
        "compression_ratio": round(compression_ratio, 3),
        "beys_analyzed": len(filtered_data)
    }


def calculate_top_dominance_share(matches, leaderboard_data):
    """
    Calculate the Top-3 Dominance Share.

    Measures what percentage of all matches feature the top 3 Beyblades.
    High dominance indicates an overcentralized meta.

    Args:
        matches: List of match data
        leaderboard_data: List of leaderboard entries

    Returns:
        dict: Dominance statistics and health score
    """
    if not matches or not leaderboard_data:
        return {
            "score": 50.0,
            "top_3_share": 0,
            "top_5_share": 0,
            "top_10_share": 0,
            "top_3_beys": [],
            "total_matches": 0
        }

    # Sort by ELO to get top beys
    sorted_beys = sorted(leaderboard_data, key=lambda x: -x["elo"])
    top_3 = set(d["bey"] for d in sorted_beys[:3])
    top_5 = set(d["bey"] for d in sorted_beys[:5])
    top_10 = set(d["bey"] for d in sorted_beys[:10])

    # Count matches involving top beys
    top_3_matches = 0
    top_5_matches = 0
    top_10_matches = 0
    total = len(matches)

    for match in matches:
        if match["bey_a"] in top_3 or match["bey_b"] in top_3:
            top_3_matches += 1
        if match["bey_a"] in top_5 or match["bey_b"] in top_5:
            top_5_matches += 1
        if match["bey_a"] in top_10 or match["bey_b"] in top_10:
            top_10_matches += 1

    top_3_share = top_3_matches / total if total > 0 else 0
    top_5_share = top_5_matches / total if total > 0 else 0
    top_10_share = top_10_matches / total if total > 0 else 0

    # Score: Lower dominance = higher score
    # Expected range: 0.1 (healthy) to 0.7 (overcentralized)
    score = normalize_to_0_100(top_3_share, 0.1, 0.7, invert=True)

    return {
        "score": round(score, 1),
        "top_3_share": round(top_3_share * 100, 1),
        "top_5_share": round(top_5_share * 100, 1),
        "top_10_share": round(top_10_share * 100, 1),
        "top_3_beys": list(top_3),
        "total_matches": total
    }


def calculate_matchup_polarization(matches):
    """
    Calculate the Matchup Polarization Index.

    Measures the frequency of highly one-sided matchups (>70/30 splits).
    High polarization indicates problematic matchup imbalances.

    Args:
        matches: List of match data

    Returns:
        dict: Polarization statistics and health score
    """
    # Build matchup win rates
    matchup_stats = defaultdict(lambda: {"wins": 0, "losses": 0})

    for match in matches:
        bey_a, bey_b = match["bey_a"], match["bey_b"]
        winner = bey_a if match["score_a"] > match["score_b"] else bey_b

        # Create canonical matchup key (alphabetically sorted)
        key = tuple(sorted([bey_a, bey_b]))
        if winner == key[0]:
            matchup_stats[key]["wins"] += 1
        else:
            matchup_stats[key]["losses"] += 1

    # Calculate win rates for each matchup
    threshold = OUTLIER_THRESHOLDS["problematic_matchup_threshold"]
    polarized_matchups = []
    total_matchups = 0
    polarized_count = 0

    for (bey1, bey2), stats in matchup_stats.items():
        total_games = stats["wins"] + stats["losses"]
        if total_games < 2:  # Need at least 2 games for meaningful analysis
            continue

        total_matchups += 1
        win_rate = stats["wins"] / total_games

        # Check for polarization (either direction)
        if win_rate >= threshold or win_rate <= (1 - threshold):
            polarized_count += 1
            polarized_matchups.append({
                "bey_1": bey1,
                "bey_2": bey2,
                "bey_1_wins": stats["wins"],
                "bey_2_wins": stats["losses"],
                "win_rate": round(win_rate * 100, 1),
                "games": total_games
            })

    polarization_rate = polarized_count / total_matchups if total_matchups > 0 else 0

    # Score: Lower polarization = higher score
    # Expected range: 0 (no polarization) to 0.5 (many polarized matchups)
    score = normalize_to_0_100(polarization_rate, 0, 0.5, invert=True)

    # Sort polarized matchups by severity
    polarized_matchups.sort(key=lambda x: abs(x["win_rate"] - 50), reverse=True)

    return {
        "score": round(score, 1),
        "polarization_rate": round(polarization_rate * 100, 1),
        "polarized_matchups_count": polarized_count,
        "total_matchups_analyzed": total_matchups,
        "threshold_used": round(threshold * 100, 1),
        "worst_matchups": polarized_matchups[:10]
    }


def identify_outliers(leaderboard_data, diversity_data, beys_data):
    """
    Identify outlier parts and combinations.

    Detects:
    - Overcentralizing parts: High usage + above-expected win rate
    - Underpowered parts: Low usage + below-expected win rate
    - Unhealthy synergies (if synergy data available)

    Args:
        leaderboard_data: List of leaderboard entries
        diversity_data: Usage diversity statistics
        beys_data: List of bey component data

    Returns:
        dict: Categorized outliers with confidence levels
    """
    outliers = {
        "overcentralizing": [],
        "underpowered": [],
        "emerging_threats": [],
        "confidence_notes": []
    }

    min_matches = OUTLIER_THRESHOLDS["min_matches_for_analysis"]
    filtered_data = [d for d in leaderboard_data if d["matches"] >= min_matches]

    if not filtered_data:
        outliers["confidence_notes"].append("Insufficient data for outlier analysis")
        return outliers

    # Calculate statistics for thresholds
    win_rates = [d["winrate"] for d in filtered_data]
    mean_wr = statistics.mean(win_rates)
    std_wr = statistics.stdev(win_rates) if len(win_rates) > 1 else 0.1

    matches_list = [d["matches"] for d in filtered_data]
    mean_matches = statistics.mean(matches_list)

    # Identify overcentralizing beys
    oc_threshold = OUTLIER_THRESHOLDS["overcentralizing_win_rate"]
    for d in filtered_data:
        if d["winrate"] >= oc_threshold and d["matches"] >= mean_matches:
            confidence = "high" if d["matches"] >= mean_matches * 1.5 else "medium"
            outliers["overcentralizing"].append({
                "bey": d["bey"],
                "elo": d["elo"],
                "winrate": round(d["winrate"] * 100, 1),
                "matches": d["matches"],
                "deviation_from_mean": round((d["winrate"] - mean_wr) / std_wr, 2) if std_wr > 0 else 0,
                "confidence": confidence
            })

    # Identify underpowered beys
    up_threshold = OUTLIER_THRESHOLDS["underpowered_win_rate"]
    for d in filtered_data:
        if d["winrate"] <= up_threshold:
            confidence = "high" if d["matches"] >= mean_matches else "medium"
            outliers["underpowered"].append({
                "bey": d["bey"],
                "elo": d["elo"],
                "winrate": round(d["winrate"] * 100, 1),
                "matches": d["matches"],
                "deviation_from_mean": round((d["winrate"] - mean_wr) / std_wr, 2) if std_wr > 0 else 0,
                "confidence": confidence
            })

    # Identify emerging threats (high win rate, low matches)
    for d in filtered_data:
        if d["winrate"] >= oc_threshold and d["matches"] < mean_matches:
            outliers["emerging_threats"].append({
                "bey": d["bey"],
                "elo": d["elo"],
                "winrate": round(d["winrate"] * 100, 1),
                "matches": d["matches"],
                "note": "Potentially overcentralizing but needs more data"
            })

    # Add confidence notes
    if len(filtered_data) < 10:
        outliers["confidence_notes"].append(
            f"Limited sample size ({len(filtered_data)} beys with {min_matches}+ matches)"
        )
    if mean_matches < 5:
        outliers["confidence_notes"].append(
            "Low average match count - results may be preliminary"
        )

    # Sort by severity
    outliers["overcentralizing"].sort(key=lambda x: -x["winrate"])
    outliers["underpowered"].sort(key=lambda x: x["winrate"])

    return outliers


def calculate_meta_health(diversity, win_rate_dev, elo_compression, dominance, polarization):
    """
    Calculate the overall Meta Health Score (0-100).

    Combines all individual metrics into a single health indicator.

    Args:
        diversity: Usage diversity data
        win_rate_dev: Win rate deviation data
        elo_compression: ELO compression data
        dominance: Top dominance data
        polarization: Matchup polarization data

    Returns:
        dict: Overall meta health score and breakdown
    """
    # Extract individual scores
    diversity_score = diversity.get("overall_score", 50)
    balance_score = win_rate_dev.get("score", 50)
    spread_score = elo_compression.get("score", 50)
    dominance_score = dominance.get("score", 50)
    polarization_score = polarization.get("score", 50)

    # Calculate weighted overall score
    overall_score = (
        META_HEALTH_WEIGHTS["usage_diversity"] * diversity_score
        + META_HEALTH_WEIGHTS["win_rate_balance"] * balance_score
        + META_HEALTH_WEIGHTS["elo_spread"] * spread_score
        + META_HEALTH_WEIGHTS["dominance_penalty"] * dominance_score
        + META_HEALTH_WEIGHTS["polarization_penalty"] * polarization_score
    )

    # Determine health status
    if overall_score >= 75:
        status = "Healthy"
        status_class = "excellent"
    elif overall_score >= 60:
        status = "Balanced"
        status_class = "good"
    elif overall_score >= 45:
        status = "Moderate"
        status_class = "moderate"
    elif overall_score >= 30:
        status = "Imbalanced"
        status_class = "warning"
    else:
        status = "Critical"
        status_class = "critical"

    # Generate alerts for concerning metrics
    alerts = []
    if diversity_score < 40:
        alerts.append({
            "type": "warning",
            "metric": "Usage Diversity",
            "message": "Usage concentration is critically high - consider promoting variety"
        })
    if balance_score < 40:
        alerts.append({
            "type": "warning",
            "metric": "Win Rate Balance",
            "message": "Win rates are highly variable - some options may be too strong/weak"
        })
    if dominance_score < 40:
        alerts.append({
            "type": "warning",
            "metric": "Top Dominance",
            "message": "Top performers dominate too many matches - meta may be centralized"
        })
    if polarization_score < 40:
        alerts.append({
            "type": "warning",
            "metric": "Matchup Polarization",
            "message": "Many matchups are one-sided - strategic variety is limited"
        })

    return {
        "overall_score": round(overall_score, 1),
        "status": status,
        "status_class": status_class,
        "breakdown": {
            "usage_diversity": {
                "score": diversity_score,
                "weight": META_HEALTH_WEIGHTS["usage_diversity"],
                "contribution": round(META_HEALTH_WEIGHTS["usage_diversity"] * diversity_score, 1)
            },
            "win_rate_balance": {
                "score": balance_score,
                "weight": META_HEALTH_WEIGHTS["win_rate_balance"],
                "contribution": round(META_HEALTH_WEIGHTS["win_rate_balance"] * balance_score, 1)
            },
            "elo_spread": {
                "score": spread_score,
                "weight": META_HEALTH_WEIGHTS["elo_spread"],
                "contribution": round(META_HEALTH_WEIGHTS["elo_spread"] * spread_score, 1)
            },
            "dominance_penalty": {
                "score": dominance_score,
                "weight": META_HEALTH_WEIGHTS["dominance_penalty"],
                "contribution": round(META_HEALTH_WEIGHTS["dominance_penalty"] * dominance_score, 1)
            },
            "polarization_penalty": {
                "score": polarization_score,
                "weight": META_HEALTH_WEIGHTS["polarization_penalty"],
                "contribution": round(META_HEALTH_WEIGHTS["polarization_penalty"] * polarization_score, 1)
            }
        },
        "alerts": alerts,
        "weights": META_HEALTH_WEIGHTS
    }


def generate_meta_balance_report():
    """
    Generate the complete Meta Balance Analysis report.

    Loads all necessary data, computes all metrics, and returns a
    comprehensive analysis dictionary.

    Returns:
        dict: Complete meta balance analysis
    """
    # Load data
    matches = load_elo_history()
    beys_data = load_beys_data()
    leaderboard_data = load_advanced_leaderboard()

    # Calculate individual metrics
    diversity = calculate_usage_diversity(matches, beys_data)
    win_rate_dev = calculate_win_rate_deviation(leaderboard_data)
    elo_compression = calculate_elo_compression_ratio(leaderboard_data)
    dominance = calculate_top_dominance_share(matches, leaderboard_data)
    polarization = calculate_matchup_polarization(matches)

    # Calculate overall health
    meta_health = calculate_meta_health(
        diversity, win_rate_dev, elo_compression, dominance, polarization
    )

    # Identify outliers
    outliers = identify_outliers(leaderboard_data, diversity, beys_data)

    # Compile full report
    report = {
        "meta_health": meta_health,
        "metrics": {
            "usage_diversity": diversity,
            "win_rate_deviation": win_rate_dev,
            "elo_compression": elo_compression,
            "top_dominance": dominance,
            "matchup_polarization": polarization
        },
        "outliers": outliers,
        "metadata": {
            "total_matches": len(matches),
            "total_beys": len(leaderboard_data),
            "analysis_thresholds": OUTLIER_THRESHOLDS
        }
    }

    return report


def save_meta_balance_report(report, output_path=META_BALANCE_OUTPUT_JSON):
    """
    Save the meta balance report to JSON file.

    Args:
        report: Meta balance report dictionary
        output_path: Output file path
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"{GREEN}Meta Balance report saved to: {output_path}{RESET}")


def print_report_summary(report):
    """Print a summary of the meta balance report to console."""
    health = report["meta_health"]
    metrics = report["metrics"]
    outliers = report["outliers"]

    print(f"\n{BOLD}{CYAN}=== Meta Balance Analysis ==={RESET}\n")

    # Overall health
    score = health["overall_score"]
    status = health["status"]
    if score >= 60:
        color = GREEN
    elif score >= 40:
        color = YELLOW
    else:
        color = RED

    print(f"{BOLD}Overall Meta Health:{RESET} {color}{score}/100 ({status}){RESET}\n")

    # Individual metrics
    print(f"{BOLD}Individual Metrics:{RESET}")
    print(f"  Usage Diversity:     {metrics['usage_diversity']['overall_score']}/100")
    print(f"  Win Rate Balance:    {metrics['win_rate_deviation']['score']}/100")
    print(f"  ELO Spread:          {metrics['elo_compression']['score']}/100")
    print(f"  Dominance Score:     {metrics['top_dominance']['score']}/100")
    print(f"  Polarization Score:  {metrics['matchup_polarization']['score']}/100")

    # Alerts
    if health["alerts"]:
        print(f"\n{BOLD}{YELLOW}Alerts:{RESET}")
        for alert in health["alerts"]:
            print(f"  ⚠️  {alert['message']}")

    # Outliers
    if outliers["overcentralizing"]:
        print(f"\n{BOLD}{RED}Overcentralizing (watch list):{RESET}")
        for o in outliers["overcentralizing"][:3]:
            print(f"  - {o['bey']}: {o['winrate']}% WR, {o['matches']} matches")

    if outliers["underpowered"]:
        print(f"\n{BOLD}{YELLOW}Underpowered:{RESET}")
        for o in outliers["underpowered"][:3]:
            print(f"  - {o['bey']}: {o['winrate']}% WR, {o['matches']} matches")

    print(f"\n{GREEN}Analysis complete!{RESET}")


def run_meta_balance_analysis():
    """
    Run the complete meta balance analysis pipeline.

    Returns:
        dict: Complete meta balance report
    """
    print(f"{BOLD}{CYAN}Running Meta Balance Analysis...{RESET}")

    report = generate_meta_balance_report()
    save_meta_balance_report(report)
    print_report_summary(report)

    return report


# --- Main ---
if __name__ == "__main__":
    run_meta_balance_analysis()
