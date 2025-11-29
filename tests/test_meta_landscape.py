"""
Unit tests for meta_landscape.py module.
Tests the offense/defense score calculation functions.
"""
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'visualization'))

from meta_landscape import (
    calculate_offense_score,
    calculate_defense_score,
    OFFENSE_WEIGHTS,
    DEFENSE_WEIGHTS,
)


class TestOffenseWeights:
    """Tests for offense weight configuration."""

    def test_offense_weights_sum_to_one(self):
        """Offense weights should sum to 1.0."""
        total = sum(OFFENSE_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_all_weights_positive(self):
        """All offense weights should be positive."""
        for weight in OFFENSE_WEIGHTS.values():
            assert weight > 0

    def test_required_weight_keys(self):
        """Offense weights should have all required keys."""
        required_keys = [
            "burst_finish_rate",
            "pocket_finish_rate",
            "extreme_finish_rate",
            "offensive_point_efficiency",
            "opening_dominance",
        ]
        for key in required_keys:
            assert key in OFFENSE_WEIGHTS


class TestDefenseWeights:
    """Tests for defense weight configuration."""

    def test_defense_weights_sum_to_one(self):
        """Defense weights should sum to 1.0."""
        total = sum(DEFENSE_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_all_weights_positive(self):
        """All defense weights should be positive."""
        for weight in DEFENSE_WEIGHTS.values():
            assert weight > 0

    def test_required_weight_keys(self):
        """Defense weights should have all required keys."""
        required_keys = [
            "burst_resistance",
            "pocket_resistance",
            "extreme_resistance",
            "defensive_conversion",
        ]
        for key in required_keys:
            assert key in DEFENSE_WEIGHTS


class TestCalculateOffenseScore:
    """Tests for the calculate_offense_score function."""

    def test_high_offense_metrics(self):
        """High attack metrics should produce high offense score."""
        metrics = {
            "burst_finish_rate": 0.8,
            "pocket_finish_rate": 0.5,
            "extreme_finish_rate": 0.6,
            "offensive_point_efficiency": 2.0,
            "opening_dominance": 0.9,
        }
        result = calculate_offense_score(metrics)
        assert 3.0 <= result <= 5.0

    def test_low_offense_metrics(self):
        """Low attack metrics should produce low offense score."""
        metrics = {
            "burst_finish_rate": 0.0,
            "pocket_finish_rate": 0.0,
            "extreme_finish_rate": 0.0,
            "offensive_point_efficiency": 1.0,
            "opening_dominance": 0.0,
        }
        result = calculate_offense_score(metrics)
        assert 0.0 <= result <= 1.5

    def test_score_range(self):
        """Offense score should be between 0 and 5."""
        metrics = {
            "burst_finish_rate": 0.3,
            "pocket_finish_rate": 0.2,
            "extreme_finish_rate": 0.1,
            "offensive_point_efficiency": 1.5,
            "opening_dominance": 0.5,
        }
        result = calculate_offense_score(metrics)
        assert 0.0 <= result <= 5.0

    def test_empty_metrics(self):
        """Empty metrics should return low score."""
        result = calculate_offense_score({})
        assert 0.0 <= result <= 1.0

    def test_max_possible_score(self):
        """Maximum metrics should approach max score."""
        metrics = {
            "burst_finish_rate": 1.0,
            "pocket_finish_rate": 1.0,
            "extreme_finish_rate": 1.0,
            "offensive_point_efficiency": 2.5,
            "opening_dominance": 1.0,
        }
        result = calculate_offense_score(metrics)
        assert 4.0 <= result <= 5.0


class TestCalculateDefenseScore:
    """Tests for the calculate_defense_score function."""

    def test_high_defense_metrics(self):
        """High defense metrics should produce high defense score."""
        metrics = {
            "burst_resistance": 1.0,
            "pocket_resistance": 1.0,
            "extreme_resistance": 1.0,
            "defensive_conversion": 0.8,
        }
        result = calculate_defense_score(metrics)
        assert 4.0 <= result <= 5.0

    def test_low_defense_metrics(self):
        """Low defense metrics should produce low defense score."""
        metrics = {
            "burst_resistance": 0.2,
            "pocket_resistance": 0.2,
            "extreme_resistance": 0.2,
            "defensive_conversion": 0.1,
        }
        result = calculate_defense_score(metrics)
        assert 0.0 <= result <= 1.5

    def test_score_range(self):
        """Defense score should be between 0 and 5."""
        metrics = {
            "burst_resistance": 0.7,
            "pocket_resistance": 0.6,
            "extreme_resistance": 0.8,
            "defensive_conversion": 0.5,
        }
        result = calculate_defense_score(metrics)
        assert 0.0 <= result <= 5.0

    def test_empty_metrics(self):
        """Empty metrics should return score of 0."""
        result = calculate_defense_score({})
        assert result == 0.0

    def test_perfect_resistance(self):
        """Perfect resistance metrics should give high score."""
        metrics = {
            "burst_resistance": 1.0,
            "pocket_resistance": 1.0,
            "extreme_resistance": 1.0,
            "defensive_conversion": 1.0,
        }
        result = calculate_defense_score(metrics)
        assert result == 5.0


class TestScoreSymmetry:
    """Tests for score calculation symmetry."""

    def test_balanced_build(self):
        """Balanced metrics should give similar offense and defense scores."""
        attack_metrics = {
            "burst_finish_rate": 0.5,
            "pocket_finish_rate": 0.5,
            "extreme_finish_rate": 0.5,
            "offensive_point_efficiency": 1.75,
            "opening_dominance": 0.5,
        }
        defense_metrics = {
            "burst_resistance": 0.5,
            "pocket_resistance": 0.5,
            "extreme_resistance": 0.5,
            "defensive_conversion": 0.5,
        }
        offense = calculate_offense_score(attack_metrics)
        defense = calculate_defense_score(defense_metrics)
        # Both should be around 2.5 (middle of range)
        assert 2.0 <= offense <= 3.5
        assert 2.0 <= defense <= 3.0
