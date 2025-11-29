# synergy_heatmaps.py
"""
Synergy Heatmap System for Beyblade Analytics

This module calculates synergy scores for part combinations:
- Blade × Bit synergy
- Blade × Ratchet synergy
- Bit × Ratchet synergy

Synergy scores are computed from match data and part statistics
to identify which combinations perform well together.
"""

import json
import os
import pandas as pd
import numpy as np

# File paths
BEYS_DATA_JSON = "./docs/data/beys_data.json"
PARTS_STATS_JSON = "./csv/parts_stats.json"
ELO_HISTORY_CSV = "./csv/elo_history.csv"
ROUNDS_CSV = "./csv/rounds.csv"
SYNERGY_OUTPUT_JSON = "./docs/data/synergy_data.json"
SYNERGY_CSV_DIR = "./csv"

# Minimum matches required for valid synergy score
MIN_MATCHES_THRESHOLD = 5

# Synergy score weights
SYNERGY_WEIGHTS = {
    "win_rate": 0.35,          # Win rate contribution
    "finish_quality": 0.25,    # Finish distribution quality (burst/extreme bonus)
    "elo_performance": 0.20,   # Average ELO performance
    "stability": 0.10,         # Consistency (inverse of variance)
    "stat_complementarity": 0.10  # How well part stats complement each other
}

# Finish type quality scores (higher = better finish)
FINISH_QUALITY = {
    "extreme": 1.0,   # 3 points - best finish
    "burst": 0.8,     # 2 points - strong finish
    "pocket": 0.6,    # 2 points - good finish
    "spin": 0.4       # 1 point - standard finish
}

# Stat complementarity constants
# Baseline bonus added to complementarity score to ensure moderate synergy
# for average stat combinations (prevents all-zero or negative scores)
COMPLEMENTARITY_BASELINE_BONUS = 0.1

# Maximum expected ELO standard deviation for stability normalization
# Based on typical competitive ELO distributions; values above this
# indicate highly volatile performance
MAX_ELO_STD_DEVIATION = 100


