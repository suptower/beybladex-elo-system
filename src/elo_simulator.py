#!/usr/bin/env python3
"""
Elo Outcome Simulator Module

Provides reusable math utilities and simulation functions for the Elo rating system.
This module supports:
- Expected score calculations
- Elo change predictions for win/loss scenarios
- Single match simulations
- Multi-match Monte Carlo simulations

Compatible with the site's K-factor settings.
"""

import random
from typing import Tuple, List, Dict, Optional

# Default K-factor settings (same as beyblade_elo.py)
K_LEARNING = 40
K_INTERMEDIATE = 24
K_EXPERIENCED = 12

# Default starting Elo
DEFAULT_ELO = 1000


def dynamic_k(matches: int) -> int:
    """
    Calculate K-factor based on number of matches played.

    K-Factor Rules:
    - Learning (< 6 matches): K = 40
    - Intermediate (6-14 matches): K = 24
    - Experienced (15+ matches): K = 12

    Args:
        matches: Number of matches the player has played

    Returns:
        K-factor value (40, 24, or 12)
    """
    if matches < 6:
        return K_LEARNING
    elif matches < 15:
        return K_INTERMEDIATE
    return K_EXPERIENCED


def expected_score(elo_a: float, elo_b: float) -> float:
    """
    Calculate expected score for player A against player B using Elo formula.

    The expected score represents the probability of player A winning,
    where 0.5 means equal chances.

    Args:
        elo_a: Elo rating of player A
        elo_b: Elo rating of player B

    Returns:
        Expected score for player A (between 0 and 1)
    """
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))


def calculate_elo_change(
    elo_a: float,
    elo_b: float,
    actual_score_a: float,
    k_factor_a: int
) -> float:
    """
    Calculate Elo rating change for player A after a match.

    Args:
        elo_a: Current Elo rating of player A
        elo_b: Current Elo rating of player B
        actual_score_a: Actual score achieved (1.0 for win, 0.0 for loss, 0.5 for draw)
        k_factor_a: K-factor for player A

    Returns:
        Elo change for player A (positive for gain, negative for loss)
    """
    expected_a = expected_score(elo_a, elo_b)
    return k_factor_a * (actual_score_a - expected_a)


def calculate_match_outcomes(
    elo_a: float,
    elo_b: float,
    matches_a: int = 0,
    matches_b: int = 0,
    k_factor_a: Optional[int] = None,
    k_factor_b: Optional[int] = None
) -> Dict:
    """
    Calculate expected outcomes for a single match including probabilities and Elo changes.

    Args:
        elo_a: Elo rating of player A
        elo_b: Elo rating of player B
        matches_a: Number of matches player A has played (for K-factor)
        matches_b: Number of matches player B has played (for K-factor)
        k_factor_a: Override K-factor for player A (optional)
        k_factor_b: Override K-factor for player B (optional)

    Returns:
        Dictionary containing:
        - expected_a: Expected score for player A
        - expected_b: Expected score for player B
        - win_prob_a: Win probability for player A
        - win_prob_b: Win probability for player B
        - k_factor_a: K-factor used for player A
        - k_factor_b: K-factor used for player B
        - elo_change_a_win: Elo change for A if A wins
        - elo_change_a_loss: Elo change for A if A loses
        - elo_change_b_win: Elo change for B if B wins
        - elo_change_b_loss: Elo change for B if B loses
    """
    # Use provided K-factors or calculate from match count
    k_a = k_factor_a if k_factor_a is not None else dynamic_k(matches_a)
    k_b = k_factor_b if k_factor_b is not None else dynamic_k(matches_b)

    # Calculate expected scores
    exp_a = expected_score(elo_a, elo_b)
    exp_b = 1 - exp_a  # Expected scores sum to 1

    # Calculate Elo changes for win/loss scenarios
    elo_change_a_win = calculate_elo_change(elo_a, elo_b, 1.0, k_a)
    elo_change_a_loss = calculate_elo_change(elo_a, elo_b, 0.0, k_a)
    elo_change_b_win = calculate_elo_change(elo_b, elo_a, 1.0, k_b)
    elo_change_b_loss = calculate_elo_change(elo_b, elo_a, 0.0, k_b)

    return {
        "expected_a": exp_a,
        "expected_b": exp_b,
        "win_prob_a": exp_a,
        "win_prob_b": exp_b,
        "k_factor_a": k_a,
        "k_factor_b": k_b,
        "elo_change_a_win": elo_change_a_win,
        "elo_change_a_loss": elo_change_a_loss,
        "elo_change_b_win": elo_change_b_win,
        "elo_change_b_loss": elo_change_b_loss,
        "new_elo_a_win": elo_a + elo_change_a_win,
        "new_elo_a_loss": elo_a + elo_change_a_loss,
        "new_elo_b_win": elo_b + elo_change_b_win,
        "new_elo_b_loss": elo_b + elo_change_b_loss
    }


