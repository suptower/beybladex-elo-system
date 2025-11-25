"""
Unit tests for advanced_stats.py module.
Tests the Power Index (Meta Score) calculation function.
"""
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from advanced_stats import calculate_power_index, POWER_INDEX_WEIGHTS


class TestPowerIndexWeights:
    """Tests for Power Index weight configuration."""

    def test_weights_sum_to_one(self):
        """All weights should sum to 1.0 for a valid composite score."""
        total = sum(POWER_INDEX_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_all_weights_positive(self):
        """All weights should be positive."""
        for weight in POWER_INDEX_WEIGHTS.values():
            assert weight > 0

    def test_required_weight_keys(self):
        """All required weight keys should be present."""
        required_keys = ["elo", "winrate", "trend", "activity", "consistency"]
        for key in required_keys:
            assert key in POWER_INDEX_WEIGHTS


class TestCalculatePowerIndex:
    """Tests for the calculate_power_index function."""

    def test_perfect_stats_high_score(self):
        """Perfect stats should give a high Power Index (close to 100)."""
        # Max ELO, max winrate, max trend, max activity, lowest volatility
        result = calculate_power_index(
            elo=1100, winrate=1.0, trend=100, matches=10, volatility=0,
            max_elo=1100, min_elo=900, max_trend=100, min_trend=-100,
            max_matches=10, max_volatility=20
        )
        assert result > 90  # Should be close to 100

    def test_worst_stats_low_score(self):
        """Worst stats should give a low Power Index (close to 0)."""
        # Min ELO, min winrate, min trend, min activity, highest volatility
        result = calculate_power_index(
            elo=900, winrate=0.0, trend=-100, matches=1, volatility=20,
            max_elo=1100, min_elo=900, max_trend=100, min_trend=-100,
            max_matches=10, max_volatility=20
        )
        assert result < 20  # Should be close to 0

    def test_average_stats_middle_score(self):
        """Average stats should give a medium Power Index (around 50)."""
        result = calculate_power_index(
            elo=1000, winrate=0.5, trend=0, matches=5, volatility=10,
            max_elo=1100, min_elo=900, max_trend=100, min_trend=-100,
            max_matches=10, max_volatility=20
        )
        # With average stats, expect something around 40-60
        assert 30 < result < 70

    def test_score_range(self):
        """Power Index should always be between 0 and 100."""
        test_cases = [
            (1100, 1.0, 100, 10, 0),      # Best case
            (900, 0.0, -100, 1, 20),       # Worst case
            (1000, 0.5, 0, 5, 10),         # Average case
            (1050, 0.75, 50, 8, 5),        # Good case
        ]

        for elo, winrate, trend, matches, volatility in test_cases:
            result = calculate_power_index(
                elo=elo, winrate=winrate, trend=trend, matches=matches,
                volatility=volatility, max_elo=1100, min_elo=900,
                max_trend=100, min_trend=-100, max_matches=10, max_volatility=20
            )
            assert 0 <= result <= 100

    def test_elo_weight_impact(self):
        """Higher ELO should increase Power Index significantly."""
        low_elo = calculate_power_index(
            elo=950, winrate=0.5, trend=0, matches=5, volatility=10,
            max_elo=1100, min_elo=900, max_trend=100, min_trend=-100,
            max_matches=10, max_volatility=20
        )
        high_elo = calculate_power_index(
            elo=1050, winrate=0.5, trend=0, matches=5, volatility=10,
            max_elo=1100, min_elo=900, max_trend=100, min_trend=-100,
            max_matches=10, max_volatility=20
        )
        assert high_elo > low_elo

    def test_winrate_weight_impact(self):
        """Higher winrate should increase Power Index."""
        low_winrate = calculate_power_index(
            elo=1000, winrate=0.2, trend=0, matches=5, volatility=10,
            max_elo=1100, min_elo=900, max_trend=100, min_trend=-100,
            max_matches=10, max_volatility=20
        )
        high_winrate = calculate_power_index(
            elo=1000, winrate=0.8, trend=0, matches=5, volatility=10,
            max_elo=1100, min_elo=900, max_trend=100, min_trend=-100,
            max_matches=10, max_volatility=20
        )
        assert high_winrate > low_winrate

    def test_trend_weight_impact(self):
        """Positive trend should increase Power Index."""
        negative_trend = calculate_power_index(
            elo=1000, winrate=0.5, trend=-50, matches=5, volatility=10,
            max_elo=1100, min_elo=900, max_trend=100, min_trend=-100,
            max_matches=10, max_volatility=20
        )
        positive_trend = calculate_power_index(
            elo=1000, winrate=0.5, trend=50, matches=5, volatility=10,
            max_elo=1100, min_elo=900, max_trend=100, min_trend=-100,
            max_matches=10, max_volatility=20
        )
        assert positive_trend > negative_trend

    def test_activity_weight_impact(self):
        """More matches should increase Power Index."""
        low_activity = calculate_power_index(
            elo=1000, winrate=0.5, trend=0, matches=2, volatility=10,
            max_elo=1100, min_elo=900, max_trend=100, min_trend=-100,
            max_matches=10, max_volatility=20
        )
        high_activity = calculate_power_index(
            elo=1000, winrate=0.5, trend=0, matches=8, volatility=10,
            max_elo=1100, min_elo=900, max_trend=100, min_trend=-100,
            max_matches=10, max_volatility=20
        )
        assert high_activity > low_activity

    def test_consistency_weight_impact(self):
        """Lower volatility (more consistent) should increase Power Index."""
        high_volatility = calculate_power_index(
            elo=1000, winrate=0.5, trend=0, matches=5, volatility=18,
            max_elo=1100, min_elo=900, max_trend=100, min_trend=-100,
            max_matches=10, max_volatility=20
        )
        low_volatility = calculate_power_index(
            elo=1000, winrate=0.5, trend=0, matches=5, volatility=2,
            max_elo=1100, min_elo=900, max_trend=100, min_trend=-100,
            max_matches=10, max_volatility=20
        )
        assert low_volatility > high_volatility

    def test_same_elo_range_edge_case(self):
        """Handle case where max_elo equals min_elo."""
        result = calculate_power_index(
            elo=1000, winrate=0.5, trend=0, matches=5, volatility=10,
            max_elo=1000, min_elo=1000, max_trend=100, min_trend=-100,
            max_matches=10, max_volatility=20
        )
        # Should handle division by zero gracefully
        assert 0 <= result <= 100

    def test_same_trend_range_edge_case(self):
        """Handle case where max_trend equals min_trend."""
        result = calculate_power_index(
            elo=1000, winrate=0.5, trend=0, matches=5, volatility=10,
            max_elo=1100, min_elo=900, max_trend=0, min_trend=0,
            max_matches=10, max_volatility=20
        )
        # Should handle division by zero gracefully
        assert 0 <= result <= 100

    def test_zero_max_matches_edge_case(self):
        """Handle case where max_matches is zero."""
        result = calculate_power_index(
            elo=1000, winrate=0.5, trend=0, matches=0, volatility=10,
            max_elo=1100, min_elo=900, max_trend=100, min_trend=-100,
            max_matches=0, max_volatility=20
        )
        # Should handle division by zero gracefully
        assert 0 <= result <= 100

    def test_zero_max_volatility_edge_case(self):
        """Handle case where max_volatility is zero."""
        result = calculate_power_index(
            elo=1000, winrate=0.5, trend=0, matches=5, volatility=0,
            max_elo=1100, min_elo=900, max_trend=100, min_trend=-100,
            max_matches=10, max_volatility=0
        )
        # Should handle division by zero gracefully
        assert 0 <= result <= 100
