"""
Unit tests for rpg_stats.py module.
Tests the RPG-style stat bar calculation functions.
"""
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from rpg_stats import (
    percentile_normalize,
    minmax_normalize,
    clamp,
    calculate_attack_stat,
    calculate_defense_stat,
    calculate_stamina_stat,
    calculate_control_stat,
    calculate_meta_impact_stat,
    ATTACK_WEIGHTS,
    DEFENSE_WEIGHTS,
    STAMINA_WEIGHTS,
    CONTROL_WEIGHTS,
    META_IMPACT_WEIGHTS,
)


class TestStatWeights:
    """Tests for stat weight configuration."""

    def test_attack_weights_sum_to_one(self):
        """Attack weights should sum to 1.0."""
        total = sum(ATTACK_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_defense_weights_sum_to_one(self):
        """Defense weights should sum to 1.0."""
        total = sum(DEFENSE_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_stamina_weights_sum_to_one(self):
        """Stamina weights should sum to 1.0."""
        total = sum(STAMINA_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_control_weights_sum_to_one(self):
        """Control weights should sum to 1.0."""
        total = sum(CONTROL_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_meta_impact_weights_sum_to_one(self):
        """Meta Impact weights should sum to 1.0."""
        total = sum(META_IMPACT_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_all_weights_positive(self):
        """All weights should be positive."""
        all_weights = [
            ATTACK_WEIGHTS,
            DEFENSE_WEIGHTS,
            STAMINA_WEIGHTS,
            CONTROL_WEIGHTS,
            META_IMPACT_WEIGHTS,
        ]
        for weights in all_weights:
            for weight in weights.values():
                assert weight > 0


class TestPercentileNormalize:
    """Tests for the percentile_normalize function."""

    def test_lowest_value(self):
        """Lowest value should get 0.0."""
        values = [1, 2, 3, 4, 5]
        result = percentile_normalize(1, values)
        assert result == 0.0

    def test_highest_value(self):
        """Highest value should get 1.0."""
        values = [1, 2, 3, 4, 5]
        result = percentile_normalize(5, values)
        assert result == 1.0

    def test_middle_value(self):
        """Middle value should get ~0.5."""
        values = [1, 2, 3, 4, 5]
        result = percentile_normalize(3, values)
        assert 0.4 <= result <= 0.6

    def test_empty_list(self):
        """Empty list should return 0.5."""
        result = percentile_normalize(5, [])
        assert result == 0.5

    def test_single_value(self):
        """Single value list should return 0.5."""
        result = percentile_normalize(5, [5])
        assert result == 0.5

    def test_result_range(self):
        """Result should always be between 0 and 1."""
        values = [10, 20, 30, 40, 50]
        for v in values:
            result = percentile_normalize(v, values)
            assert 0.0 <= result <= 1.0


class TestMinmaxNormalize:
    """Tests for the minmax_normalize function."""

    def test_min_value(self):
        """Minimum value should return 0.0."""
        result = minmax_normalize(0, 0, 100)
        assert result == 0.0

    def test_max_value(self):
        """Maximum value should return 1.0."""
        result = minmax_normalize(100, 0, 100)
        assert result == 1.0

    def test_middle_value(self):
        """Middle value should return 0.5."""
        result = minmax_normalize(50, 0, 100)
        assert result == 0.5

    def test_same_min_max(self):
        """Same min and max should return 0.5."""
        result = minmax_normalize(50, 50, 50)
        assert result == 0.5

    def test_value_below_min(self):
        """Value below min should return 0.0 (clamped)."""
        result = minmax_normalize(-10, 0, 100)
        assert result == 0.0

    def test_value_above_max(self):
        """Value above max should return 1.0 (clamped)."""
        result = minmax_normalize(150, 0, 100)
        assert result == 1.0


class TestClamp:
    """Tests for the clamp function."""

    def test_value_in_range(self):
        """Value in range should be unchanged."""
        assert clamp(3.0) == 3.0

    def test_value_below_min(self):
        """Value below min should be clamped to min."""
        assert clamp(-1.0) == 0.0

    def test_value_above_max(self):
        """Value above max should be clamped to max."""
        assert clamp(6.0) == 5.0

    def test_custom_range(self):
        """Custom range should work correctly."""
        assert clamp(50, 0, 100) == 50
        assert clamp(-10, 0, 100) == 0
        assert clamp(150, 0, 100) == 100


class TestCalculateAttackStat:
    """Tests for the calculate_attack_stat function."""

    def test_high_attack_metrics(self):
        """High attack metrics should produce high attack stat."""
        metrics = {
            "burst_finish_rate": 0.5,
            "pocket_finish_rate": 0.3,
            "extreme_finish_rate": 0.2,
            "offensive_point_efficiency": 2.0,
            "opening_dominance": 0.8,
        }
        all_metrics = [
            metrics,
            {
                "burst_finish_rate": 0.1,
                "pocket_finish_rate": 0.1,
                "extreme_finish_rate": 0.0,
                "offensive_point_efficiency": 1.0,
                "opening_dominance": 0.2,
            },
        ]
        result = calculate_attack_stat(metrics, all_metrics)
        assert 3.0 <= result <= 5.0

    def test_low_attack_metrics(self):
        """Low attack metrics should produce low attack stat."""
        metrics = {
            "burst_finish_rate": 0.0,
            "pocket_finish_rate": 0.0,
            "extreme_finish_rate": 0.0,
            "offensive_point_efficiency": 1.0,
            "opening_dominance": 0.0,
        }
        all_metrics = [
            metrics,
            {
                "burst_finish_rate": 0.5,
                "pocket_finish_rate": 0.3,
                "extreme_finish_rate": 0.2,
                "offensive_point_efficiency": 2.0,
                "opening_dominance": 0.8,
            },
        ]
        result = calculate_attack_stat(metrics, all_metrics)
        assert 0.0 <= result <= 2.0

    def test_stat_range(self):
        """Attack stat should be between 0 and 5."""
        metrics = {
            "burst_finish_rate": 0.3,
            "pocket_finish_rate": 0.2,
            "extreme_finish_rate": 0.1,
            "offensive_point_efficiency": 1.5,
            "opening_dominance": 0.5,
        }
        all_metrics = [metrics]
        result = calculate_attack_stat(metrics, all_metrics)
        assert 0.0 <= result <= 5.0


class TestCalculateDefenseStat:
    """Tests for the calculate_defense_stat function."""

    def test_high_defense_metrics(self):
        """High defense metrics should produce high defense stat."""
        metrics = {
            "burst_resistance": 1.0,
            "pocket_resistance": 1.0,
            "extreme_resistance": 1.0,
            "defensive_conversion": 0.8,
        }
        all_metrics = [
            metrics,
            {
                "burst_resistance": 0.5,
                "pocket_resistance": 0.5,
                "extreme_resistance": 0.5,
                "defensive_conversion": 0.2,
            },
        ]
        result = calculate_defense_stat(metrics, all_metrics)
        assert 3.0 <= result <= 5.0

    def test_stat_range(self):
        """Defense stat should be between 0 and 5."""
        metrics = {
            "burst_resistance": 0.7,
            "pocket_resistance": 0.7,
            "extreme_resistance": 0.8,
            "defensive_conversion": 0.5,
        }
        all_metrics = [metrics]
        result = calculate_defense_stat(metrics, all_metrics)
        assert 0.0 <= result <= 5.0


class TestCalculateStaminaStat:
    """Tests for the calculate_stamina_stat function."""

    def test_high_stamina_metrics(self):
        """High stamina metrics should produce high stamina stat."""
        metrics = {
            "spin_finish_win_rate": 0.8,
            "spin_differential_index": 0.9,
            "long_round_win_rate": 0.8,
        }
        all_metrics = [
            metrics,
            {
                "spin_finish_win_rate": 0.2,
                "spin_differential_index": 0.3,
                "long_round_win_rate": 0.3,
            },
        ]
        result = calculate_stamina_stat(metrics, all_metrics)
        assert 3.0 <= result <= 5.0

    def test_stat_range(self):
        """Stamina stat should be between 0 and 5."""
        metrics = {
            "spin_finish_win_rate": 0.5,
            "spin_differential_index": 0.5,
            "long_round_win_rate": 0.5,
        }
        all_metrics = [metrics]
        result = calculate_stamina_stat(metrics, all_metrics)
        assert 0.0 <= result <= 5.0


class TestCalculateControlStat:
    """Tests for the calculate_control_stat function."""

    def test_high_control_metrics(self):
        """High control metrics should produce high control stat."""
        metrics = {
            "volatility_inverse": 0.9,
            "first_contact_advantage": 0.9,
            "match_flow_stability": 0.9,
        }
        all_metrics = [
            metrics,
            {
                "volatility_inverse": 0.3,
                "first_contact_advantage": 0.3,
                "match_flow_stability": 0.3,
            },
        ]
        result = calculate_control_stat(metrics, all_metrics)
        assert 3.0 <= result <= 5.0

    def test_stat_range(self):
        """Control stat should be between 0 and 5."""
        metrics = {
            "volatility_inverse": 0.5,
            "first_contact_advantage": 0.5,
            "match_flow_stability": 0.5,
        }
        all_metrics = [metrics]
        result = calculate_control_stat(metrics, all_metrics)
        assert 0.0 <= result <= 5.0


class TestCalculateMetaImpactStat:
    """Tests for the calculate_meta_impact_stat function."""

    def test_high_meta_metrics(self):
        """High meta metrics should produce high meta impact stat."""
        metrics = {
            "elo_normalized": 0.95,
            "elo_per_match": 8.0,
            "upset_rate": 0.5,
            "matchup_spread": 0.8,
            "anti_meta_score": 0.8,
        }
        all_metrics = [
            metrics,
            {
                "elo_normalized": 0.3,
                "elo_per_match": -2.0,
                "upset_rate": 0.0,
                "matchup_spread": 0.2,
                "anti_meta_score": 0.2,
            },
        ]
        result = calculate_meta_impact_stat(metrics, all_metrics)
        assert 3.0 <= result <= 5.0

    def test_stat_range(self):
        """Meta impact stat should be between 0 and 5."""
        metrics = {
            "elo_normalized": 0.5,
            "elo_per_match": 0.0,
            "upset_rate": 0.2,
            "matchup_spread": 0.5,
            "anti_meta_score": 0.5,
        }
        all_metrics = [metrics]
        result = calculate_meta_impact_stat(metrics, all_metrics)
        assert 0.0 <= result <= 5.0
