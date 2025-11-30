# matchup_predictor.py
"""
Matchup Predictor: Probabilistic Outcome Model for Beyblade X

This module predicts the win probabilities between any two Beyblade combinations
using a statistical model based on ELO ratings and detailed stats. It provides:
- Overall win probability for each Bey
- Per-outcome probabilities (Burst, Pocket, Extreme, Spin Finish, Judge Decision)
- Confidence scores based on data availability
- Upset likelihood indicators

The prediction engine uses:
1. ELO-based win probability (baseline)
2. Stat differentials (Attack, Defense, Stamina, Control, Meta Impact)
3. Historical finish type rates for outcome breakdowns
"""

import json
import math
from typing import Any


# ============================================
# PREDICTION WEIGHTS
# ============================================

# Weights for combining ELO-based and stats-based predictions
PREDICTION_WEIGHTS = {
    "elo_weight": 0.50,         # Base ELO difference
    "attack_weight": 0.15,       # Attack stat differential
    "defense_weight": 0.10,      # Defense stat differential
    "stamina_weight": 0.10,      # Stamina stat differential
    "control_weight": 0.08,      # Control stat differential
    "meta_impact_weight": 0.07,  # Meta impact differential
}

# Weights for outcome type predictions
OUTCOME_WEIGHTS = {
    "burst_attack": 0.35,       # Attack influence on burst finish
    "burst_defense": 0.65,      # Defense (resistance) influence on burst finish
    "pocket_attack": 0.40,      # Attack influence on pocket finish
    "pocket_defense": 0.60,     # Defense influence on pocket finish
    "extreme_attack": 0.30,     # Attack influence on extreme finish
    "extreme_defense": 0.70,    # Defense influence on extreme finish
    "spin_stamina": 0.80,       # Stamina influence on spin finish
    "spin_control": 0.20,       # Control influence on spin finish
}

# Confidence thresholds
MIN_MATCHES_HIGH_CONFIDENCE = 8
MIN_MATCHES_MEDIUM_CONFIDENCE = 4


# ============================================
# ELO-BASED PROBABILITY FUNCTIONS
# ============================================

def calculate_expected_score(elo_a: float, elo_b: float) -> float:
    """
    Calculate the expected score for Bey A against Bey B using the ELO formula.

    Args:
        elo_a: ELO rating of Bey A
        elo_b: ELO rating of Bey B

    Returns:
        float: Expected score (probability) for Bey A, between 0 and 1
    """
    return 1.0 / (1.0 + math.pow(10, (elo_b - elo_a) / 400.0))


def calculate_stat_advantage(stat_a: float, stat_b: float) -> float:
    """
    Calculate the advantage from a stat differential.

    Normalizes the difference to a -0.5 to +0.5 range based on the
    maximum possible difference (5.0 scale for stats).

    Args:
        stat_a: Stat value for Bey A (0-5 scale)
        stat_b: Stat value for Bey B (0-5 scale)

    Returns:
        float: Advantage value between -0.5 and 0.5
    """
    diff = stat_a - stat_b
    # Max difference is 5 (one bey at 5.0, other at 0.0)
    # Normalize to -0.5 to 0.5 range
    normalized = diff / 10.0
    return max(-0.5, min(0.5, normalized))


# ============================================
# WIN PROBABILITY CALCULATION
# ============================================

