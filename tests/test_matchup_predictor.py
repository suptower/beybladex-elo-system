"""
Unit tests for matchup_predictor.py module.
Tests the matchup prediction functions including probability calculations,
outcome predictions, confidence scoring, and upset likelihood.
"""
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from matchup_predictor import (
    calculate_expected_score,
    calculate_stat_advantage,
    calculate_win_probability,
    calculate_outcome_probabilities,
    calculate_confidence,
    calculate_upset_likelihood,
    predict_matchup,
    PREDICTION_WEIGHTS,
)


class TestPredictionWeights:
    """Tests for prediction weight configuration."""

    def test_weights_sum_to_one(self):
        """Prediction weights should sum to 1.0."""
        total = sum(PREDICTION_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_all_weights_positive(self):
        """All weights should be positive."""
        for weight in PREDICTION_WEIGHTS.values():
            assert weight > 0

    def test_elo_weight_is_significant(self):
        """ELO weight should be at least 0.3 for meaningful base prediction."""
        assert PREDICTION_WEIGHTS["elo_weight"] >= 0.3


class TestCalculateExpectedScore:
    """Tests for the calculate_expected_score function."""

    def test_equal_ratings(self):
        """Equal ratings should give 0.5 expected score."""
        result = calculate_expected_score(1000, 1000)
        assert result == 0.5

    def test_higher_rating_favored(self):
        """Higher rated player should have expected score > 0.5."""
        result = calculate_expected_score(1200, 1000)
        assert result > 0.5
        assert result < 1.0

    def test_lower_rating_unfavored(self):
        """Lower rated player should have expected score < 0.5."""
        result = calculate_expected_score(1000, 1200)
        assert result < 0.5
        assert result > 0.0

    def test_400_point_difference(self):
        """400 point difference should give approximately 10:1 odds."""
        result = calculate_expected_score(1400, 1000)
        # 1 / (1 + 10^1) ≈ 0.909
        assert abs(result - 0.909) < 0.01

    def test_symmetry(self):
        """Expected scores of opponents should sum to 1."""
        e_a = calculate_expected_score(1200, 1000)
        e_b = calculate_expected_score(1000, 1200)
        assert abs(e_a + e_b - 1.0) < 0.0001


class TestCalculateStatAdvantage:
    """Tests for the calculate_stat_advantage function."""

    def test_equal_stats(self):
        """Equal stats should give 0 advantage."""
        result = calculate_stat_advantage(3.0, 3.0)
        assert result == 0.0

    def test_higher_stat_positive_advantage(self):
        """Higher stat A should give positive advantage."""
        result = calculate_stat_advantage(4.0, 2.0)
        assert result > 0

    def test_lower_stat_negative_advantage(self):
        """Lower stat A should give negative advantage."""
        result = calculate_stat_advantage(2.0, 4.0)
        assert result < 0

    def test_advantage_range(self):
        """Advantage should be clamped to -0.5 to 0.5."""
        # Max possible difference
        result_max = calculate_stat_advantage(5.0, 0.0)
        result_min = calculate_stat_advantage(0.0, 5.0)
        assert -0.5 <= result_max <= 0.5
        assert -0.5 <= result_min <= 0.5

    def test_symmetry(self):
        """Swapping stats should give opposite advantage."""
        adv_a = calculate_stat_advantage(4.0, 2.0)
        adv_b = calculate_stat_advantage(2.0, 4.0)
        assert abs(adv_a + adv_b) < 0.0001


class TestCalculateWinProbability:
    """Tests for the calculate_win_probability function."""

    def test_equal_stats_approximately_equal_probability(self):
        """Beys with equal stats should have approximately equal win probability."""
        stats_a = {
            "leaderboard": {"elo": 1000},
            "stats": {"attack": 3.0, "defense": 3.0, "stamina": 3.0, "control": 3.0, "meta_impact": 3.0}
        }
        stats_b = {
            "leaderboard": {"elo": 1000},
            "stats": {"attack": 3.0, "defense": 3.0, "stamina": 3.0, "control": 3.0, "meta_impact": 3.0}
        }
        result = calculate_win_probability(stats_a, stats_b)
        assert abs(result["prob_a"] - 0.5) < 0.1
        assert abs(result["prob_b"] - 0.5) < 0.1

    def test_probabilities_sum_to_one(self):
        """Win probabilities should sum to 1."""
        stats_a = {
            "leaderboard": {"elo": 1100},
            "stats": {"attack": 4.0, "defense": 3.0, "stamina": 3.5, "control": 3.0, "meta_impact": 3.5}
        }
        stats_b = {
            "leaderboard": {"elo": 1000},
            "stats": {"attack": 2.0, "defense": 3.5, "stamina": 2.5, "control": 3.0, "meta_impact": 2.5}
        }
        result = calculate_win_probability(stats_a, stats_b)
        assert abs(result["prob_a"] + result["prob_b"] - 1.0) < 0.0001

    def test_higher_elo_higher_probability(self):
        """Higher ELO should increase win probability."""
        stats_a = {
            "leaderboard": {"elo": 1200},
            "stats": {"attack": 3.0, "defense": 3.0, "stamina": 3.0, "control": 3.0, "meta_impact": 3.0}
        }
        stats_b = {
            "leaderboard": {"elo": 1000},
            "stats": {"attack": 3.0, "defense": 3.0, "stamina": 3.0, "control": 3.0, "meta_impact": 3.0}
        }
        result = calculate_win_probability(stats_a, stats_b)
        assert result["prob_a"] > result["prob_b"]

    def test_probability_clamped(self):
        """Probabilities should be clamped between 0.01 and 0.99."""
        stats_a = {
            "leaderboard": {"elo": 2000},
            "stats": {"attack": 5.0, "defense": 5.0, "stamina": 5.0, "control": 5.0, "meta_impact": 5.0}
        }
        stats_b = {
            "leaderboard": {"elo": 500},
            "stats": {"attack": 0.0, "defense": 0.0, "stamina": 0.0, "control": 0.0, "meta_impact": 0.0}
        }
        result = calculate_win_probability(stats_a, stats_b)
        assert 0.01 <= result["prob_a"] <= 0.99
        assert 0.01 <= result["prob_b"] <= 0.99

    def test_handles_missing_stats(self):
        """Should handle missing stats gracefully with defaults."""
        stats_a = {"leaderboard": {"elo": 1000}}
        stats_b = {"leaderboard": {"elo": 1000}}
        result = calculate_win_probability(stats_a, stats_b)
        assert "prob_a" in result
        assert "prob_b" in result
        assert abs(result["prob_a"] - 0.5) < 0.1


class TestCalculateOutcomeProbabilities:
    """Tests for the calculate_outcome_probabilities function."""

    def test_returns_all_outcome_types(self):
        """Should return all five outcome types for each Bey."""
        stats_a = {
            "stats": {"attack": 3.0, "defense": 3.0, "stamina": 3.0, "control": 3.0, "meta_impact": 3.0},
            "sub_metrics": {
                "attack": {"burst_finish_rate": 0.2, "pocket_finish_rate": 0.15, "extreme_finish_rate": 0.1},
                "defense": {"burst_resistance": 0.7, "pocket_resistance": 0.7, "extreme_resistance": 0.9},
                "stamina": {"spin_finish_win_rate": 0.4}
            }
        }
        stats_b = stats_a.copy()
        win_probs = {"prob_a": 0.5, "prob_b": 0.5}

        result = calculate_outcome_probabilities(stats_a, stats_b, win_probs)

        assert "bey_a" in result
        assert "bey_b" in result
        assert "burst_finish" in result["bey_a"]
        assert "pocket_finish" in result["bey_a"]
        assert "extreme_finish" in result["bey_a"]
        assert "spin_finish" in result["bey_a"]
        assert "judge_decision" in result["bey_a"]

    def test_outcome_probabilities_non_negative(self):
        """All outcome probabilities should be non-negative."""
        stats_a = {
            "stats": {"attack": 4.0, "defense": 2.0, "stamina": 3.0, "control": 3.0, "meta_impact": 3.0},
            "sub_metrics": {
                "attack": {"burst_finish_rate": 0.3, "pocket_finish_rate": 0.2, "extreme_finish_rate": 0.15},
                "defense": {"burst_resistance": 0.6, "pocket_resistance": 0.6, "extreme_resistance": 0.8},
                "stamina": {"spin_finish_win_rate": 0.35}
            }
        }
        stats_b = {
            "stats": {"attack": 2.0, "defense": 4.0, "stamina": 3.0, "control": 3.0, "meta_impact": 3.0},
            "sub_metrics": {
                "attack": {"burst_finish_rate": 0.1, "pocket_finish_rate": 0.1, "extreme_finish_rate": 0.05},
                "defense": {"burst_resistance": 0.85, "pocket_resistance": 0.85, "extreme_resistance": 0.95},
                "stamina": {"spin_finish_win_rate": 0.5}
            }
        }
        win_probs = {"prob_a": 0.6, "prob_b": 0.4}

        result = calculate_outcome_probabilities(stats_a, stats_b, win_probs)

        for bey_key in ["bey_a", "bey_b"]:
            for outcome_key in result[bey_key]:
                assert result[bey_key][outcome_key] >= 0


class TestCalculateConfidence:
    """Tests for the calculate_confidence function."""

    def test_high_confidence_with_many_matches(self):
        """Should return high confidence when both Beys have many matches."""
        stats_a = {
            "leaderboard": {"matches": 10},
            "stats": {"attack": 3.0},
            "sub_metrics": {"attack": {}}
        }
        stats_b = {
            "leaderboard": {"matches": 12},
            "stats": {"attack": 3.0},
            "sub_metrics": {"attack": {}}
        }
        result = calculate_confidence(stats_a, stats_b)
        assert result["level"] == "high"
        assert result["score"] >= 80

    def test_low_confidence_with_few_matches(self):
        """Should return low confidence when Beys have few matches."""
        stats_a = {"leaderboard": {"matches": 1}}
        stats_b = {"leaderboard": {"matches": 2}}
        result = calculate_confidence(stats_a, stats_b)
        assert result["level"] in ["low", "medium"]
        assert result["score"] < 80

    def test_confidence_score_range(self):
        """Confidence score should be between 0 and 100."""
        stats_a = {"leaderboard": {"matches": 5}, "stats": {}, "sub_metrics": {}}
        stats_b = {"leaderboard": {"matches": 5}, "stats": {}, "sub_metrics": {}}
        result = calculate_confidence(stats_a, stats_b)
        assert 0 <= result["score"] <= 100

    def test_returns_reasons(self):
        """Should return list of reasoning."""
        stats_a = {"leaderboard": {"matches": 10}, "stats": {}, "sub_metrics": {}}
        stats_b = {"leaderboard": {"matches": 10}, "stats": {}, "sub_metrics": {}}
        result = calculate_confidence(stats_a, stats_b)
        assert "reasons" in result
        assert isinstance(result["reasons"], list)


class TestCalculateUpsetLikelihood:
    """Tests for the calculate_upset_likelihood function."""

    def test_close_match_no_upset(self):
        """Close matches should not be classified as potential upsets."""
        stats_a = {"leaderboard": {"elo": 1000}}
        stats_b = {"leaderboard": {"elo": 1010}}
        win_probs = {"prob_a": 0.48, "prob_b": 0.52}
        result = calculate_upset_likelihood(stats_a, stats_b, win_probs)
        assert result["likelihood"] == "none"

    def test_one_sided_match_low_upset(self):
        """One-sided matches should have low upset potential."""
        stats_a = {"leaderboard": {"elo": 1200}}
        stats_b = {"leaderboard": {"elo": 1000}, "sub_metrics": {"meta_impact": {"upset_rate": 0.1}}}
        win_probs = {"prob_a": 0.85, "prob_b": 0.15}
        result = calculate_upset_likelihood(stats_a, stats_b, win_probs)
        assert result["likelihood"] in ["very_low", "low"]

    def test_identifies_favorite_and_underdog(self):
        """Should correctly identify favorite and underdog."""
        stats_a = {"leaderboard": {"elo": 1100}}
        stats_b = {"leaderboard": {"elo": 1000}}
        win_probs = {"prob_a": 0.65, "prob_b": 0.35}
        result = calculate_upset_likelihood(stats_a, stats_b, win_probs)
        assert result["favorite"] == "bey_a"
        assert result["underdog"] == "bey_b"

    def test_returns_elo_difference(self):
        """Should return the ELO difference."""
        stats_a = {"leaderboard": {"elo": 1150}}
        stats_b = {"leaderboard": {"elo": 1000}}
        win_probs = {"prob_a": 0.70, "prob_b": 0.30}
        result = calculate_upset_likelihood(stats_a, stats_b, win_probs)
        assert result["elo_difference"] == 150


class TestPredictMatchup:
    """Tests for the main predict_matchup function."""

    def test_returns_complete_prediction(self):
        """Should return all required prediction components."""
        stats_a = {
            "leaderboard": {"elo": 1050, "matches": 8},
            "stats": {"attack": 3.5, "defense": 2.5, "stamina": 3.0, "control": 3.0, "meta_impact": 3.0},
            "sub_metrics": {
                "attack": {"burst_finish_rate": 0.2, "pocket_finish_rate": 0.15, "extreme_finish_rate": 0.1},
                "defense": {"burst_resistance": 0.7, "pocket_resistance": 0.7, "extreme_resistance": 0.9},
                "stamina": {"spin_finish_win_rate": 0.4},
                "meta_impact": {"upset_rate": 0.1}
            }
        }
        stats_b = {
            "leaderboard": {"elo": 1000, "matches": 6},
            "stats": {"attack": 2.5, "defense": 3.5, "stamina": 3.0, "control": 3.0, "meta_impact": 2.5},
            "sub_metrics": {
                "attack": {"burst_finish_rate": 0.1, "pocket_finish_rate": 0.1, "extreme_finish_rate": 0.05},
                "defense": {"burst_resistance": 0.8, "pocket_resistance": 0.8, "extreme_resistance": 0.95},
                "stamina": {"spin_finish_win_rate": 0.5},
                "meta_impact": {"upset_rate": 0.2}
            }
        }

        result = predict_matchup(stats_a, stats_b)

        assert "win_probability" in result
        assert "outcome_breakdown" in result
        assert "confidence" in result
        assert "upset_likelihood" in result
        assert "stat_comparison" in result

    def test_stat_comparison_identifies_advantages(self):
        """Should correctly identify stat advantages."""
        stats_a = {
            "leaderboard": {"elo": 1000},
            "stats": {"attack": 4.0, "defense": 2.0, "stamina": 3.0, "control": 3.0, "meta_impact": 3.0}
        }
        stats_b = {
            "leaderboard": {"elo": 1000},
            "stats": {"attack": 2.0, "defense": 4.0, "stamina": 3.0, "control": 3.0, "meta_impact": 3.0}
        }

        result = predict_matchup(stats_a, stats_b)

        assert result["stat_comparison"]["attack"]["advantage"] == "bey_a"
        assert result["stat_comparison"]["defense"]["advantage"] == "bey_b"
        # Equal stats should show as tie
        assert result["stat_comparison"]["stamina"]["advantage"] == "tie"

    def test_handles_empty_stats(self):
        """Should handle Beys with minimal stats."""
        stats_a = {}
        stats_b = {}

        result = predict_matchup(stats_a, stats_b)

        assert "win_probability" in result
        # Should default to approximately 50-50
        assert abs(result["win_probability"]["prob_a"] - 0.5) < 0.1
