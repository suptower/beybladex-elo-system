"""
Unit tests for beyblade_elo.py module.
Tests the ELO calculation functions including K-factor, expected scores,
ELO updates, and winrate calculations.
"""
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from collections import defaultdict
from beyblade_elo import (
    dynamic_k,
    expected,
    calculate_score_with_dominance,
    update_elo,
    calculate_winrates,
    K_LEARNING,
    K_INTERMEDIATE,
    K_EXPERIENCED,
    START_ELO
)


class TestDynamicK:
    """Tests for the dynamic_k function that calculates K-factor based on match count."""

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


class TestExpected:
    """Tests for the expected function that calculates expected score."""

    def test_equal_ratings(self):
        """Equal ratings should give 0.5 expected score."""
        assert expected(1000, 1000) == 0.5
        assert expected(1500, 1500) == 0.5

    def test_higher_rating_favored(self):
        """Higher rated player should have expected score > 0.5."""
        result = expected(1200, 1000)
        assert result > 0.5
        assert result < 1.0

    def test_lower_rating_unfavored(self):
        """Lower rated player should have expected score < 0.5."""
        result = expected(1000, 1200)
        assert result < 0.5
        assert result > 0.0

    def test_400_point_difference(self):
        """400 point difference should give approximately 10:1 odds."""
        result = expected(1400, 1000)
        # 1 / (1 + 10^1) ≈ 0.909
        assert abs(result - 0.909) < 0.01

    def test_symmetry(self):
        """Expected scores of opponents should sum to 1."""
        e_a = expected(1200, 1000)
        e_b = expected(1000, 1200)
        assert abs(e_a + e_b - 1.0) < 0.0001


class TestScoreWithDominance:
    """Tests for the calculate_score_with_dominance function."""

    def test_close_match_4_3(self):
        """Close 4-3 match should give small dominance bonus."""
        s_a, s_b = calculate_score_with_dominance(4, 3)
        # Point diff = 1, dominance_bonus = 0.1
        # Winner gets 0.5 + 0.1 = 0.6
        assert abs(s_a - 0.8125) < 0.01
        assert abs(s_b - 0.1875) < 0.01
        assert abs(s_a + s_b - 1.0) < 0.0001

    def test_moderate_win_4_2(self):
        """Moderate 4-2 win should give medium dominance bonus."""
        s_a, s_b = calculate_score_with_dominance(4, 2)
        # Point diff = 2, dominance_bonus = 0.25
        # Winner gets 0.5 + 0.25 = 0.75
        assert abs(s_a - 0.875) < 0.01
        assert abs(s_b - 0.125) < 0.01
        assert abs(s_a + s_b - 1.0) < 0.0001

    def test_strong_win_4_1(self):
        """Strong 4-1 win should give large dominance bonus."""
        s_a, s_b = calculate_score_with_dominance(4, 1)
        # Point diff = 3, dominance_bonus = 0.375
        # Winner gets 0.5 + 0.375 = 0.875
        assert abs(s_a - 0.9375) < 0.01
        assert abs(s_b - 0.0625) < 0.01
        assert abs(s_a + s_b - 1.0) < 0.0001

    def test_dominant_win_4_0(self):
        """Dominant 4-0 win should give maximum score."""
        s_a, s_b = calculate_score_with_dominance(4, 0)
        # Point diff = 4, dominance_bonus = 0.5
        # Winner gets 0.5 + 0.5 = 1.0
        assert abs(s_a - 1.0) < 0.0001
        assert abs(s_b - 0.0) < 0.0001
        assert abs(s_a + s_b - 1.0) < 0.0001

    def test_overwhelming_win_5_0(self):
        """Overwhelming 5-0 win should give maximum score."""
        s_a, s_b = calculate_score_with_dominance(5, 0)
        # Point diff = 5, dominance_bonus = 0.5 (capped at WIN_THRESHOLD)
        # Winner gets 0.5 + 0.5 = 1.0
        assert abs(s_a - 1.125) < 0.0001
        assert abs(s_b + 0.125) < 0.0001
        assert abs(s_a + s_b - 1.0) < 0.0001

    def test_overwhelming_win_6_0(self):
        """Overwhelming 6-0 win should give maximum score."""
        s_a, s_b = calculate_score_with_dominance(6, 0)
        # Point diff = 6, dominance_bonus = 0.5 (capped at WIN_THRESHOLD)
        # Winner gets 0.5 + 0.5 = 1.0
        assert abs(s_a - 1.25) < 0.0001
        assert abs(s_b + 0.25) < 0.0001
        assert abs(s_a + s_b - 1.0) < 0.0001

    def test_loser_perspective(self):
        """Test that loser (second argument) wins work correctly."""
        s_a, s_b = calculate_score_with_dominance(2, 4)
        # Point diff = 2, dominance_bonus = 0.25
        # Winner (B) gets 0.5 + 0.25 = 0.75
        # Loser (A) gets 0.25
        assert abs(s_a - 0.125) < 0.01
        assert abs(s_b - 0.875) < 0.01
        assert abs(s_a + s_b - 1.0) < 0.0001

    def test_zero_zero_draw(self):
        """0-0 draw should give equal scores."""
        s_a, s_b = calculate_score_with_dominance(0, 0)
        assert s_a == 0.5
        assert s_b == 0.5

    def test_tie_score(self):
        """Equal scores should give 0.5 to each player."""
        s_a, s_b = calculate_score_with_dominance(3, 3)
        assert s_a == 0.5
        assert s_b == 0.5

    def test_scores_sum_to_one(self):
        """All score combinations should sum to 1.0."""
        test_cases = [
            (4, 3), (4, 2), (4, 1), (4, 0),
            (5, 0), (6, 0), (5, 2), (3, 5)
        ]
        for sa, sb in test_cases:
            s_a, s_b = calculate_score_with_dominance(sa, sb)
            assert abs(s_a + s_b - 1.0) < 0.0001, f"Failed for {sa}-{sb}"

    def test_base_win_value_present(self):
        """Winner should always get at least 0.5 (base win value)."""
        test_cases = [(4, 3), (5, 4), (6, 5)]
        for sa, sb in test_cases:
            s_a, s_b = calculate_score_with_dominance(sa, sb)
            assert s_a >= 0.5, "Winner should get at least 0.5"

    def test_larger_differential_gives_higher_score(self):
        """Larger point differential should give higher score to winner."""
        s_a_4_3, _ = calculate_score_with_dominance(4, 3)
        s_a_4_2, _ = calculate_score_with_dominance(4, 2)
        s_a_4_0, _ = calculate_score_with_dominance(4, 0)

        # Winner's score should increase with larger differential
        assert s_a_4_3 < s_a_4_2 < s_a_4_0


