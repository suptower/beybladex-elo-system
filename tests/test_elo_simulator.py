"""
Unit tests for elo_simulator.py module.
Tests the Elo simulation functions including expected scores,
match outcomes, single match simulation, and multi-match Monte Carlo simulations.
"""
import sys
import os
import random

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from elo_simulator import (
    dynamic_k,
    expected_score,
    calculate_elo_change,
    calculate_match_outcomes,
    simulate_single_match,
    run_multi_match_simulation,
    get_percentile_ranges,
    K_LEARNING,
    K_INTERMEDIATE,
    K_EXPERIENCED
)


class TestDynamicK:
    """Tests for the dynamic_k function."""

    def test_k_factor_learning_phase(self):
        """K-factor should be 40 for players with fewer than 6 matches."""
        assert dynamic_k(0) == K_LEARNING
        assert dynamic_k(1) == K_LEARNING
        assert dynamic_k(5) == K_LEARNING

    def test_k_factor_intermediate_phase(self):
        """K-factor should be 24 for players with 6-14 matches."""
        assert dynamic_k(6) == K_INTERMEDIATE
        assert dynamic_k(10) == K_INTERMEDIATE
        assert dynamic_k(14) == K_INTERMEDIATE

    def test_k_factor_experienced_phase(self):
        """K-factor should be 12 for players with 15+ matches."""
        assert dynamic_k(15) == K_EXPERIENCED
        assert dynamic_k(50) == K_EXPERIENCED
        assert dynamic_k(100) == K_EXPERIENCED


class TestExpectedScore:
    """Tests for the expected_score function."""

    def test_equal_ratings(self):
        """Equal ratings should give 0.5 expected score."""
        assert expected_score(1000, 1000) == 0.5
        assert expected_score(1500, 1500) == 0.5

    def test_higher_rating_favored(self):
        """Higher rated player should have expected score > 0.5."""
        result = expected_score(1200, 1000)
        assert result > 0.5
        assert result < 1.0

    def test_lower_rating_unfavored(self):
        """Lower rated player should have expected score < 0.5."""
        result = expected_score(1000, 1200)
        assert result < 0.5
        assert result > 0.0

    def test_400_point_difference(self):
        """400 point difference should give approximately 10:1 odds."""
        result = expected_score(1400, 1000)
        # 1 / (1 + 10^1) ≈ 0.909
        assert abs(result - 0.909) < 0.01

    def test_symmetry(self):
        """Expected scores of opponents should sum to 1."""
        e_a = expected_score(1200, 1000)
        e_b = expected_score(1000, 1200)
        assert abs(e_a + e_b - 1.0) < 0.0001


class TestCalculateEloChange:
    """Tests for the calculate_elo_change function."""

    def test_win_increases_elo(self):
        """Winning should result in positive Elo change."""
        change = calculate_elo_change(1000, 1000, 1.0, K_LEARNING)
        assert change > 0

    def test_loss_decreases_elo(self):
        """Losing should result in negative Elo change."""
        change = calculate_elo_change(1000, 1000, 0.0, K_LEARNING)
        assert change < 0

    def test_equal_ratings_win(self):
        """Equal ratings win should give K/2 points."""
        change = calculate_elo_change(1000, 1000, 1.0, K_LEARNING)
        assert abs(change - K_LEARNING * 0.5) < 0.01

    def test_equal_ratings_loss(self):
        """Equal ratings loss should lose K/2 points."""
        change = calculate_elo_change(1000, 1000, 0.0, K_LEARNING)
        assert abs(change - (-K_LEARNING * 0.5)) < 0.01

    def test_upset_win_gives_more_points(self):
        """Winning as underdog should give more than K/2 points."""
        change = calculate_elo_change(1000, 1200, 1.0, K_LEARNING)
        # Expected score is less than 0.5, so win gives more than K/2
        assert change > K_LEARNING * 0.5

    def test_expected_win_gives_fewer_points(self):
        """Winning as favorite should give less than K/2 points."""
        change = calculate_elo_change(1200, 1000, 1.0, K_LEARNING)
        # Expected score is more than 0.5, so win gives less than K/2
        assert change < K_LEARNING * 0.5
        assert change > 0