def simulate_single_match(
    elo_a: float,
    elo_b: float,
    max_points: int = 5,
    seed: Optional[int] = None
) -> Tuple[int, int]:
    """
    Simulate a single match between two players based on their Elo ratings.

    The match is simulated as a series of rounds where each round's winner
    is determined by Elo-based probability.

    Args:
        elo_a: Elo rating of player A
        elo_b: Elo rating of player B
        max_points: Points needed to win (default: 5)
        seed: Random seed for reproducibility (optional)

    Returns:
        Tuple of (score_a, score_b)
    """
    if seed is not None:
        random.seed(seed)

    exp_a = expected_score(elo_a, elo_b)

    score_a = 0
    score_b = 0

    while score_a < max_points and score_b < max_points:
        if random.random() < exp_a:
            score_a += 1
        else:
            score_b += 1

    return score_a, score_b


def run_multi_match_simulation(
    elo_a: float,
    elo_b: float,
    num_matches: int,
    matches_a: int = 0,
    matches_b: int = 0,
    k_factor_a: Optional[int] = None,
    k_factor_b: Optional[int] = None,
    max_points: int = 5,
    seed: Optional[int] = None
) -> Dict:
    """
    Run a Monte Carlo simulation of multiple matches between two players.

    Simulates num_matches independent matches and tracks Elo changes over time.
    Each match's K-factor increases based on simulated match count.

    Args:
        elo_a: Starting Elo rating of player A
        elo_b: Starting Elo rating of player B
        num_matches: Number of matches to simulate
        matches_a: Initial match count for player A
        matches_b: Initial match count for player B
        k_factor_a: Fixed K-factor for player A (if None, calculated dynamically)
        k_factor_b: Fixed K-factor for player B (if None, calculated dynamically)
        max_points: Points needed to win each match
        seed: Random seed for reproducibility

    Returns:
        Dictionary containing:
        - elo_progression_a: List of Elo values for A after each match
        - elo_progression_b: List of Elo values for B after each match
        - wins_a: Total wins for player A
        - wins_b: Total wins for player B
        - final_elo_a: Final Elo rating for player A
        - final_elo_b: Final Elo rating for player B
        - elo_changes_a: List of individual Elo changes for A
        - elo_changes_b: List of individual Elo changes for B
        - total_elo_change_a: Sum of all Elo changes for A
        - total_elo_change_b: Sum of all Elo changes for B
        - match_results: List of match outcomes [(score_a, score_b), ...]
    """
    if seed is not None:
        random.seed(seed)

    current_elo_a = elo_a
    current_elo_b = elo_b
    current_matches_a = matches_a
    current_matches_b = matches_b

    elo_progression_a = [current_elo_a]
    elo_progression_b = [current_elo_b]
    elo_changes_a = []
    elo_changes_b = []
    match_results = []
    wins_a = 0
    wins_b = 0

    for _ in range(num_matches):
        # Simulate match
        score_a, score_b = simulate_single_match(current_elo_a, current_elo_b, max_points)
        match_results.append((score_a, score_b))

        # Determine winner
        winner_is_a = score_a > score_b
        if winner_is_a:
            wins_a += 1
            actual_score_a = 1.0
            actual_score_b = 0.0
        else:
            wins_b += 1
            actual_score_a = 0.0
            actual_score_b = 1.0

        # Calculate K-factors
        k_a = k_factor_a if k_factor_a is not None else dynamic_k(current_matches_a)
        k_b = k_factor_b if k_factor_b is not None else dynamic_k(current_matches_b)

        # Calculate Elo changes
        change_a = calculate_elo_change(current_elo_a, current_elo_b, actual_score_a, k_a)
        change_b = calculate_elo_change(current_elo_b, current_elo_a, actual_score_b, k_b)

        elo_changes_a.append(change_a)
        elo_changes_b.append(change_b)

        # Update ratings
        current_elo_a += change_a
        current_elo_b += change_b
        current_matches_a += 1
        current_matches_b += 1

        elo_progression_a.append(current_elo_a)
        elo_progression_b.append(current_elo_b)

    return {
        "elo_progression_a": elo_progression_a,
        "elo_progression_b": elo_progression_b,
        "wins_a": wins_a,
        "wins_b": wins_b,
        "final_elo_a": current_elo_a,
        "final_elo_b": current_elo_b,
        "elo_changes_a": elo_changes_a,
        "elo_changes_b": elo_changes_b,
        "total_elo_change_a": sum(elo_changes_a),
        "total_elo_change_b": sum(elo_changes_b),
        "match_results": match_results
    }