def calculate_win_probability(
    stats_a: dict[str, Any],
    stats_b: dict[str, Any]
) -> dict[str, float]:
    """
    Calculate the overall win probability for each Bey.

    Combines ELO-based probability with stat-based adjustments
    to produce a final win probability.

    Args:
        stats_a: Complete stats dictionary for Bey A
        stats_b: Complete stats dictionary for Bey B

    Returns:
        dict: Contains 'prob_a' and 'prob_b' (probabilities summing to 1.0)
    """
    # Get ELO ratings (default to 1000 if not available)
    elo_a = stats_a.get("leaderboard", {}).get("elo", 1000)
    elo_b = stats_b.get("leaderboard", {}).get("elo", 1000)

    # Calculate ELO-based probability
    elo_prob_a = calculate_expected_score(elo_a, elo_b)

    # Get RPG stats (default to 2.5 neutral if not available)
    rpg_a = stats_a.get("stats", {})
    rpg_b = stats_b.get("stats", {})

    attack_a = rpg_a.get("attack", 2.5)
    attack_b = rpg_b.get("attack", 2.5)
    defense_a = rpg_a.get("defense", 2.5)
    defense_b = rpg_b.get("defense", 2.5)
    stamina_a = rpg_a.get("stamina", 2.5)
    stamina_b = rpg_b.get("stamina", 2.5)
    control_a = rpg_a.get("control", 2.5)
    control_b = rpg_b.get("control", 2.5)
    meta_a = rpg_a.get("meta_impact", 2.5)
    meta_b = rpg_b.get("meta_impact", 2.5)

    # Calculate stat advantages (positive = A is better)
    attack_adv = calculate_stat_advantage(attack_a, attack_b)
    defense_adv = calculate_stat_advantage(defense_a, defense_b)
    stamina_adv = calculate_stat_advantage(stamina_a, stamina_b)
    control_adv = calculate_stat_advantage(control_a, control_b)
    meta_adv = calculate_stat_advantage(meta_a, meta_b)

    # Combine stat advantages with weights
    stats_adjustment = (
        PREDICTION_WEIGHTS["attack_weight"] * attack_adv
        + PREDICTION_WEIGHTS["defense_weight"] * defense_adv
        + PREDICTION_WEIGHTS["stamina_weight"] * stamina_adv
        + PREDICTION_WEIGHTS["control_weight"] * control_adv
        + PREDICTION_WEIGHTS["meta_impact_weight"] * meta_adv
    )

    # Combine ELO probability with stat adjustments
    # ELO weight is ~0.5, stats contribute ~0.5
    combined_prob_a = (
        PREDICTION_WEIGHTS["elo_weight"] * elo_prob_a
        + (1 - PREDICTION_WEIGHTS["elo_weight"]) * (0.5 + stats_adjustment)
    )

    # Clamp to valid probability range
    prob_a = max(0.01, min(0.99, combined_prob_a))
    prob_b = 1.0 - prob_a

    return {
        "prob_a": round(prob_a, 4),
        "prob_b": round(prob_b, 4)
    }


# ============================================
# OUTCOME TYPE PREDICTIONS
# ============================================