def load_beys_data() -> list:
    """Load beyblade data with component information."""
    with open(BEYS_DATA_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def load_parts_stats() -> dict:
    """Load parts performance statistics."""
    with open(PARTS_STATS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def load_match_history() -> pd.DataFrame:
    """Load ELO history with match results."""
    return pd.read_csv(ELO_HISTORY_CSV)


def load_rounds_data() -> pd.DataFrame:
    """Load detailed round-by-round match data."""
    return pd.read_csv(ROUNDS_CSV)


def normalize_bey_name(name: str) -> str:
    """Normalize bey name by removing spaces for consistent lookups."""
    return name.replace(" ", "") if name else ""


def build_bey_components_map(beys_data: list) -> dict:
    """
    Build a mapping from bey names to their component parts.

    Uses normalized names (spaces removed) as primary keys to handle
    inconsistencies like "Hells Hammer" vs "HellsHammer".

    Args:
        beys_data: List of bey dictionaries from beys_data.json

    Returns:
        Dictionary mapping normalized bey blade names to their components
    """
    components = {}
    for bey in beys_data:
        blade = bey.get("blade", "")
        if blade:
            normalized_blade = normalize_bey_name(blade)
            components[normalized_blade] = {
                "blade": blade,
                "ratchet": bey.get("ratchet", ""),
                "bit": bey.get("bit", ""),
                "type": bey.get("type", "")
            }

    return components


def get_bey_components(bey_name: str, bey_components: dict) -> dict | None:
    """
    Get components for a bey by name, handling name normalization.

    Args:
        bey_name: The bey name (may contain spaces)
        bey_components: The components mapping dictionary

    Returns:
        Components dict or None if not found
    """
    normalized = normalize_bey_name(bey_name)
    return bey_components.get(normalized)


def calculate_finish_quality_score(finish_counts: dict) -> float:
    """
    Calculate a finish quality score based on finish distribution.

    Higher scores indicate more decisive victories (burst/extreme).

    Args:
        finish_counts: Dict with finish type counts

    Returns:
        Quality score between 0.0 and 1.0
    """
    total = sum(finish_counts.values())
    if total == 0:
        return 0.5  # Neutral score for no data

    weighted_sum = sum(
        count * FINISH_QUALITY.get(finish, 0.4)
        for finish, count in finish_counts.items()
    )
    return weighted_sum / total


def calculate_stat_complementarity(
    part1_stats: dict,
    part2_stats: dict,
    part1_type: str,
    part2_type: str
) -> float:
    """
    Calculate how well two parts' statistics complement each other.

    Good synergy occurs when:
    - Attack blade + Control bit
    - Defense blade + Stability ratchet
    - High stamina parts together

    Args:
        part1_stats: Stats dict for first part
        part2_stats: Stats dict for second part
        part1_type: Type of first part (blade/ratchet/bit)
        part2_type: Type of second part (blade/ratchet/bit)

    Returns:
        Complementarity score between 0.0 and 1.0
    """
    if not part1_stats or not part2_stats:
        return 0.5  # Neutral for missing data

    # Calculate average stat values (normalized to 0-1 from 0-5 scale)
    avg1 = np.mean(list(part1_stats.values())) / 5.0
    avg2 = np.mean(list(part2_stats.values())) / 5.0

    # Simple complementarity: higher total stats = better synergy potential
    base_score = (avg1 + avg2) / 2.0

    # Penalty for imbalanced stat combinations
    variance_penalty = abs(avg1 - avg2) * 0.2

    return min(1.0, max(0.0, base_score - variance_penalty + COMPLEMENTARITY_BASELINE_BONUS))


def calculate_synergy_score(
    win_rate: float,
    finish_quality: float,
    elo_performance: float,
    stability: float,
    stat_complementarity: float
) -> float:
    """
    Calculate the composite synergy score (0-100 scale).

    Args:
        win_rate: Win rate (0.0 to 1.0)
        finish_quality: Finish quality score (0.0 to 1.0)
        elo_performance: Normalized ELO performance (0.0 to 1.0)
        stability: Stability factor (0.0 to 1.0)
        stat_complementarity: Stat complementarity (0.0 to 1.0)

    Returns:
        Synergy score from 0 to 100
    """
    score = (
        SYNERGY_WEIGHTS["win_rate"] * win_rate
        + SYNERGY_WEIGHTS["finish_quality"] * finish_quality
        + SYNERGY_WEIGHTS["elo_performance"] * elo_performance
        + SYNERGY_WEIGHTS["stability"] * stability
        + SYNERGY_WEIGHTS["stat_complementarity"] * stat_complementarity
    )
    return round(score * 100, 1)


def compute_pair_synergy(
    matches_df: pd.DataFrame,
    rounds_df: pd.DataFrame,
    bey_components: dict,
    parts_stats: dict,
    part1_key: str,
    part2_key: str
) -> dict:
    """
    Compute synergy scores for a pair of part types.

    Args:
        matches_df: Match history DataFrame
        rounds_df: Rounds data DataFrame
        bey_components: Bey to components mapping
        parts_stats: Parts statistics data
        part1_key: First part type ('blade', 'ratchet', 'bit')
        part2_key: Second part type ('blade', 'ratchet', 'bit')

    Returns:
        Dictionary with synergy matrix and metadata
    """
    # Get all unique parts
    parts1 = set()
    parts2 = set()

    for bey, components in bey_components.items():
        p1 = components.get(part1_key, "")
        p2 = components.get(part2_key, "")
        if p1:
            parts1.add(p1)
        if p2:
            parts2.add(p2)

    parts1 = sorted(parts1)
    parts2 = sorted(parts2)

    # Initialize tracking structures
    pair_stats = {}  # (part1, part2) -> stats

    # Process matches
    for _, match in matches_df.iterrows():
        bey_a = match["BeyA"]
        bey_b = match["BeyB"]
        score_a = match["ScoreA"]
        score_b = match["ScoreB"]
        post_a = match["PostA"]
        post_b = match["PostB"]

        for bey, score, opp_score, post_elo in [
            (bey_a, score_a, score_b, post_a),
            (bey_b, score_b, score_a, post_b)
        ]:
            components = get_bey_components(bey, bey_components)
            if components is None:
                continue

            p1 = components.get(part1_key, "")
            p2 = components.get(part2_key, "")

            if not p1 or not p2:
                continue

            key = (p1, p2)
            if key not in pair_stats:
                pair_stats[key] = {
                    "matches": 0,
                    "wins": 0,
                    "points_for": 0,
                    "points_against": 0,
                    "elo_values": [],
                    "finish_counts": {"spin": 0, "burst": 0, "pocket": 0, "extreme": 0}
                }

            pair_stats[key]["matches"] += 1
            pair_stats[key]["points_for"] += score
            pair_stats[key]["points_against"] += opp_score
            pair_stats[key]["elo_values"].append(post_elo)
            if score > opp_score:
                pair_stats[key]["wins"] += 1

    # Add finish type data from rounds
    for _, round_row in rounds_df.iterrows():
        winner = round_row["winner"]
        finish_type = round_row["finish_type"]

        components = get_bey_components(winner, bey_components)
        if components is None:
            continue

        p1 = components.get(part1_key, "")
        p2 = components.get(part2_key, "")

        if not p1 or not p2:
            continue

        key = (p1, p2)
        if key in pair_stats:
            pair_stats[key]["finish_counts"][finish_type] = \
                pair_stats[key]["finish_counts"].get(finish_type, 0) + 1

    # Calculate synergy scores
    synergy_matrix = {}
    max_elo = max(
        (max(s["elo_values"]) for s in pair_stats.values() if s["elo_values"]),
        default=1100
    )
    min_elo = min(
        (min(s["elo_values"]) for s in pair_stats.values() if s["elo_values"]),
        default=900
    )
    elo_range = max_elo - min_elo if max_elo != min_elo else 1

    # Get parts stats for complementarity calculation
    stats_key1 = part1_key + "s"  # blades, ratchets, bits
    stats_key2 = part2_key + "s"

    for (p1, p2), stats in pair_stats.items():
        # Win rate
        win_rate = stats["wins"] / stats["matches"] if stats["matches"] > 0 else 0.5

        # Finish quality
        finish_quality = calculate_finish_quality_score(stats["finish_counts"])

        # ELO performance (normalized)
        avg_elo = np.mean(stats["elo_values"]) if stats["elo_values"] else 1000
        elo_performance = (avg_elo - min_elo) / elo_range

        # Stability (inverse of variance, normalized)
        if len(stats["elo_values"]) > 1:
            elo_std = np.std(stats["elo_values"])
            stability = 1.0 - min(elo_std / MAX_ELO_STD_DEVIATION, 1.0)
        else:
            stability = 0.5  # Neutral for single data point

        # Stat complementarity
        part1_data = parts_stats.get(stats_key1, {}).get(p1, {})
        part2_data = parts_stats.get(stats_key2, {}).get(p2, {})
        part1_stats = part1_data.get("stats", {})
        part2_stats = part2_data.get("stats", {})
        complementarity = calculate_stat_complementarity(
            part1_stats, part2_stats, part1_key, part2_key
        )

        # Calculate final synergy score
        synergy_score = calculate_synergy_score(
            win_rate, finish_quality, elo_performance, stability, complementarity
        )

        synergy_matrix[(p1, p2)] = {
            "score": synergy_score,
            "matches": stats["matches"],
            "win_rate": round(win_rate * 100, 1),
            "finish_quality": round(finish_quality * 100, 1),
            "avg_elo": round(avg_elo, 1),
            "has_sufficient_data": stats["matches"] >= MIN_MATCHES_THRESHOLD
        }

    return {
        "parts1": parts1,
        "parts2": parts2,
        "matrix": synergy_matrix,
        "part1_type": part1_key,
        "part2_type": part2_key
    }


def generate_all_synergy_data() -> dict:
    """
    Generate synergy data for all three part pairings.

    Returns:
        Dictionary containing all synergy heatmap data
    """
    # Load data
    beys_data = load_beys_data()
    parts_stats = load_parts_stats()
    matches_df = load_match_history()
    rounds_df = load_rounds_data()

    # Build component mapping
    bey_components = build_bey_components_map(beys_data)

    # Calculate synergies for each pairing
    blade_bit_synergy = compute_pair_synergy(
        matches_df, rounds_df, bey_components, parts_stats,
        "blade", "bit"
    )

    blade_ratchet_synergy = compute_pair_synergy(
        matches_df, rounds_df, bey_components, parts_stats,
        "blade", "ratchet"
    )

    bit_ratchet_synergy = compute_pair_synergy(
        matches_df, rounds_df, bey_components, parts_stats,
        "bit", "ratchet"
    )

    return {
        "blade_bit": format_synergy_for_json(blade_bit_synergy),
        "blade_ratchet": format_synergy_for_json(blade_ratchet_synergy),
        "bit_ratchet": format_synergy_for_json(bit_ratchet_synergy),
        "metadata": {
            "min_matches_threshold": MIN_MATCHES_THRESHOLD,
            "weights": SYNERGY_WEIGHTS,
            "finish_quality_scores": FINISH_QUALITY,
            "total_beys_analyzed": len(bey_components),
            "total_matches_analyzed": len(matches_df)
        }
    }


def format_synergy_for_json(synergy_data: dict) -> dict:
    """
    Format synergy data for JSON serialization.

    Converts tuple keys to string format for JSON compatibility.
    """
    matrix_list = []
    for (p1, p2), data in synergy_data["matrix"].items():
        matrix_list.append({
            "part1": p1,
            "part2": p2,
            **data
        })

    return {
        "parts1": synergy_data["parts1"],
        "parts2": synergy_data["parts2"],
        "part1_type": synergy_data["part1_type"],
        "part2_type": synergy_data["part2_type"],
        "data": matrix_list
    }


def save_synergy_data(synergy_data: dict) -> None:
    """Save synergy data to JSON file."""
    os.makedirs(os.path.dirname(SYNERGY_OUTPUT_JSON), exist_ok=True)

    with open(SYNERGY_OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(synergy_data, f, indent=2)

    print(f"Synergy data saved to {SYNERGY_OUTPUT_JSON}")


def get_top_synergies(synergy_data: dict, pair_type: str, n: int = 10) -> list:
    """
    Get top N synergy combinations for a specific pairing.

    Args:
        synergy_data: Full synergy data dictionary
        pair_type: 'blade_bit', 'blade_ratchet', or 'bit_ratchet'
        n: Number of top synergies to return

    Returns:
        List of top synergy combinations with scores
    """
    pair_data = synergy_data.get(pair_type, {})
    data_list = pair_data.get("data", [])

    # Filter for sufficient data and sort by score
    valid_data = [d for d in data_list if d.get("has_sufficient_data", False)]
    sorted_data = sorted(valid_data, key=lambda x: x["score"], reverse=True)

    return sorted_data[:n]


def get_low_synergies(synergy_data: dict, pair_type: str, n: int = 10) -> list:
    """
    Get bottom N synergy combinations for a specific pairing.

    Args:
        synergy_data: Full synergy data dictionary
        pair_type: 'blade_bit', 'blade_ratchet', or 'bit_ratchet'
        n: Number of low synergies to return

    Returns:
        List of low synergy combinations with scores
    """
    pair_data = synergy_data.get(pair_type, {})
    data_list = pair_data.get("data", [])

    # Filter for sufficient data and sort by score
    valid_data = [d for d in data_list if d.get("has_sufficient_data", False)]
    sorted_data = sorted(valid_data, key=lambda x: x["score"])

    return sorted_data[:n]


# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == "__main__":
    print("Generating Synergy Heatmap Data...")

    # Generate all synergy data
    synergy_data = generate_all_synergy_data()

    # Save to JSON
    save_synergy_data(synergy_data)

    # Print summary
    print("\n=== Synergy Data Summary ===")

    for pair_type in ["blade_bit", "blade_ratchet", "bit_ratchet"]:
        pair_data = synergy_data[pair_type]
        total_pairs = len(pair_data["data"])
        sufficient_data = sum(1 for d in pair_data["data"] if d["has_sufficient_data"])

        print(f"\n{pair_type.replace('_', ' × ').title()}:")
        print(f"  Total pairs: {total_pairs}")
        print(f"  With sufficient data (>={MIN_MATCHES_THRESHOLD} matches): {sufficient_data}")

        # Show top 3 synergies
        top = get_top_synergies(synergy_data, pair_type, 3)
        if top:
            print("  Top synergies:")
            for t in top:
                print(f"    {t['part1']} × {t['part2']}: {t['score']} "
                      f"(WR: {t['win_rate']}%, {t['matches']} matches)")

    print("\n=== Done! ===")
