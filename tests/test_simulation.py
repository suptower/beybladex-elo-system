"""
Unit tests for simulation.py module.
Tests the tournament simulation functions including expected scores,
match simulation, and tournament formats.
"""
import sys
import os
import random

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from datetime import date
from simulation import (
    expected_score,
    simulate_match,
    simulate_single_elimination,
    simulate_round_robin,
    DEFAULT_ELO
)


class TestExpectedScore:
    """Tests for the expected_score function."""

    def test_equal_ratings(self):
        """Equal ratings should give 0.5 expected score."""
        assert expected_score(1000, 1000) == 0.5
        assert expected_score(1500, 1500) == 0.5

    def test_higher_rating_favored(self):
        """Higher rated player should have expected score > 0.5."""
        result = expected_score(1200, 1000)
        assert result > 0.5
        assert result < 1.0

    def test_lower_rating_unfavored(self):
        """Lower rated player should have expected score < 0.5."""
        result = expected_score(1000, 1200)
        assert result < 0.5
        assert result > 0.0

    def test_400_point_difference(self):
        """400 point difference should give approximately 10:1 odds."""
        result = expected_score(1400, 1000)
        # 1 / (1 + 10^1) ≈ 0.909
        assert abs(result - 0.909) < 0.01

    def test_symmetry(self):
        """Expected scores of opponents should sum to 1."""
        e_a = expected_score(1200, 1000)
        e_b = expected_score(1000, 1200)
        assert abs(e_a + e_b - 1.0) < 0.0001


class TestSimulateMatch:
    """Tests for the simulate_match function."""

    def test_match_returns_valid_scores(self):
        """Match should return valid score tuple."""
        random.seed(42)
        score_a, score_b = simulate_match("BeyA", "BeyB", 1000, 1000)

        assert isinstance(score_a, int)
        assert isinstance(score_b, int)
        assert score_a >= 0
        assert score_b >= 0

    def test_match_has_winner(self):
        """One player should reach max_points."""
        random.seed(42)
        score_a, score_b = simulate_match("BeyA", "BeyB", 1000, 1000, max_points=5)

        # One player should have exactly 5 points (winner)
        assert score_a == 5 or score_b == 5
        # The other should have less than 5
        if score_a == 5:
            assert score_b < 5
        else:
            assert score_a < 5

    def test_match_deterministic_with_seed(self):
        """Same seed should produce same results."""
        random.seed(123)
        result1 = simulate_match("BeyA", "BeyB", 1000, 1000)

        random.seed(123)
        result2 = simulate_match("BeyA", "BeyB", 1000, 1000)

        assert result1 == result2

    def test_higher_elo_wins_more_often(self):
        """Higher ELO player should win more often over many matches."""
        random.seed(42)
        wins_high = 0
        wins_low = 0

        for _ in range(100):
            score_a, score_b = simulate_match("High", "Low", 1400, 1000)
            if score_a > score_b:
                wins_high += 1
            else:
                wins_low += 1

        # Higher rated should win significantly more
        assert wins_high > wins_low
        # With 400 point difference, should win ~75%+ of the time
        assert wins_high > 60

    def test_custom_max_points(self):
        """Custom max_points should be respected."""
        random.seed(42)
        score_a, score_b = simulate_match("BeyA", "BeyB", 1000, 1000, max_points=3)

        assert score_a == 3 or score_b == 3
        assert max(score_a, score_b) == 3


class TestSimulateSingleElimination:
    """Tests for single elimination tournament simulation."""

    def test_single_elimination_produces_matches(self):
        """Single elimination should produce matches."""
        random.seed(42)
        participants = ["Bey1", "Bey2", "Bey3", "Bey4"]
        elos = {bey: DEFAULT_ELO for bey in participants}

        matches = simulate_single_elimination(participants, elos, date(2024, 1, 1), verbose=False)

        assert len(matches) > 0

    def test_single_elimination_correct_match_count_power_of_two(self):
        """Power of 2 participants should have n-1 matches."""
        random.seed(42)
        participants = ["Bey1", "Bey2", "Bey3", "Bey4"]
        elos = {bey: DEFAULT_ELO for bey in participants}

        matches = simulate_single_elimination(participants, elos, date(2024, 1, 1), verbose=False)

        # 4 participants = 3 matches (2 semifinals + 1 final)
        assert len(matches) == 3

    def test_single_elimination_match_format(self):
        """Matches should have correct format (date, bey_a, bey_b, score_a, score_b)."""
        random.seed(42)
        participants = ["Bey1", "Bey2"]
        elos = {bey: DEFAULT_ELO for bey in participants}

        matches = simulate_single_elimination(participants, elos, date(2024, 1, 1), verbose=False)

        assert len(matches) == 1
        match = matches[0]
        assert len(match) == 5
        assert match[0] == "2024-01-01"  # Date
        assert match[1] in participants  # BeyA
        assert match[2] in participants  # BeyB
        assert isinstance(match[3], int)  # ScoreA
        assert isinstance(match[4], int)  # ScoreB

    def test_single_elimination_handles_odd_participants(self):
        """Single elimination should handle odd number of participants with byes."""
        random.seed(42)
        participants = ["Bey1", "Bey2", "Bey3"]
        elos = {bey: DEFAULT_ELO for bey in participants}

        matches = simulate_single_elimination(participants, elos, date(2024, 1, 1), verbose=False)

        # With 3 participants and a bye, we should have 2 matches
        assert len(matches) == 2


class TestSimulateRoundRobin:
    """Tests for round-robin tournament simulation."""

    def test_round_robin_produces_matches(self):
        """Round robin should produce matches."""
        random.seed(42)
        participants = ["Bey1", "Bey2", "Bey3"]
        elos = {bey: DEFAULT_ELO for bey in participants}

        matches = simulate_round_robin(participants, elos, date(2024, 1, 1), verbose=False)

        assert len(matches) > 0

    def test_round_robin_correct_match_count(self):
        """Round robin should have n*(n-1)/2 matches."""
        random.seed(42)
        participants = ["Bey1", "Bey2", "Bey3", "Bey4"]
        elos = {bey: DEFAULT_ELO for bey in participants}

        matches = simulate_round_robin(participants, elos, date(2024, 1, 1), verbose=False)

        # 4 participants: 4*3/2 = 6 matches
        assert len(matches) == 6

    def test_round_robin_all_pairs_play(self):
        """Every pair of participants should play exactly once."""
        random.seed(42)
        participants = ["Bey1", "Bey2", "Bey3"]
        elos = {bey: DEFAULT_ELO for bey in participants}

        matches = simulate_round_robin(participants, elos, date(2024, 1, 1), verbose=False)

        # Collect all pairs that played
        pairs = set()
        for match in matches:
            pair = frozenset([match[1], match[2]])
            pairs.add(pair)

        # Should have all 3 possible pairs
        expected_pairs = {
            frozenset(["Bey1", "Bey2"]),
            frozenset(["Bey1", "Bey3"]),
            frozenset(["Bey2", "Bey3"])
        }
        assert pairs == expected_pairs

    def test_round_robin_match_format(self):
        """Matches should have correct format."""
        random.seed(42)
        participants = ["Bey1", "Bey2"]
        elos = {bey: DEFAULT_ELO for bey in participants}

        matches = simulate_round_robin(participants, elos, date(2024, 1, 1), verbose=False)

        assert len(matches) == 1
        match = matches[0]
        assert len(match) == 5
        assert match[0] == "2024-01-01"
        assert isinstance(match[3], int)
        assert isinstance(match[4], int)