def calculate_outcome_probabilities(
    stats_a: dict[str, Any],
    stats_b: dict[str, Any],
    win_probs: dict[str, float]
) -> dict[str, dict[str, float]]:
    """
    Calculate per-outcome type probabilities for each Bey.

    Predicts the probability of each finish type:
    - Burst Finish: High-impact knockout
    - Pocket Finish: Ring-out victory
    - Extreme Finish: Stadium-exit victory
    - Spin Finish: Outspin victory
    - Judge Decision: Points-based victory

    Args:
        stats_a: Complete stats dictionary for Bey A
        stats_b: Complete stats dictionary for Bey B
        win_probs: Overall win probabilities from calculate_win_probability

    Returns:
        dict: Contains outcome probabilities for both Beys
    """
    # Get sub-metrics for finish type calculations
    sub_a = stats_a.get("sub_metrics", {})
    sub_b = stats_b.get("sub_metrics", {})

    # Get historical finish rates
    attack_metrics_a = sub_a.get("attack", {})
    attack_metrics_b = sub_b.get("attack", {})
    defense_metrics_a = sub_a.get("defense", {})
    defense_metrics_b = sub_b.get("defense", {})
    stamina_metrics_a = sub_a.get("stamina", {})
    stamina_metrics_b = sub_b.get("stamina", {})

    # Historical finish rates for A (offensive)
    burst_rate_a = attack_metrics_a.get("burst_finish_rate", 0.15)
    pocket_rate_a = attack_metrics_a.get("pocket_finish_rate", 0.15)
    extreme_rate_a = attack_metrics_a.get("extreme_finish_rate", 0.10)
    spin_rate_a = stamina_metrics_a.get("spin_finish_win_rate", 0.40)

    # Historical finish rates for B (offensive)
    burst_rate_b = attack_metrics_b.get("burst_finish_rate", 0.15)
    pocket_rate_b = attack_metrics_b.get("pocket_finish_rate", 0.15)
    extreme_rate_b = attack_metrics_b.get("extreme_finish_rate", 0.10)
    spin_rate_b = stamina_metrics_b.get("spin_finish_win_rate", 0.40)

    # Defensive resistance rates (reduce opponent's finish type chances)
    burst_resist_a = defense_metrics_a.get("burst_resistance", 0.70)
    pocket_resist_a = defense_metrics_a.get("pocket_resistance", 0.70)
    extreme_resist_a = defense_metrics_a.get("extreme_resistance", 0.85)
    burst_resist_b = defense_metrics_b.get("burst_resistance", 0.70)
    pocket_resist_b = defense_metrics_b.get("pocket_resistance", 0.70)
    extreme_resist_b = defense_metrics_b.get("extreme_resistance", 0.85)

    # Calculate outcome probabilities for A (when A wins)
    # A's finish types are boosted by their offensive rates and opponent's weaknesses
    burst_a = burst_rate_a * (1.0 - burst_resist_b) * 3.0  # Scaled by opponent weakness
    pocket_a = pocket_rate_a * (1.0 - pocket_resist_b) * 3.0
    extreme_a = extreme_rate_a * (1.0 - extreme_resist_b) * 5.0
    spin_a = spin_rate_a

    # Calculate outcome probabilities for B (when B wins)
    burst_b = burst_rate_b * (1.0 - burst_resist_a) * 3.0
    pocket_b = pocket_rate_b * (1.0 - pocket_resist_a) * 3.0
    extreme_b = extreme_rate_b * (1.0 - extreme_resist_a) * 5.0
    spin_b = spin_rate_b

    # Normalize A's outcomes
    total_a = burst_a + pocket_a + extreme_a + spin_a + 0.05  # 0.05 for judge decision
    if total_a > 0:
        burst_a /= total_a
        pocket_a /= total_a
        extreme_a /= total_a
        spin_a /= total_a
        decision_a = 0.05 / total_a
    else:
        burst_a = pocket_a = extreme_a = 0.2
        spin_a = 0.35
        decision_a = 0.05

    # Normalize B's outcomes
    total_b = burst_b + pocket_b + extreme_b + spin_b + 0.05
    if total_b > 0:
        burst_b /= total_b
        pocket_b /= total_b
        extreme_b /= total_b
        spin_b /= total_b
        decision_b = 0.05 / total_b
    else:
        burst_b = pocket_b = extreme_b = 0.2
        spin_b = 0.35
        decision_b = 0.05

    # Scale by overall win probability
    prob_a = win_probs["prob_a"]
    prob_b = win_probs["prob_b"]

    return {
        "bey_a": {
            "burst_finish": round(burst_a * prob_a, 4),
            "pocket_finish": round(pocket_a * prob_a, 4),
            "extreme_finish": round(extreme_a * prob_a, 4),
            "spin_finish": round(spin_a * prob_a, 4),
            "judge_decision": round(decision_a * prob_a, 4),
        },
        "bey_b": {
            "burst_finish": round(burst_b * prob_b, 4),
            "pocket_finish": round(pocket_b * prob_b, 4),
            "extreme_finish": round(extreme_b * prob_b, 4),
            "spin_finish": round(spin_b * prob_b, 4),
            "judge_decision": round(decision_b * prob_b, 4),
        }
    }


# ============================================
# CONFIDENCE CALCULATION
# ============================================