class TestCalculateMatchOutcomes:
    """Tests for the calculate_match_outcomes function."""

    def test_returns_all_expected_keys(self):
        """Function should return all expected keys."""
        result = calculate_match_outcomes(1000, 1000)
        expected_keys = [
            "expected_a", "expected_b", "win_prob_a", "win_prob_b",
            "k_factor_a", "k_factor_b",
            "elo_change_a_win", "elo_change_a_loss",
            "elo_change_b_win", "elo_change_b_loss",
            "new_elo_a_win", "new_elo_a_loss",
            "new_elo_b_win", "new_elo_b_loss"
        ]
        for key in expected_keys:
            assert key in result

    def test_equal_ratings_equal_probabilities(self):
        """Equal ratings should give equal win probabilities."""
        result = calculate_match_outcomes(1000, 1000)
        assert abs(result["win_prob_a"] - 0.5) < 0.01
        assert abs(result["win_prob_b"] - 0.5) < 0.01

    def test_k_factor_override(self):
        """Custom K-factors should be used when provided."""
        result = calculate_match_outcomes(1000, 1000, k_factor_a=50, k_factor_b=30)
        assert result["k_factor_a"] == 50
        assert result["k_factor_b"] == 30

    def test_k_factor_from_matches(self):
        """K-factors should be calculated from match count when not provided."""
        result = calculate_match_outcomes(1000, 1000, matches_a=0, matches_b=20)
        assert result["k_factor_a"] == K_LEARNING
        assert result["k_factor_b"] == K_EXPERIENCED

    def test_win_loss_elo_opposite_signs(self):
        """Win Elo change should be positive, loss should be negative."""
        result = calculate_match_outcomes(1000, 1000)
        assert result["elo_change_a_win"] > 0
        assert result["elo_change_a_loss"] < 0
        assert result["elo_change_b_win"] > 0
        assert result["elo_change_b_loss"] < 0

    def test_new_elo_calculations(self):
        """New Elo values should equal base + change."""
        result = calculate_match_outcomes(1000, 1100)
        assert abs(result["new_elo_a_win"] - (1000 + result["elo_change_a_win"])) < 0.01
        assert abs(result["new_elo_a_loss"] - (1000 + result["elo_change_a_loss"])) < 0.01


class TestSimulateSingleMatch:
    """Tests for the simulate_single_match function."""

    def test_returns_valid_scores(self):
        """Match should return valid score tuple."""
        random.seed(42)
        score_a, score_b = simulate_single_match(1000, 1000)
        assert isinstance(score_a, int)
        assert isinstance(score_b, int)
        assert score_a >= 0
        assert score_b >= 0

    def test_one_player_reaches_max_points(self):
        """One player should reach max_points."""
        random.seed(42)
        score_a, score_b = simulate_single_match(1000, 1000, max_points=5)
        assert score_a == 5 or score_b == 5
        if score_a == 5:
            assert score_b < 5
        else:
            assert score_a < 5

    def test_custom_max_points(self):
        """Custom max_points should be respected."""
        random.seed(42)
        score_a, score_b = simulate_single_match(1000, 1000, max_points=3)
        assert max(score_a, score_b) == 3

    def test_deterministic_with_seed(self):
        """Same seed should produce same results."""
        result1 = simulate_single_match(1000, 1000, seed=123)
        result2 = simulate_single_match(1000, 1000, seed=123)
        assert result1 == result2

    def test_higher_elo_wins_more_often(self):
        """Higher Elo player should win more often over many matches."""
        random.seed(42)
        wins_high = 0
        wins_low = 0

        for i in range(100):
            score_a, score_b = simulate_single_match(1400, 1000, seed=42 + i)
            if score_a > score_b:
                wins_high += 1
            else:
                wins_low += 1

        assert wins_high > wins_low


