"""
Unit tests for upset_analysis.py module.
Tests the Giant Killer Score calculation and upset analysis functions.
"""
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from upset_analysis import (
    calculate_giant_killer_score,
    GIANT_KILLER_WEIGHTS,
    analyze_upsets,
    calculate_analysis_metrics,
    calculate_giant_killer_scores
)


class TestGiantKillerWeights:
    """Tests for Giant Killer Score weight configuration."""

    def test_weights_sum_to_one(self):
        """All weights should sum to 1.0 for a valid composite score."""
        total = sum(GIANT_KILLER_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_all_weights_positive(self):
        """All weights should be positive."""
        for weight in GIANT_KILLER_WEIGHTS.values():
            assert weight > 0

    def test_required_weight_keys(self):
        """All required weight keys should be present."""
        required_keys = ["upset_winrate", "upset_frequency", "avg_magnitude", "total_upsets"]
        for key in required_keys:
            assert key in GIANT_KILLER_WEIGHTS


class TestCalculateGiantKillerScore:
    """Tests for the calculate_giant_killer_score function."""

    def test_perfect_giant_killer_high_score(self):
        """Perfect giant killer stats should give a high score."""
        # All wins are upsets, high frequency, high magnitude
        result = calculate_giant_killer_score(
            upset_wins=10,
            total_wins=10,
            total_matches=10,
            avg_magnitude=100,
            max_upset_wins=10,
            max_magnitude=100
        )
        assert result > 90  # Should be close to 100

    def test_no_upsets_zero_score(self):
        """A Bey with no upset wins should have zero Giant Killer score."""
        result = calculate_giant_killer_score(
            upset_wins=0,
            total_wins=10,
            total_matches=10,
            avg_magnitude=0,
            max_upset_wins=10,
            max_magnitude=100
        )
        assert result == 0.0

    def test_score_range(self):
        """Giant Killer Score should always be between 0 and 100."""
        test_cases = [
            (10, 10, 10, 100),  # Best case
            (0, 10, 10, 0),     # Worst case (no upsets)
            (5, 10, 20, 50),    # Average case
            (3, 5, 10, 75),     # Good upset rate
        ]

        for upset_wins, total_wins, total_matches, avg_magnitude in test_cases:
            result = calculate_giant_killer_score(
                upset_wins=upset_wins,
                total_wins=total_wins,
                total_matches=total_matches,
                avg_magnitude=avg_magnitude,
                max_upset_wins=10,
                max_magnitude=100
            )
            assert 0 <= result <= 100

    def test_upset_winrate_impact(self):
        """Higher upset win rate should increase Giant Killer Score."""
        low_rate = calculate_giant_killer_score(
            upset_wins=2,
            total_wins=10,
            total_matches=10,
            avg_magnitude=50,
            max_upset_wins=10,
            max_magnitude=100
        )
        high_rate = calculate_giant_killer_score(
            upset_wins=8,
            total_wins=10,
            total_matches=10,
            avg_magnitude=50,
            max_upset_wins=10,
            max_magnitude=100
        )
        assert high_rate > low_rate

    def test_magnitude_impact(self):
        """Higher average magnitude should increase Giant Killer Score."""
        low_magnitude = calculate_giant_killer_score(
            upset_wins=5,
            total_wins=10,
            total_matches=10,
            avg_magnitude=20,
            max_upset_wins=10,
            max_magnitude=100
        )
        high_magnitude = calculate_giant_killer_score(
            upset_wins=5,
            total_wins=10,
            total_matches=10,
            avg_magnitude=80,
            max_upset_wins=10,
            max_magnitude=100
        )
        assert high_magnitude > low_magnitude

    def test_zero_total_wins_edge_case(self):
        """Handle case where total_wins is zero."""
        result = calculate_giant_killer_score(
            upset_wins=0,
            total_wins=0,
            total_matches=10,
            avg_magnitude=0,
            max_upset_wins=10,
            max_magnitude=100
        )
        # Should handle division by zero gracefully
        assert 0 <= result <= 100

    def test_zero_total_matches_edge_case(self):
        """Handle case where total_matches is zero."""
        result = calculate_giant_killer_score(
            upset_wins=0,
            total_wins=0,
            total_matches=0,
            avg_magnitude=0,
            max_upset_wins=10,
            max_magnitude=100
        )
        # Should handle division by zero gracefully
        assert 0 <= result <= 100

    def test_zero_max_values_edge_case(self):
        """Handle case where max normalization values are zero."""
        result = calculate_giant_killer_score(
            upset_wins=5,
            total_wins=10,
            total_matches=10,
            avg_magnitude=50,
            max_upset_wins=0,
            max_magnitude=0
        )
        # Should handle division by zero gracefully
        assert 0 <= result <= 100


class TestAnalyzeUpsets:
    """Tests for the analyze_upsets function using real data."""

    def test_analyze_upsets_returns_data(self):
        """analyze_upsets should return bey_stats and upset_matches."""
        bey_stats, upset_matches = analyze_upsets()

        assert isinstance(bey_stats, dict)
        assert isinstance(upset_matches, list)
        assert len(bey_stats) > 0
        assert len(upset_matches) > 0

    def test_upset_match_structure(self):
        """Each upset match should have required fields."""
        _, upset_matches = analyze_upsets()

        required_fields = [
            "date", "winner", "loser", "winner_pre_elo",
            "loser_pre_elo", "elo_difference", "score"
        ]

        for match in upset_matches:
            for field in required_fields:
                assert field in match, f"Missing field: {field}"

    def test_upset_elo_difference_positive(self):
        """Upset ELO difference should always be positive (loser had higher ELO)."""
        _, upset_matches = analyze_upsets()

        for match in upset_matches:
            assert match["elo_difference"] > 0
            assert match["loser_pre_elo"] > match["winner_pre_elo"]

    def test_bey_stats_structure(self):
        """Each bey's stats should have required fields."""
        bey_stats, _ = analyze_upsets()

        required_fields = [
            "matches", "wins", "losses", "upset_wins", "upset_losses",
            "upset_win_magnitudes", "upset_loss_magnitudes",
            "biggest_upset_win", "biggest_upset_loss", "last_elo"
        ]

        for bey, stats in bey_stats.items():
            for field in required_fields:
                assert field in stats, f"Missing field: {field} for bey {bey}"


class TestCalculateAnalysisMetrics:
    """Tests for the calculate_analysis_metrics function."""

    def test_metrics_structure(self):
        """Calculated metrics should have required fields."""
        bey_stats, _ = analyze_upsets()
        metrics = calculate_analysis_metrics(bey_stats)

        required_fields = [
            "bey", "elo", "matches", "wins", "losses",
            "upset_wins", "upset_losses", "upset_rate", "vulnerability",
            "avg_upset_win_magnitude", "avg_upset_loss_magnitude",
            "biggest_upset_win", "biggest_upset_loss"
        ]

        for entry in metrics:
            for field in required_fields:
                assert field in entry, f"Missing field: {field}"

    def test_upset_rate_range(self):
        """Upset rate should be between 0 and 1."""
        bey_stats, _ = analyze_upsets()
        metrics = calculate_analysis_metrics(bey_stats)

        for entry in metrics:
            assert 0 <= entry["upset_rate"] <= 1

    def test_vulnerability_range(self):
        """Vulnerability should be between 0 and 1."""
        bey_stats, _ = analyze_upsets()
        metrics = calculate_analysis_metrics(bey_stats)

        for entry in metrics:
            assert 0 <= entry["vulnerability"] <= 1


class TestCalculateGiantKillerScores:
    """Tests for the calculate_giant_killer_scores function."""

    def test_scores_added_to_data(self):
        """Giant Killer scores should be added to each entry."""
        bey_stats, _ = analyze_upsets()
        metrics = calculate_analysis_metrics(bey_stats)
        scored_data = calculate_giant_killer_scores(metrics)

        for entry in scored_data:
            assert "giant_killer_score" in entry
            assert 0 <= entry["giant_killer_score"] <= 100

    def test_higher_upsets_higher_score(self):
        """Beys with more upset wins should generally have higher scores."""
        bey_stats, _ = analyze_upsets()
        metrics = calculate_analysis_metrics(bey_stats)
        scored_data = calculate_giant_killer_scores(metrics)

        # Find entries with upsets vs without
        with_upsets = [e for e in scored_data if e["upset_wins"] > 0]
        without_upsets = [e for e in scored_data if e["upset_wins"] == 0]

        if with_upsets and without_upsets:
            max_with = max(e["giant_killer_score"] for e in with_upsets)
            max_without = max(e["giant_killer_score"] for e in without_upsets)
            assert max_with > max_without