def calculate_confidence(
    stats_a: dict[str, Any],
    stats_b: dict[str, Any]
) -> dict[str, Any]:
    """
    Calculate confidence score for the prediction.

    Confidence is based on:
    - Number of matches played by each Bey
    - Availability of detailed stats
    - Historical data quality

    Args:
        stats_a: Complete stats dictionary for Bey A
        stats_b: Complete stats dictionary for Bey B

    Returns:
        dict: Contains confidence level, score, and reasoning
    """
    matches_a = stats_a.get("leaderboard", {}).get("matches", 0)
    matches_b = stats_b.get("leaderboard", {}).get("matches", 0)

    # Check for presence of detailed stats
    has_rpg_a = bool(stats_a.get("stats"))
    has_rpg_b = bool(stats_b.get("stats"))
    has_sub_a = bool(stats_a.get("sub_metrics"))
    has_sub_b = bool(stats_b.get("sub_metrics"))

    # Calculate confidence score (0-100)
    score = 0

    # Matches contribute up to 40 points
    min_matches = min(matches_a, matches_b)
    if min_matches >= MIN_MATCHES_HIGH_CONFIDENCE:
        score += 40
    elif min_matches >= MIN_MATCHES_MEDIUM_CONFIDENCE:
        score += 25
    elif min_matches >= 1:
        score += 10

    # RPG stats contribute up to 30 points
    if has_rpg_a and has_rpg_b:
        score += 30
    elif has_rpg_a or has_rpg_b:
        score += 15

    # Sub-metrics contribute up to 30 points
    if has_sub_a and has_sub_b:
        score += 30
    elif has_sub_a or has_sub_b:
        score += 15

    # Determine confidence level
    if score >= 80:
        level = "high"
    elif score >= 50:
        level = "medium"
    else:
        level = "low"

    # Build reasoning
    reasons = []
    if min_matches >= MIN_MATCHES_HIGH_CONFIDENCE:
        reasons.append("Both Beys have sufficient match history")
    elif min_matches < MIN_MATCHES_MEDIUM_CONFIDENCE:
        reasons.append("Limited match data available")

    if has_rpg_a and has_rpg_b:
        reasons.append("Complete stat profiles available")
    elif not has_rpg_a or not has_rpg_b:
        reasons.append("Incomplete stat profiles")

    if has_sub_a and has_sub_b:
        reasons.append("Detailed finish type data available")

    return {
        "level": level,
        "score": score,
        "reasons": reasons
    }


# ============================================
# UPSET LIKELIHOOD
# ============================================

def calculate_upset_likelihood(
    stats_a: dict[str, Any],
    stats_b: dict[str, Any],
    win_probs: dict[str, float]
) -> dict[str, Any]:
    """
    Calculate the likelihood of an upset based on ELO differential
    and historical upset rates.

    An upset occurs when the lower-ELO Bey wins.

    Args:
        stats_a: Complete stats dictionary for Bey A
        stats_b: Complete stats dictionary for Bey B
        win_probs: Overall win probabilities

    Returns:
        dict: Contains upset likelihood level and description
    """
    elo_a = stats_a.get("leaderboard", {}).get("elo", 1000)
    elo_b = stats_b.get("leaderboard", {}).get("elo", 1000)

    # Determine the favorite and underdog
    if elo_a >= elo_b:
        favorite = "bey_a"
        underdog = "bey_b"
        underdog_win_prob = win_probs["prob_b"]
        elo_diff = elo_a - elo_b
    else:
        favorite = "bey_b"
        underdog = "bey_a"
        underdog_win_prob = win_probs["prob_a"]
        elo_diff = elo_b - elo_a

    # Get historical upset rates (for potential future use in model refinement)
    sub_underdog = (stats_b if underdog == "bey_b" else stats_a).get("sub_metrics", {})
    meta_metrics = sub_underdog.get("meta_impact", {})
    # Note: historical_upset_rate could be used to adjust probabilities in future versions
    _ = meta_metrics.get("upset_rate", 0.0)

    # Calculate upset likelihood
    # Higher if underdog has good upset history and close ELO
    if elo_diff < 20:
        # Very close match, not really an upset
        likelihood = "none"
        description = "Match is too close to call an upset"
    elif underdog_win_prob >= 0.40:
        likelihood = "high"
        description = "High upset potential - underdog has strong chances"
    elif underdog_win_prob >= 0.30:
        likelihood = "moderate"
        description = "Moderate upset potential"
    elif underdog_win_prob >= 0.20:
        likelihood = "low"
        description = "Low upset potential - favorite is clearly stronger"
    else:
        likelihood = "very_low"
        description = "Very low upset potential - heavily one-sided matchup"

    return {
        "likelihood": likelihood,
        "description": description,
        "elo_difference": round(elo_diff),
        "underdog": underdog,
        "favorite": favorite,
        "underdog_win_probability": round(underdog_win_prob, 4)
    }


# ============================================
# MAIN PREDICTION FUNCTION
# ============================================

