"""
Unit tests for recommended_matches.py module.
Tests the Recommended Matches functionality for data-driven match suggestions.
"""
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'analytics'))

from recommended_matches import (
    identify_low_data_beys,
    identify_similar_elo_clusters,
    identify_high_uncertainty_beys,
    calculate_usage_ratios,
    generate_low_data_recommendations,
    generate_elo_clarity_recommendations,
    generate_uncertainty_recommendations,
    generate_meta_balance_recommendations,
    generate_upset_recommendations,
    CONFIG,
)


class TestConfiguration:
    """Tests for configuration constants."""

    def test_config_has_required_keys(self):
        """Config should have all required keys."""
        required = {
            "low_data_threshold_percentile",
            "elo_similarity_window",
            "top_n_recommendations",
            "min_matches_for_analysis",
            "high_volatility_percentile",
            "meta_balance_usage_threshold",
            "upset_elo_difference_min",
            "max_existing_matches_threshold",
            "division_by_zero_epsilon",
        }
        assert required == set(CONFIG.keys())

    def test_percentiles_in_valid_range(self):
        """Percentiles should be between 0 and 1."""
        assert 0 < CONFIG["low_data_threshold_percentile"] <= 1
        assert 0 < CONFIG["high_volatility_percentile"] <= 1

    def test_thresholds_positive(self):
        """Numeric thresholds should be positive."""
        assert CONFIG["elo_similarity_window"] > 0
        assert CONFIG["top_n_recommendations"] > 0
        assert CONFIG["min_matches_for_analysis"] >= 0
        assert CONFIG["meta_balance_usage_threshold"] > 0
        assert CONFIG["upset_elo_difference_min"] > 0
        assert CONFIG["max_existing_matches_threshold"] > 0
        assert CONFIG["division_by_zero_epsilon"] > 0


class TestLowDataIdentification:
    """Tests for low-data Bey identification."""

    def test_identifies_low_data_beys(self):
        """Should identify Beys with fewer matches."""
        beys = {
            "BeyA": {"matches": 3},
            "BeyB": {"matches": 5},
            "BeyC": {"matches": 10},
            "BeyD": {"matches": 15},
            "BeyE": {"matches": 20},
        }
        low_data = identify_low_data_beys(beys)
        assert "BeyA" in low_data or "BeyB" in low_data

    def test_excludes_insufficient_data(self):
        """Should exclude Beys below minimum threshold."""
        beys = {
            "BeyA": {"matches": 1},  # Below minimum
            "BeyB": {"matches": 10},
            "BeyC": {"matches": 15},
        }
        low_data = identify_low_data_beys(beys)
        assert "BeyA" not in low_data

    def test_handles_empty_dataset(self):
        """Should handle empty dataset gracefully."""
        low_data = identify_low_data_beys({})
        assert low_data == []


class TestELOClusterIdentification:
    """Tests for ELO cluster identification."""

    def test_identifies_similar_elo_beys(self):
        """Should identify Beys with similar ELO."""
        beys = {
            "BeyA": {"elo": 1000},
            "BeyB": {"elo": 1010},  # Within 30 ELO
            "BeyC": {"elo": 1100},  # Far away
        }
        clusters = identify_similar_elo_clusters(beys)
        # Should find at least the BeyA-BeyB pair
        pairs = [(c[0], c[1]) for c in clusters]
        assert ("BeyA", "BeyB") in pairs or ("BeyB", "BeyA") in pairs

    def test_excludes_distant_elo(self):
        """Should not cluster Beys with large ELO differences."""
        beys = {
            "BeyA": {"elo": 1000},
            "BeyB": {"elo": 1100},  # 100 ELO difference
        }
        clusters = identify_similar_elo_clusters(beys)
        assert len(clusters) == 0

    def test_handles_empty_dataset(self):
        """Should handle empty dataset gracefully."""
        clusters = identify_similar_elo_clusters({})
        assert clusters == []