class TestUpdateElo:
    """Tests for the update_elo function that updates ratings after a match."""

    def _create_test_data(self):
        """Helper to create test data structures."""
        elos = defaultdict(lambda: START_ELO)
        stats = defaultdict(lambda: {
            "wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0, "winrate": 0.0
        })
        return elos, stats

    def test_winner_gains_elo(self):
        """Winner should gain ELO points."""
        elos, stats = self._create_test_data()
        elos["BeyA"] = 1000
        elos["BeyB"] = 1000

        update_elo("BeyA", "BeyB", 5, 3, "2024-01-01", elos, stats)

        assert elos["BeyA"] > 1000  # Winner gained
        assert elos["BeyB"] < 1000  # Loser lost

    def test_loser_loses_elo(self):
        """Loser should lose ELO points."""
        elos, stats = self._create_test_data()
        elos["BeyA"] = 1000
        elos["BeyB"] = 1000

        update_elo("BeyA", "BeyB", 2, 5, "2024-01-01", elos, stats)

        assert elos["BeyA"] < 1000  # Loser lost
        assert elos["BeyB"] > 1000  # Winner gained

    def test_stats_updated(self):
        """Match stats should be properly updated."""
        elos, stats = self._create_test_data()
        elos["BeyA"] = 1000
        elos["BeyB"] = 1000

        update_elo("BeyA", "BeyB", 5, 3, "2024-01-01", elos, stats)

        # Check BeyA stats
        assert stats["BeyA"]["matches"] == 1
        assert stats["BeyA"]["wins"] == 1
        assert stats["BeyA"]["losses"] == 0
        assert stats["BeyA"]["for"] == 5
        assert stats["BeyA"]["against"] == 3

        # Check BeyB stats
        assert stats["BeyB"]["matches"] == 1
        assert stats["BeyB"]["wins"] == 0
        assert stats["BeyB"]["losses"] == 1
        assert stats["BeyB"]["for"] == 3
        assert stats["BeyB"]["against"] == 5

    def test_elo_conservation_approximately(self):
        """Total ELO change should be roughly zero for equal K-factors."""
        elos, stats = self._create_test_data()
        elos["BeyA"] = 1000
        elos["BeyB"] = 1000

        initial_total = elos["BeyA"] + elos["BeyB"]
        update_elo("BeyA", "BeyB", 5, 3, "2024-01-01", elos, stats)
        final_total = elos["BeyA"] + elos["BeyB"]

        # With equal K-factors, total should be roughly conserved
        assert abs(initial_total - final_total) < 1

    def test_zero_total_score_no_update(self):
        """A match with 0-0 score should not update anything."""
        elos, stats = self._create_test_data()
        elos["BeyA"] = 1000
        elos["BeyB"] = 1000

        update_elo("BeyA", "BeyB", 0, 0, "2024-01-01", elos, stats)

        assert elos["BeyA"] == 1000
        assert elos["BeyB"] == 1000

    def test_upset_victory(self):
        """Lower rated player winning should gain more ELO."""
        elos1, stats1 = self._create_test_data()
        elos1["BeyA"] = 1200
        elos1["BeyB"] = 1000

        elos2, stats2 = self._create_test_data()
        elos2["BeyC"] = 1000
        elos2["BeyD"] = 1000

        # Lower rated wins
        update_elo("BeyA", "BeyB", 3, 5, "2024-01-01", elos1, stats1)
        # Equal rated match
        update_elo("BeyC", "BeyD", 3, 5, "2024-01-01", elos2, stats2)

        # BeyB (underdog) gained more than BeyD (equal match)
        gain_underdog = elos1["BeyB"] - 1000
        gain_equal = elos2["BeyD"] - 1000
        assert gain_underdog > gain_equal

    def test_dominance_affects_elo_gain(self):
        """More dominant wins should result in larger ELO gains."""
        # Test three equal-rated matches with different dominance levels
        elos_close, stats_close = self._create_test_data()
        elos_close["BeyA"] = 1000
        elos_close["BeyB"] = 1000

        elos_moderate, stats_moderate = self._create_test_data()
        elos_moderate["BeyC"] = 1000
        elos_moderate["BeyD"] = 1000

        elos_dominant, stats_dominant = self._create_test_data()
        elos_dominant["BeyE"] = 1000
        elos_dominant["BeyF"] = 1000

        # Close win: 4-3 (point diff = 1, dominance_bonus = 0.1)
        update_elo("BeyA", "BeyB", 4, 3, "2024-01-01", elos_close, stats_close)

        # Moderate win: 4-2 (point diff = 2, dominance_bonus = 0.25)
        update_elo("BeyC", "BeyD", 4, 2, "2024-01-01", elos_moderate, stats_moderate)

        # Dominant win: 4-0 (point diff = 4, dominance_bonus = 0.5)
        update_elo("BeyE", "BeyF", 4, 0, "2024-01-01", elos_dominant, stats_dominant)

        # Calculate ELO gains
        gain_close = elos_close["BeyA"] - 1000
        gain_moderate = elos_moderate["BeyC"] - 1000
        gain_dominant = elos_dominant["BeyE"] - 1000

        # More dominant wins should result in larger ELO gains
        assert gain_close < gain_moderate < gain_dominant, \
            f"Expected gains to increase with dominance: {gain_close} < {gain_moderate} < {gain_dominant}"

    def test_4_0_and_above_give_maximum_gain(self):
        """4-0, 5-0, and 6-0 wins should all give maximum ELO gain."""
        elos_4_0, stats_4_0 = self._create_test_data()
        elos_4_0["BeyA"] = 1000
        elos_4_0["BeyB"] = 1000

        elos_5_0, stats_5_0 = self._create_test_data()
        elos_5_0["BeyC"] = 1000
        elos_5_0["BeyD"] = 1000

        elos_6_0, stats_6_0 = self._create_test_data()
        elos_6_0["BeyE"] = 1000
        elos_6_0["BeyF"] = 1000

        # 4-0 win (point diff = 4)
        update_elo("BeyA", "BeyB", 4, 0, "2024-01-01", elos_4_0, stats_4_0)

        # 5-0 win (point diff = 5)
        update_elo("BeyC", "BeyD", 5, 0, "2024-01-01", elos_5_0, stats_5_0)

        # 6-0 win (point diff = 6)
        update_elo("BeyE", "BeyF", 6, 0, "2024-01-01", elos_6_0, stats_6_0)


