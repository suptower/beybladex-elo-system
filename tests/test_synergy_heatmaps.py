"""
Unit tests for synergy_heatmaps.py module.
Tests the Synergy Heatmap functionality for part combinations.
"""
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from synergy_heatmaps import (
    calculate_finish_quality_score,
    calculate_stat_complementarity,
    calculate_synergy_score,
    build_bey_components_map,
    SYNERGY_WEIGHTS,
    FINISH_QUALITY,
    MIN_MATCHES_THRESHOLD,
)


class TestSynergyWeights:
    """Tests for synergy weight configuration."""

    def test_weights_sum_to_one(self):
        """Synergy weights should sum to 1.0."""
        total = sum(SYNERGY_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"

    def test_all_weights_positive(self):
        """All weights should be positive."""
        for name, weight in SYNERGY_WEIGHTS.items():
            assert weight > 0, f"Weight {name} is not positive: {weight}"

    def test_required_weight_keys(self):
        """Should have all required weight keys."""
        required = {"win_rate", "finish_quality", "elo_performance",
                    "stability", "stat_complementarity"}
        assert required == set(SYNERGY_WEIGHTS.keys())


class TestFinishQualityScores:
    """Tests for finish quality score configuration."""

    def test_extreme_is_highest(self):
        """Extreme finish should have highest quality score."""
        assert FINISH_QUALITY["extreme"] == max(FINISH_QUALITY.values())

    def test_spin_is_lowest(self):
        """Spin finish should have lowest quality score."""
        assert FINISH_QUALITY["spin"] == min(FINISH_QUALITY.values())

    def test_all_scores_in_valid_range(self):
        """All finish scores should be between 0 and 1."""
        for finish, score in FINISH_QUALITY.items():
            assert 0 <= score <= 1, f"{finish} score {score} out of range"

    def test_required_finish_types(self):
        """Should have all required finish types."""
        required = {"extreme", "burst", "pocket", "spin"}
        assert required == set(FINISH_QUALITY.keys())


class TestCalculateFinishQualityScore:
    """Tests for finish quality score calculation."""

    def test_empty_counts_returns_neutral(self):
        """Empty counts should return 0.5 (neutral)."""
        result = calculate_finish_quality_score({})
        assert result == 0.5

    def test_all_extreme_finishes(self):
        """All extreme finishes should give maximum score."""
        result = calculate_finish_quality_score({"extreme": 10})
        assert result == FINISH_QUALITY["extreme"]

    def test_all_spin_finishes(self):
        """All spin finishes should give minimum score."""
        result = calculate_finish_quality_score({"spin": 10})
        assert result == FINISH_QUALITY["spin"]

    def test_mixed_finishes(self):
        """Mixed finishes should give weighted average."""
        # 50% extreme (1.0) + 50% spin (0.4) = 0.7
        result = calculate_finish_quality_score({"extreme": 5, "spin": 5})
        expected = (5 * FINISH_QUALITY["extreme"] + 5 * FINISH_QUALITY["spin"]) / 10
        assert abs(result - expected) < 0.01

    def test_result_in_valid_range(self):
        """Result should always be between 0 and 1."""
        test_cases = [
            {"spin": 1},
            {"burst": 5, "spin": 5},
            {"extreme": 3, "burst": 2, "pocket": 1, "spin": 4},
        ]
        for counts in test_cases:
            result = calculate_finish_quality_score(counts)
            assert 0 <= result <= 1, f"Result {result} out of range for {counts}"


class TestCalculateStatComplementarity:
    """Tests for stat complementarity calculation."""

    def test_empty_stats_returns_neutral(self):
        """Empty stats should return 0.5 (neutral)."""
        result = calculate_stat_complementarity({}, {}, "blade", "bit")
        assert result == 0.5

    def test_high_stats_give_higher_score(self):
        """Parts with high stats should have better complementarity."""
        high_stats = {"stat1": 4.5, "stat2": 4.0, "stat3": 4.5}
        low_stats = {"stat1": 1.0, "stat2": 1.5, "stat3": 1.0}

        high_result = calculate_stat_complementarity(
            high_stats, high_stats, "blade", "bit"
        )
        low_result = calculate_stat_complementarity(
            low_stats, low_stats, "blade", "bit"
        )

        assert high_result > low_result

    def test_result_in_valid_range(self):
        """Result should always be between 0 and 1."""
        test_cases = [
            ({"a": 0}, {"b": 0}),
            ({"a": 5}, {"b": 5}),
            ({"a": 2.5, "b": 3.5}, {"c": 1.0, "d": 4.0}),
        ]
        for stats1, stats2 in test_cases:
            result = calculate_stat_complementarity(stats1, stats2, "blade", "bit")
            assert 0 <= result <= 1, f"Result {result} out of range"


class TestCalculateSynergyScore:
    """Tests for synergy score calculation."""

    def test_perfect_scores_give_100(self):
        """Perfect inputs should give score of 100."""
        result = calculate_synergy_score(1.0, 1.0, 1.0, 1.0, 1.0)
        assert result == 100.0

    def test_zero_scores_give_zero(self):
        """Zero inputs should give score of 0."""
        result = calculate_synergy_score(0.0, 0.0, 0.0, 0.0, 0.0)
        assert result == 0.0

    def test_neutral_scores_give_50(self):
        """Neutral inputs (0.5) should give score around 50."""
        result = calculate_synergy_score(0.5, 0.5, 0.5, 0.5, 0.5)
        assert result == 50.0

    def test_win_rate_has_highest_weight(self):
        """Win rate should have highest impact on score."""
        # High win rate only
        high_wr = calculate_synergy_score(1.0, 0.5, 0.5, 0.5, 0.5)
        # High finish quality only
        high_fq = calculate_synergy_score(0.5, 1.0, 0.5, 0.5, 0.5)

        # Win rate (0.35) > finish quality (0.25)
        assert high_wr > high_fq

    def test_result_range(self):
        """Score should be between 0 and 100."""
        import random
        for _ in range(10):
            inputs = [random.random() for _ in range(5)]
            result = calculate_synergy_score(*inputs)
            assert 0 <= result <= 100, f"Score {result} out of range"


class TestBuildBeyComponentsMap:
    """Tests for building bey components mapping."""

    def test_returns_dict(self):
        """Should return a dictionary."""
        result = build_bey_components_map([])
        assert isinstance(result, dict)

    def test_extracts_components(self):
        """Should extract blade, ratchet, and bit."""
        beys_data = [{
            "name": "TestBey 3-60F",
            "blade": "TestBlade",
            "ratchet": "3-60",
            "bit": "Flat",
            "type": "Attack"
        }]
        result = build_bey_components_map(beys_data)

        assert "TestBlade" in result
        assert result["TestBlade"]["blade"] == "TestBlade"
        assert result["TestBlade"]["ratchet"] == "3-60"
        assert result["TestBlade"]["bit"] == "Flat"

    def test_handles_space_in_name(self):
        """Should handle blade names with spaces."""
        beys_data = [{
            "name": "Hells Hammer 3-70H",
            "blade": "Hells Hammer",
            "ratchet": "3-70",
            "bit": "Hexa",
            "type": "Balance"
        }]
        result = build_bey_components_map(beys_data)

        # Both normalized and original should be accessible
        assert "HellsHammer" in result
        assert "Hells Hammer" in result

    def test_skips_entries_without_blade(self):
        """Should skip entries without blade field."""
        beys_data = [
            {"name": "Valid", "blade": "ValidBlade", "ratchet": "1-60", "bit": "Flat"},
            {"name": "Invalid", "ratchet": "2-60", "bit": "Ball"},  # No blade
        ]
        result = build_bey_components_map(beys_data)

        assert "ValidBlade" in result
        assert len(result) == 1


class TestMinMatchesThreshold:
    """Tests for minimum matches threshold configuration."""

    def test_threshold_is_positive(self):
        """Threshold should be a positive integer."""
        assert MIN_MATCHES_THRESHOLD > 0
        assert isinstance(MIN_MATCHES_THRESHOLD, int)

    def test_threshold_is_reasonable(self):
        """Threshold should be within reasonable range (3-20)."""
        assert 3 <= MIN_MATCHES_THRESHOLD <= 20