class TestHighUncertaintyIdentification:
    """Tests for high-uncertainty Bey identification."""

    def test_identifies_high_volatility_beys(self):
        """Should identify Beys with high volatility."""
        beys = {
            "BeyA": {"matches": 10},
            "BeyB": {"matches": 10},
            "BeyC": {"matches": 10},
        }
        advanced_stats = {
            "BeyA": {"volatility": 5.0},
            "BeyB": {"volatility": 20.0},  # High
            "BeyC": {"volatility": 10.0},
        }
        high_uncertainty = identify_high_uncertainty_beys(beys, advanced_stats)
        assert "BeyB" in high_uncertainty

    def test_handles_missing_advanced_stats(self):
        """Should handle missing advanced stats gracefully."""
        beys = {"BeyA": {"matches": 10}}
        high_uncertainty = identify_high_uncertainty_beys(beys, {})
        assert high_uncertainty == []


class TestUsageRatios:
    """Tests for usage ratio calculation."""

    def test_calculates_usage_ratios(self):
        """Should calculate usage ratios correctly."""
        beys = {
            "BeyA": {"matches": 10},
            "BeyB": {"matches": 20},
            "BeyC": {"matches": 5},
        }
        ratios = calculate_usage_ratios(beys)
        # Average is ~11.67, so BeyB should be > 1, BeyC should be < 1
        assert ratios["BeyB"] > 1.0
        assert ratios["BeyC"] < 1.0

    def test_handles_empty_dataset(self):
        """Should handle empty dataset gracefully."""
        ratios = calculate_usage_ratios({})
        assert ratios == {}


class TestLowDataRecommendations:
    """Tests for low-data recommendation generation."""

    def test_generates_recommendations_for_low_data(self):
        """Should generate recommendations for low-data Beys."""
        low_data_beys = ["BeyA"]
        beys = {
            "BeyA": {"matches": 3, "elo": 1000},
            "BeyB": {"matches": 10, "elo": 1000},
            "BeyC": {"matches": 10, "elo": 950},
            "BeyD": {"matches": 10, "elo": 1050},
        }
        matchups = {}

        recs = generate_low_data_recommendations(low_data_beys, beys, matchups)
        assert len(recs) > 0
        assert all(rec["category"] == "low_data_exploration" for rec in recs)

    def test_avoids_overplayed_matchups(self):
        """Should avoid recommending already overplayed matchups."""
        low_data_beys = ["BeyA"]
        beys = {
            "BeyA": {"matches": 3, "elo": 1000},
            "BeyB": {"matches": 10, "elo": 1000},
        }
        matchups = {("BeyA", "BeyB"): 5}  # Already played 5 times

        recs = generate_low_data_recommendations(low_data_beys, beys, matchups)
        # Should not recommend this matchup
        assert not any(
            set([rec["bey_a"], rec["bey_b"]]) == set(["BeyA", "BeyB"])
            for rec in recs
        )


class TestELOClarityRecommendations:
    """Tests for ELO clarity recommendation generation."""

    def test_generates_clarity_recommendations(self):
        """Should generate recommendations for similar ELO Beys."""
        clusters = [("BeyA", "BeyB", 10)]
        beys = {
            "BeyA": {"matches": 10, "elo": 1000, "rank": 5},
            "BeyB": {"matches": 10, "elo": 1010, "rank": 6},
        }
        matchups = {}

        recs = generate_elo_clarity_recommendations(clusters, beys, matchups)
        assert len(recs) > 0
        assert all(rec["category"] == "elo_clarity" for rec in recs)

    def test_prioritizes_top_rankings(self):
        """Should give bonus to top-ranked matchups."""
        clusters = [
            ("BeyA", "BeyB", 10),
            ("BeyC", "BeyD", 10),
        ]
        beys = {
            "BeyA": {"matches": 10, "elo": 1000, "rank": 3},
            "BeyB": {"matches": 10, "elo": 1010, "rank": 4},
            "BeyC": {"matches": 10, "elo": 900, "rank": 15},
            "BeyD": {"matches": 10, "elo": 910, "rank": 16},
        }
        matchups = {}

        recs = generate_elo_clarity_recommendations(clusters, beys, matchups)
        # Top-ranked matchup should have higher info value
        top_rec = [r for r in recs if set([r["bey_a"], r["bey_b"]]) == set(["BeyA", "BeyB"])][0]
        bottom_rec = [r for r in recs if set([r["bey_a"], r["bey_b"]]) == set(["BeyC", "BeyD"])][0]
        assert top_rec["info_value"] > bottom_rec["info_value"]