def predict_matchup(
    stats_a: dict[str, Any],
    stats_b: dict[str, Any]
) -> dict[str, Any]:
    """
    Generate a complete matchup prediction between two Beyblades.

    This is the main entry point for the prediction engine.

    Args:
        stats_a: Complete stats dictionary for Bey A (from rpg_stats.json)
        stats_b: Complete stats dictionary for Bey B (from rpg_stats.json)

    Returns:
        dict: Complete prediction result containing:
            - win_probability: Overall win chances for each Bey
            - outcome_breakdown: Per-finish-type probabilities
            - confidence: Prediction confidence level and score
            - upset_likelihood: Upset potential analysis
            - stat_comparison: Head-to-head stat differentials
    """
    # Calculate overall win probability
    win_probs = calculate_win_probability(stats_a, stats_b)

    # Calculate outcome type probabilities
    outcome_probs = calculate_outcome_probabilities(stats_a, stats_b, win_probs)

    # Calculate confidence
    confidence = calculate_confidence(stats_a, stats_b)

    # Calculate upset likelihood
    upset = calculate_upset_likelihood(stats_a, stats_b, win_probs)

    # Get stat comparison
    rpg_a = stats_a.get("stats", {})
    rpg_b = stats_b.get("stats", {})

    stat_comparison = {
        "attack": {
            "bey_a": rpg_a.get("attack", 2.5),
            "bey_b": rpg_b.get("attack", 2.5),
            "advantage": "bey_a" if rpg_a.get("attack", 2.5) > rpg_b.get("attack", 2.5) else "bey_b"
        },
        "defense": {
            "bey_a": rpg_a.get("defense", 2.5),
            "bey_b": rpg_b.get("defense", 2.5),
            "advantage": "bey_a" if rpg_a.get("defense", 2.5) > rpg_b.get("defense", 2.5) else "bey_b"
        },
        "stamina": {
            "bey_a": rpg_a.get("stamina", 2.5),
            "bey_b": rpg_b.get("stamina", 2.5),
            "advantage": "bey_a" if rpg_a.get("stamina", 2.5) > rpg_b.get("stamina", 2.5) else "bey_b"
        },
        "control": {
            "bey_a": rpg_a.get("control", 2.5),
            "bey_b": rpg_b.get("control", 2.5),
            "advantage": "bey_a" if rpg_a.get("control", 2.5) > rpg_b.get("control", 2.5) else "bey_b"
        },
        "meta_impact": {
            "bey_a": rpg_a.get("meta_impact", 2.5),
            "bey_b": rpg_b.get("meta_impact", 2.5),
            "advantage": "bey_a" if rpg_a.get("meta_impact", 2.5) > rpg_b.get("meta_impact", 2.5) else "bey_b"
        }
    }

    return {
        "win_probability": win_probs,
        "outcome_breakdown": outcome_probs,
        "confidence": confidence,
        "upset_likelihood": upset,
        "stat_comparison": stat_comparison
    }


# ============================================
# JSON EXPORT FUNCTION
# ============================================

def export_prediction_json(
    name_a: str,
    name_b: str,
    stats_a: dict[str, Any],
    stats_b: dict[str, Any]
) -> str:
    """
    Export a prediction as a JSON string.

    Args:
        name_a: Name of Bey A
        name_b: Name of Bey B
        stats_a: Complete stats dictionary for Bey A
        stats_b: Complete stats dictionary for Bey B

    Returns:
        str: JSON string of the complete prediction
    """
    prediction = predict_matchup(stats_a, stats_b)
    result = {
        "matchup": {
            "bey_a": name_a,
            "bey_b": name_b
        },
        "prediction": prediction
    }
    return json.dumps(result, indent=2)


# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == "__main__":
    # Example usage
    import os

    # Load RPG stats
    rpg_stats_path = os.path.join(
        os.path.dirname(__file__),
        "..", "csv", "rpg_stats.json"
    )

    with open(rpg_stats_path, "r", encoding="utf-8") as f:
        rpg_stats = json.load(f)

    # Get list of Beys
    beys = list(rpg_stats.keys())

    if len(beys) >= 2:
        bey_a_name = beys[0]
        bey_b_name = beys[1]

        print(f"\n=== Matchup Prediction: {bey_a_name} vs {bey_b_name} ===\n")

        result = export_prediction_json(
            bey_a_name, bey_b_name,
            rpg_stats[bey_a_name], rpg_stats[bey_b_name]
        )
        print(result)