class TestRunMultiMatchSimulation:
    """Tests for the run_multi_match_simulation function."""

    def test_returns_all_expected_keys(self):
        """Function should return all expected keys."""
        result = run_multi_match_simulation(1000, 1000, 5, seed=42)
        expected_keys = [
            "elo_progression_a", "elo_progression_b",
            "wins_a", "wins_b",
            "final_elo_a", "final_elo_b",
            "elo_changes_a", "elo_changes_b",
            "total_elo_change_a", "total_elo_change_b",
            "match_results"
        ]
        for key in expected_keys:
            assert key in result

    def test_correct_number_of_matches(self):
        """Should simulate correct number of matches."""
        result = run_multi_match_simulation(1000, 1000, 10, seed=42)
        assert len(result["match_results"]) == 10
        assert len(result["elo_changes_a"]) == 10
        assert len(result["elo_changes_b"]) == 10

    def test_elo_progression_length(self):
        """Elo progression should have n+1 entries (initial + after each match)."""
        result = run_multi_match_simulation(1000, 1000, 10, seed=42)
        assert len(result["elo_progression_a"]) == 11
        assert len(result["elo_progression_b"]) == 11

    def test_wins_sum_to_total_matches(self):
        """Total wins should equal number of matches."""
        result = run_multi_match_simulation(1000, 1000, 10, seed=42)
        assert result["wins_a"] + result["wins_b"] == 10

    def test_deterministic_with_seed(self):
        """Same seed should produce same results."""
        result1 = run_multi_match_simulation(1000, 1000, 5, seed=123)
        result2 = run_multi_match_simulation(1000, 1000, 5, seed=123)
        assert result1["wins_a"] == result2["wins_a"]
        assert result1["final_elo_a"] == result2["final_elo_a"]

    def test_final_elo_equals_progression_last(self):
        """Final Elo should equal last value in progression."""
        result = run_multi_match_simulation(1000, 1000, 10, seed=42)
        assert result["final_elo_a"] == result["elo_progression_a"][-1]
        assert result["final_elo_b"] == result["elo_progression_b"][-1]

    def test_total_change_equals_sum_of_changes(self):
        """Total Elo change should equal sum of individual changes."""
        result = run_multi_match_simulation(1000, 1000, 10, seed=42)
        assert abs(result["total_elo_change_a"] - sum(result["elo_changes_a"])) < 0.01
        assert abs(result["total_elo_change_b"] - sum(result["elo_changes_b"])) < 0.01


class TestGetPercentileRanges:
    """Tests for the get_percentile_ranges function."""

    def test_returns_all_expected_keys(self):
        """Function should return all expected keys."""
        result = get_percentile_ranges(1000, 1000, 5, num_simulations=10, seed=42)
        expected_keys = [
            "final_elos_a", "final_elos_b",
            "total_changes_a", "total_changes_b",
            "percentiles_a", "percentiles_b",
            "change_percentiles_a", "change_percentiles_b",
            "avg_final_elo_a", "avg_final_elo_b",
            "avg_wins_a", "avg_wins_b"
        ]
        for key in expected_keys:
            assert key in result

    def test_correct_number_of_simulations(self):
        """Should run correct number of simulations."""
        result = get_percentile_ranges(1000, 1000, 5, num_simulations=50, seed=42)
        assert len(result["final_elos_a"]) == 50
        assert len(result["final_elos_b"]) == 50

    def test_percentiles_structure(self):
        """Percentiles should have expected keys."""
        result = get_percentile_ranges(1000, 1000, 5, num_simulations=100, seed=42)
        percentile_keys = ["p5", "p25", "p50", "p75", "p95"]
        for key in percentile_keys:
            assert key in result["percentiles_a"]
            assert key in result["percentiles_b"]

    def test_percentiles_ordered(self):
        """Percentiles should be in ascending order."""
        result = get_percentile_ranges(1000, 1000, 10, num_simulations=100, seed=42)
        p = result["percentiles_a"]
        assert p["p5"] <= p["p25"] <= p["p50"] <= p["p75"] <= p["p95"]

    def test_deterministic_with_seed(self):
        """Same seed should produce same results."""
        result1 = get_percentile_ranges(1000, 1000, 5, num_simulations=20, seed=123)
        result2 = get_percentile_ranges(1000, 1000, 5, num_simulations=20, seed=123)
        assert result1["avg_final_elo_a"] == result2["avg_final_elo_a"]
        assert result1["percentiles_a"]["p50"] == result2["percentiles_a"]["p50"]

    def test_average_elo_reasonable(self):
        """Average Elo should be close to starting for equal players."""
        result = get_percentile_ranges(1000, 1000, 10, num_simulations=500, seed=42)
        # For equal players, average should stay near starting Elo
        assert abs(result["avg_final_elo_a"] - 1000) < 50
        assert abs(result["avg_final_elo_b"] - 1000) < 50

    def test_average_wins_reasonable(self):
        """Average wins should be close to half for equal players."""
        result = get_percentile_ranges(1000, 1000, 10, num_simulations=500, seed=42)
        # For equal players, each should win ~50% of matches
        assert abs(result["avg_wins_a"] - 5) < 1
        assert abs(result["avg_wins_b"] - 5) < 1