class TestUncertaintyRecommendations:
    """Tests for uncertainty recommendation generation."""

    def test_generates_uncertainty_recommendations(self):
        """Should generate recommendations for high-uncertainty Beys."""
        high_uncertainty_beys = ["BeyA"]
        beys = {
            "BeyA": {"matches": 10, "elo": 1000},
            "BeyB": {"matches": 15, "elo": 1000},  # Stable reference
        }
        advanced_stats = {
            "BeyA": {"volatility": 20.0},
            "BeyB": {"volatility": 5.0},
        }
        matchups = {}

        recs = generate_uncertainty_recommendations(
            high_uncertainty_beys, beys, advanced_stats, matchups
        )
        assert len(recs) > 0
        assert all(rec["category"] == "high_uncertainty" for rec in recs)


class TestMetaBalanceRecommendations:
    """Tests for meta balance recommendation generation."""

    def test_generates_meta_balance_recommendations(self):
        """Should generate recommendations between overplayed and underplayed Beys."""
        beys = {
            "BeyA": {"matches": 30},  # Overplayed
            "BeyB": {"matches": 3},   # Underplayed
            "BeyC": {"matches": 10},  # Normal
        }
        matchups = {}

        recs = generate_meta_balance_recommendations(beys, matchups)
        # Should recommend BeyA vs BeyB
        assert any(
            set([rec["bey_a"], rec["bey_b"]]) == set(["BeyA", "BeyB"])
            for rec in recs
        )


class TestUpsetRecommendations:
    """Tests for upset recommendation generation."""

    def test_generates_upset_recommendations(self):
        """Should generate recommendations for large ELO gaps."""
        beys = {
            "StrongBey": {"matches": 10, "elo": 1100},
            "WeakBey": {"matches": 10, "elo": 950},
        }
        matchups = {}

        recs = generate_upset_recommendations(beys, matchups)
        assert len(recs) > 0
        assert all(rec["category"] == "upset_testing" for rec in recs)

    def test_requires_minimum_elo_gap(self):
        """Should not recommend matchups with small ELO gaps."""
        beys = {
            "BeyA": {"matches": 10, "elo": 1000},
            "BeyB": {"matches": 10, "elo": 1020},  # Only 20 ELO gap
        }
        matchups = {}

        recs = generate_upset_recommendations(beys, matchups)
        assert len(recs) == 0  # Below 50 ELO minimum


class TestRecommendationStructure:
    """Tests for recommendation data structure."""

    def test_recommendation_has_required_fields(self):
        """Each recommendation should have required fields."""
        low_data_beys = ["BeyA"]
        beys = {
            "BeyA": {"matches": 3, "elo": 1000},
            "BeyB": {"matches": 10, "elo": 1000},
        }
        matchups = {}

        recs = generate_low_data_recommendations(low_data_beys, beys, matchups)
        assert len(recs) > 0

        required_fields = {"bey_a", "bey_b", "category", "info_value", "explanation", "existing_matches"}
        for rec in recs:
            assert required_fields == set(rec.keys())

    def test_info_value_is_numeric(self):
        """Info value should be numeric."""
        low_data_beys = ["BeyA"]
        beys = {
            "BeyA": {"matches": 3, "elo": 1000},
            "BeyB": {"matches": 10, "elo": 1000},
        }
        matchups = {}

        recs = generate_low_data_recommendations(low_data_beys, beys, matchups)
        for rec in recs:
            assert isinstance(rec["info_value"], (int, float))
            assert rec["info_value"] > 0

    def test_explanation_is_descriptive(self):
        """Explanation should be a non-empty string."""
        low_data_beys = ["BeyA"]
        beys = {
            "BeyA": {"matches": 3, "elo": 1000},
            "BeyB": {"matches": 10, "elo": 1000},
        }
        matchups = {}

        recs = generate_low_data_recommendations(low_data_beys, beys, matchups)
        for rec in recs:
            assert isinstance(rec["explanation"], str)
            assert len(rec["explanation"]) > 0
