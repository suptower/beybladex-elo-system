"""
Unit tests for beyblade_elo.py module.
Tests the ELO calculation functions including K-factor, expected scores,
ELO updates, and winrate calculations.
"""
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from collections import defaultdict
from beyblade_elo import (
    dynamic_k,
    expected,
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