class TestCalculateWinrates:
    """Tests for the calculate_winrates function."""

    def test_perfect_winrate(self):
        """Player with all wins should have winrate of 1.0."""
        stats = {
            "BeyA": {"wins": 10, "losses": 0, "for": 0, "against": 0, "matches": 10, "winrate": 0.0}
        }
        calculate_winrates(stats)
        assert stats["BeyA"]["winrate"] == 1.0

    def test_zero_winrate(self):
        """Player with all losses should have winrate of 0.0."""
        stats = {
            "BeyA": {"wins": 0, "losses": 10, "for": 0, "against": 0, "matches": 10, "winrate": 0.0}
        }
        calculate_winrates(stats)
        assert stats["BeyA"]["winrate"] == 0.0

    def test_fifty_percent_winrate(self):
        """Player with equal wins/losses should have winrate of 0.5."""
        stats = {
            "BeyA": {"wins": 5, "losses": 5, "for": 0, "against": 0, "matches": 10, "winrate": 0.0}
        }
        calculate_winrates(stats)
        assert stats["BeyA"]["winrate"] == 0.5

    def test_no_matches_winrate(self):
        """Player with no matches should have winrate of 0.0."""
        stats = {
            "BeyA": {"wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0, "winrate": 0.0}
        }
        calculate_winrates(stats)
        assert stats["BeyA"]["winrate"] == 0.0

    def test_multiple_players(self):
        """Winrate calculation should work for multiple players."""
        stats = {
            "BeyA": {"wins": 8, "losses": 2, "for": 0, "against": 0, "matches": 10, "winrate": 0.0},
            "BeyB": {"wins": 3, "losses": 7, "for": 0, "against": 0, "matches": 10, "winrate": 0.0}
        }
        calculate_winrates(stats)
        assert stats["BeyA"]["winrate"] == 0.8
        assert stats["BeyB"]["winrate"] == 0.3