def get_percentile_ranges(
    elo_a: float,
    elo_b: float,
    num_matches: int,
    num_simulations: int = 1000,
    matches_a: int = 0,
    matches_b: int = 0,
    k_factor_a: Optional[int] = None,
    k_factor_b: Optional[int] = None,
    seed: Optional[int] = None
) -> Dict:
    """
    Run multiple simulations to get percentile ranges for Elo outcomes.

    Args:
        elo_a: Starting Elo rating of player A
        elo_b: Starting Elo rating of player B
        num_matches: Number of matches per simulation
        num_simulations: Number of simulations to run (default: 1000)
        matches_a: Initial match count for player A
        matches_b: Initial match count for player B
        k_factor_a: Fixed K-factor for player A (optional)
        k_factor_b: Fixed K-factor for player B (optional)
        seed: Base random seed for reproducibility

    Returns:
        Dictionary containing:
        - final_elos_a: List of final Elo values for A across simulations
        - final_elos_b: List of final Elo values for B across simulations
        - percentiles_a: Dictionary with 5th, 25th, 50th, 75th, 95th percentiles for A
        - percentiles_b: Dictionary with 5th, 25th, 50th, 75th, 95th percentiles for B
        - avg_final_elo_a: Average final Elo for A
        - avg_final_elo_b: Average final Elo for B
        - avg_wins_a: Average wins for A
        - avg_wins_b: Average wins for B
    """
    if seed is not None:
        random.seed(seed)

    final_elos_a = []
    final_elos_b = []
    total_changes_a = []
    total_changes_b = []
    all_wins_a = []
    all_wins_b = []

    for i in range(num_simulations):
        sim_seed = None if seed is None else seed + i
        result = run_multi_match_simulation(
            elo_a, elo_b, num_matches,
            matches_a, matches_b,
            k_factor_a, k_factor_b,
            seed=sim_seed
        )
        final_elos_a.append(result["final_elo_a"])
        final_elos_b.append(result["final_elo_b"])
        total_changes_a.append(result["total_elo_change_a"])
        total_changes_b.append(result["total_elo_change_b"])
        all_wins_a.append(result["wins_a"])
        all_wins_b.append(result["wins_b"])

    # Sort for percentile calculation
    sorted_elos_a = sorted(final_elos_a)
    sorted_elos_b = sorted(final_elos_b)
    sorted_changes_a = sorted(total_changes_a)
    sorted_changes_b = sorted(total_changes_b)

    def get_percentile(sorted_list: List[float], percentile: float) -> float:
        """Get value at given percentile from sorted list."""
        idx = int(len(sorted_list) * percentile / 100)
        idx = min(idx, len(sorted_list) - 1)
        return sorted_list[idx]

    return {
        "final_elos_a": final_elos_a,
        "final_elos_b": final_elos_b,
        "total_changes_a": total_changes_a,
        "total_changes_b": total_changes_b,
        "percentiles_a": {
            "p5": get_percentile(sorted_elos_a, 5),
            "p25": get_percentile(sorted_elos_a, 25),
            "p50": get_percentile(sorted_elos_a, 50),
            "p75": get_percentile(sorted_elos_a, 75),
            "p95": get_percentile(sorted_elos_a, 95)
        },
        "percentiles_b": {
            "p5": get_percentile(sorted_elos_b, 5),
            "p25": get_percentile(sorted_elos_b, 25),
            "p50": get_percentile(sorted_elos_b, 50),
            "p75": get_percentile(sorted_elos_b, 75),
            "p95": get_percentile(sorted_elos_b, 95)
        },
        "change_percentiles_a": {
            "p5": get_percentile(sorted_changes_a, 5),
            "p25": get_percentile(sorted_changes_a, 25),
            "p50": get_percentile(sorted_changes_a, 50),
            "p75": get_percentile(sorted_changes_a, 75),
            "p95": get_percentile(sorted_changes_a, 95)
        },
        "change_percentiles_b": {
            "p5": get_percentile(sorted_changes_b, 5),
            "p25": get_percentile(sorted_changes_b, 25),
            "p50": get_percentile(sorted_changes_b, 50),
            "p75": get_percentile(sorted_changes_b, 75),
            "p95": get_percentile(sorted_changes_b, 95)
        },
        "avg_final_elo_a": sum(final_elos_a) / len(final_elos_a),
        "avg_final_elo_b": sum(final_elos_b) / len(final_elos_b),
        "avg_wins_a": sum(all_wins_a) / len(all_wins_a),
        "avg_wins_b": sum(all_wins_b) / len(all_wins_b)
    }
