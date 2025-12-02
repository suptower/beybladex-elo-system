"""
Unit tests for meta_balance.py module.
Tests the Meta Balance Analyzer functionality for competitive health metrics.
"""
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from meta_balance import (
    shannon_entropy,
    normalize_to_0_100,
    calculate_usage_diversity,
    calculate_win_rate_deviation,
    calculate_elo_compression_ratio,
    calculate_top_dominance_share,
    calculate_matchup_polarization,
    calculate_meta_health,
    identify_outliers,
    META_HEALTH_WEIGHTS,
    OUTLIER_THRESHOLDS,
)


class TestMetaHealthWeights:
    """Tests for meta health weight configuration."""

    def test_weights_sum_to_one(self):
        """Meta health weights should sum to 1.0."""
        total = sum(META_HEALTH_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"

    def test_all_weights_positive(self):
        """All weights should be positive."""
        for name, weight in META_HEALTH_WEIGHTS.items():
            assert weight > 0, f"Weight {name} is not positive: {weight}"

    def test_required_weight_keys(self):
        """Should have all required weight keys."""
        required = {
            "usage_diversity", "win_rate_balance", "elo_spread",
            "dominance_penalty", "polarization_penalty"
        }
        assert required == set(META_HEALTH_WEIGHTS.keys())


class TestOutlierThresholds:
    """Tests for outlier threshold configuration."""

    def test_overcentralizing_thresholds_in_valid_range(self):
        """Overcentralizing thresholds should be in valid ranges."""
        assert 0 < OUTLIER_THRESHOLDS["overcentralizing_usage_percentile"] <= 1
        assert 0 < OUTLIER_THRESHOLDS["overcentralizing_win_rate"] <= 1

    def test_underpowered_thresholds_in_valid_range(self):
        """Underpowered thresholds should be in valid ranges."""
        assert 0 < OUTLIER_THRESHOLDS["underpowered_usage_percentile"] <= 1
        assert 0 < OUTLIER_THRESHOLDS["underpowered_win_rate"] <= 1

    def test_matchup_threshold_reasonable(self):
        """Matchup threshold should be reasonable (50-90%)."""
        threshold = OUTLIER_THRESHOLDS["problematic_matchup_threshold"]
        assert 0.5 <= threshold <= 0.9

    def test_min_matches_positive(self):
        """Minimum matches for analysis should be positive."""
        assert OUTLIER_THRESHOLDS["min_matches_for_analysis"] > 0


class TestShannonEntropy:
    """Tests for Shannon entropy calculation."""

    def test_empty_list_returns_zero(self):
        """Empty probability list should return 0 entropy."""
        assert shannon_entropy([]) == 0.0

    def test_single_element_returns_zero(self):
        """Single element with probability 1 has 0 entropy."""
        assert shannon_entropy([1.0]) == 0.0

    def test_uniform_distribution_max_entropy(self):
        """Uniform distribution should have maximum entropy."""
        # Two equally likely outcomes
        result = shannon_entropy([0.5, 0.5])
        expected = 1.0  # log2(2) = 1
        assert abs(result - expected) < 0.001

    def test_four_uniform_outcomes(self):
        """Four uniform outcomes should have entropy of 2."""
        result = shannon_entropy([0.25, 0.25, 0.25, 0.25])
        expected = 2.0  # log2(4) = 2
        assert abs(result - expected) < 0.001

    def test_concentrated_distribution_low_entropy(self):
        """Concentrated distribution should have lower entropy."""
        # One dominant outcome (90%)
        concentrated = shannon_entropy([0.9, 0.05, 0.05])
        # Uniform outcomes
        uniform = shannon_entropy([0.33, 0.33, 0.34])

        assert concentrated < uniform

    def test_handles_zero_probabilities(self):
        """Should handle zero probabilities gracefully."""
        result = shannon_entropy([0.5, 0.5, 0.0])
        assert result > 0  # Should still calculate


class TestNormalizeTo0_100:
    """Tests for normalization function."""

    def test_min_value_returns_zero(self):
        """Minimum value should normalize to 0."""
        assert normalize_to_0_100(0, 0, 100) == 0.0

    def test_max_value_returns_100(self):
        """Maximum value should normalize to 100."""
        assert normalize_to_0_100(100, 0, 100) == 100.0

    def test_mid_value_returns_50(self):
        """Middle value should normalize to 50."""
        assert normalize_to_0_100(50, 0, 100) == 50.0

    def test_invert_flag(self):
        """Invert flag should flip the scale."""
        normal = normalize_to_0_100(75, 0, 100, invert=False)
        inverted = normalize_to_0_100(75, 0, 100, invert=True)
        assert abs(normal + inverted - 100) < 0.1

    def test_clamps_below_min(self):
        """Values below min should clamp to 0."""
        assert normalize_to_0_100(-10, 0, 100) == 0.0

    def test_clamps_above_max(self):
        """Values above max should clamp to 100."""
        assert normalize_to_0_100(150, 0, 100) == 100.0

    def test_same_min_max_returns_50(self):
        """Same min and max should return 50 (neutral)."""
        assert normalize_to_0_100(10, 10, 10) == 50.0


class TestCalculateUsageDiversity:
    """Tests for usage diversity calculation."""

    def test_empty_data_returns_defaults(self):
        """Empty data should return neutral values."""
        result = calculate_usage_diversity([], [])
        assert "overall_score" in result
        assert "blade" in result
        assert "ratchet" in result
        assert "bit" in result

    def test_returns_expected_keys(self):
        """Should return all expected keys."""
        matches = [
            {"bey_a": "BeyA", "bey_b": "BeyB", "score_a": 3, "score_b": 2}
        ]
        result = calculate_usage_diversity(matches, [])

        assert "overall_score" in result
        assert "blade" in result
        assert "ratchet" in result
        assert "bit" in result
        assert "bey" in result

    def test_more_variety_higher_score(self):
        """More variety in usage should result in higher diversity score."""
        # Single bey used repeatedly
        single_bey_matches = [
            {"bey_a": "BeyA", "bey_b": "BeyA", "score_a": 3, "score_b": 2}
        ] * 10

        # Multiple different beys
        multi_bey_matches = [
            {"bey_a": f"Bey{i}", "bey_b": f"Bey{i + 1}", "score_a": 3, "score_b": 2}
            for i in range(10)
        ]

        single_result = calculate_usage_diversity(single_bey_matches, [])
        multi_result = calculate_usage_diversity(multi_bey_matches, [])

        # Multi-bey should have higher diversity in bey usage
        assert multi_result["bey"]["unique_count"] >= single_result["bey"]["unique_count"]


class TestCalculateWinRateDeviation:
    """Tests for win rate deviation calculation."""

    def test_empty_data_returns_neutral(self):
        """Empty data should return neutral score."""
        result = calculate_win_rate_deviation([])
        assert result["score"] == 50.0

    def test_single_entry_returns_neutral(self):
        """Single entry should return neutral score."""
        data = [{"bey": "A", "elo": 1000, "matches": 10, "winrate": 0.6}]
        result = calculate_win_rate_deviation(data)
        assert result["score"] == 50.0

    def test_uniform_winrates_high_score(self):
        """Uniform win rates should produce high balance score."""
        data = [
            {"bey": "A", "elo": 1000, "matches": 10, "winrate": 0.50},
            {"bey": "B", "elo": 1000, "matches": 10, "winrate": 0.50},
            {"bey": "C", "elo": 1000, "matches": 10, "winrate": 0.50},
        ]
        result = calculate_win_rate_deviation(data)
        assert result["score"] >= 90  # Very balanced

    def test_varied_winrates_lower_score(self):
        """Highly varied win rates should produce lower balance score."""
        data = [
            {"bey": "A", "elo": 1100, "matches": 10, "winrate": 0.90},
            {"bey": "B", "elo": 1000, "matches": 10, "winrate": 0.50},
            {"bey": "C", "elo": 900, "matches": 10, "winrate": 0.10},
        ]
        result = calculate_win_rate_deviation(data)
        assert result["score"] < 50  # Imbalanced

    def test_returns_expected_keys(self):
        """Should return all expected keys."""
        data = [
            {"bey": "A", "elo": 1000, "matches": 10, "winrate": 0.5},
            {"bey": "B", "elo": 1000, "matches": 10, "winrate": 0.5},
        ]
        result = calculate_win_rate_deviation(data)

        expected_keys = {
            "score", "std_deviation", "variance", "mean_winrate",
            "min_winrate", "max_winrate", "range", "beys_analyzed"
        }
        assert expected_keys == set(result.keys())


class TestCalculateEloCompressionRatio:
    """Tests for ELO compression ratio calculation."""

    def test_empty_data_returns_neutral(self):
        """Empty data should return neutral values."""
        result = calculate_elo_compression_ratio([])
        assert result["score"] == 50.0

    def test_returns_expected_keys(self):
        """Should return all expected keys."""
        data = [
            {"bey": "A", "elo": 1100, "matches": 10},
            {"bey": "B", "elo": 1000, "matches": 10},
        ]
        result = calculate_elo_compression_ratio(data)

        expected_keys = {
            "score", "mean_elo", "std_deviation", "min_elo",
            "max_elo", "range", "compression_ratio", "beys_analyzed"
        }
        assert expected_keys == set(result.keys())

    def test_compressed_elos_have_low_range(self):
        """Similar ELOs should have small range."""
        data = [
            {"bey": "A", "elo": 1005, "matches": 10},
            {"bey": "B", "elo": 1000, "matches": 10},
            {"bey": "C", "elo": 995, "matches": 10},
        ]
        result = calculate_elo_compression_ratio(data)
        assert result["range"] == 10  # 1005 - 995


class TestCalculateTopDominanceShare:
    """Tests for top dominance share calculation."""

    def test_empty_data_returns_neutral(self):
        """Empty data should return neutral values."""
        result = calculate_top_dominance_share([], [])
        assert result["score"] == 50.0

    def test_returns_expected_keys(self):
        """Should return all expected keys."""
        matches = [{"bey_a": "A", "bey_b": "B", "score_a": 3, "score_b": 2}]
        leaderboard = [
            {"bey": "A", "elo": 1100},
            {"bey": "B", "elo": 1000},
        ]
        result = calculate_top_dominance_share(matches, leaderboard)

        expected_keys = {
            "score", "top_3_share", "top_5_share", "top_10_share",
            "top_3_beys", "total_matches"
        }
        assert expected_keys == set(result.keys())

    def test_high_dominance_low_score(self):
        """High dominance should result in lower health score."""
        # All matches involve top bey
        matches = [
            {"bey_a": "TopBey", "bey_b": f"Other{i}", "score_a": 3, "score_b": 2}
            for i in range(10)
        ]
        leaderboard = [{"bey": "TopBey", "elo": 1200}] + [
            {"bey": f"Other{i}", "elo": 1000} for i in range(10)
        ]

        result = calculate_top_dominance_share(matches, leaderboard)
        assert result["top_3_share"] == 100.0  # TopBey in every match


class TestCalculateMatchupPolarization:
    """Tests for matchup polarization calculation."""

    def test_empty_matches_returns_high_score(self):
        """Empty matches should return high score (no polarization)."""
        result = calculate_matchup_polarization([])
        assert result["score"] >= 50

    def test_returns_expected_keys(self):
        """Should return all expected keys."""
        matches = [
            {"bey_a": "A", "bey_b": "B", "score_a": 3, "score_b": 2},
            {"bey_a": "A", "bey_b": "B", "score_a": 3, "score_b": 2},
        ]
        result = calculate_matchup_polarization(matches)

        expected_keys = {
            "score", "polarization_rate", "polarized_matchups_count",
            "total_matchups_analyzed", "threshold_used", "worst_matchups"
        }
        assert expected_keys == set(result.keys())

    def test_one_sided_matchup_detected(self):
        """Consistently one-sided matchups should be flagged."""
        # A always beats B
        matches = [
            {"bey_a": "A", "bey_b": "B", "score_a": 3, "score_b": 2},
            {"bey_a": "A", "bey_b": "B", "score_a": 4, "score_b": 1},
            {"bey_a": "B", "bey_b": "A", "score_a": 1, "score_b": 3},
        ]
        result = calculate_matchup_polarization(matches)
        assert result["polarized_matchups_count"] >= 1


class TestCalculateMetaHealth:
    """Tests for overall meta health calculation."""

    def test_all_perfect_scores_give_high_health(self):
        """Perfect individual scores should give high overall health."""
        diversity = {"overall_score": 100}
        win_rate_dev = {"score": 100}
        elo_compression = {"score": 100}
        dominance = {"score": 100}
        polarization = {"score": 100}

        result = calculate_meta_health(
            diversity, win_rate_dev, elo_compression, dominance, polarization
        )
        assert result["overall_score"] == 100.0
        assert result["status"] == "Healthy"

    def test_all_zero_scores_give_low_health(self):
        """Zero individual scores should give low overall health."""
        diversity = {"overall_score": 0}
        win_rate_dev = {"score": 0}
        elo_compression = {"score": 0}
        dominance = {"score": 0}
        polarization = {"score": 0}

        result = calculate_meta_health(
            diversity, win_rate_dev, elo_compression, dominance, polarization
        )
        assert result["overall_score"] == 0.0
        assert result["status"] == "Critical"

    def test_returns_expected_keys(self):
        """Should return all expected keys."""
        diversity = {"overall_score": 50}
        win_rate_dev = {"score": 50}
        elo_compression = {"score": 50}
        dominance = {"score": 50}
        polarization = {"score": 50}

        result = calculate_meta_health(
            diversity, win_rate_dev, elo_compression, dominance, polarization
        )

        expected_keys = {"overall_score", "status", "status_class", "breakdown", "alerts", "weights"}
        assert expected_keys == set(result.keys())

    def test_generates_alerts_for_low_scores(self):
        """Low individual scores should generate alerts."""
        diversity = {"overall_score": 30}  # Low
        win_rate_dev = {"score": 50}
        elo_compression = {"score": 50}
        dominance = {"score": 50}
        polarization = {"score": 50}

        result = calculate_meta_health(
            diversity, win_rate_dev, elo_compression, dominance, polarization
        )
        assert len(result["alerts"]) > 0

    def test_status_classes_are_valid(self):
        """Status classes should be one of the defined values."""
        valid_classes = {"excellent", "good", "moderate", "warning", "critical"}

        test_cases = [
            (90, 90, 90, 90, 90),  # Healthy
            (60, 60, 60, 60, 60),  # Balanced
            (45, 45, 45, 45, 45),  # Moderate
            (30, 30, 30, 30, 30),  # Imbalanced
            (10, 10, 10, 10, 10),  # Critical
        ]

        for scores in test_cases:
            diversity = {"overall_score": scores[0]}
            win_rate_dev = {"score": scores[1]}
            elo_compression = {"score": scores[2]}
            dominance = {"score": scores[3]}
            polarization = {"score": scores[4]}

            result = calculate_meta_health(
                diversity, win_rate_dev, elo_compression, dominance, polarization
            )
            assert result["status_class"] in valid_classes


class TestIdentifyOutliers:
    """Tests for outlier identification."""

    def test_empty_data_returns_structure(self):
        """Empty data should return proper structure with notes."""
        result = identify_outliers([], {}, [])

        expected_keys = {
            "overcentralizing", "underpowered",
            "emerging_threats", "confidence_notes"
        }
        assert expected_keys == set(result.keys())

    def test_high_winrate_flagged_as_overcentralizing(self):
        """High win rate with many matches should be flagged."""
        leaderboard = [
            {"bey": "OP", "elo": 1200, "matches": 20, "winrate": 0.85},
            {"bey": "Normal", "elo": 1000, "matches": 10, "winrate": 0.50},
            {"bey": "Weak", "elo": 900, "matches": 10, "winrate": 0.30},
        ]
        diversity = {"overall_score": 50}

        result = identify_outliers(leaderboard, diversity, [])
        assert len(result["overcentralizing"]) >= 1
        assert any(o["bey"] == "OP" for o in result["overcentralizing"])

    def test_low_winrate_flagged_as_underpowered(self):
        """Low win rate should be flagged as underpowered."""
        leaderboard = [
            {"bey": "Strong", "elo": 1200, "matches": 10, "winrate": 0.70},
            {"bey": "Normal", "elo": 1000, "matches": 10, "winrate": 0.50},
            {"bey": "Weak", "elo": 900, "matches": 10, "winrate": 0.25},
        ]
        diversity = {"overall_score": 50}

        result = identify_outliers(leaderboard, diversity, [])
        assert len(result["underpowered"]) >= 1
        assert any(o["bey"] == "Weak" for o in result["underpowered"])

    def test_insufficient_matches_excluded(self):
        """Beys with insufficient matches should not be analyzed."""
        leaderboard = [
            {"bey": "NewBey", "elo": 1200, "matches": 1, "winrate": 1.0},  # Too few matches
            {"bey": "Normal", "elo": 1000, "matches": 10, "winrate": 0.50},
        ]
        diversity = {"overall_score": 50}

        result = identify_outliers(leaderboard, diversity, [])
        # NewBey should not appear in overcentralizing due to low matches
        assert not any(o["bey"] == "NewBey" for o in result["overcentralizing"])


class TestMetaBalanceIntegration:
    """Integration tests using real data."""

    def test_full_analysis_returns_valid_structure(self):
        """Full analysis should return a valid complete structure."""
        from meta_balance import generate_meta_balance_report

        report = generate_meta_balance_report()

        # Check top-level keys
        assert "meta_health" in report
        assert "metrics" in report
        assert "outliers" in report
        assert "metadata" in report

        # Check meta health structure
        assert "overall_score" in report["meta_health"]
        assert 0 <= report["meta_health"]["overall_score"] <= 100

        # Check metrics structure
        metrics = report["metrics"]
        assert "usage_diversity" in metrics
        assert "win_rate_deviation" in metrics
        assert "elo_compression" in metrics
        assert "top_dominance" in metrics
        assert "matchup_polarization" in metrics

    def test_all_scores_in_valid_range(self):
        """All calculated scores should be in 0-100 range."""
        from meta_balance import generate_meta_balance_report

        report = generate_meta_balance_report()

        # Check main health score
        assert 0 <= report["meta_health"]["overall_score"] <= 100

        # Check all metric scores
        for metric_name, metric_data in report["metrics"].items():
            if "score" in metric_data:
                score = metric_data["score"]
                assert 0 <= score <= 100, f"{metric_name} score {score} out of range"
            if "overall_score" in metric_data:
                score = metric_data["overall_score"]
                assert 0 <= score <= 100, f"{metric_name} overall_score {score} out of range"
