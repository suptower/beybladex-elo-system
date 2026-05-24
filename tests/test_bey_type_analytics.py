"""
Unit tests for bey_type_analytics.py module.
Tests the native bey type effectiveness analytics functions.
"""
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'analytics'))

from bey_type_analytics import (
    calculate_type_stats,
    calculate_matchup_matrix,
    generate_meta_insights,
    MIN_MATCHES_FOR_TYPE,
)


class TestCalculateTypeStats:
    """Tests for the calculate_type_stats function."""

    def test_basic_type_stats_calculation(self):
        """Test basic type stats calculation with valid data."""
        bey_types = {
            'BeyA': 'attack',
            'BeyB': 'attack',
        }

        leaderboard = {
            'BeyA': {
                'elo': 1100,
                'wins': 7,
                'losses': 3,
                'matches': 10,
                'winrate': 0.7,
                'avg_point_diff': 1.5
            },
            'BeyB': {
                'elo': 1050,
                'wins': 5,
                'losses': 5,
                'matches': 10,
                'winrate': 0.5,
                'avg_point_diff': 0.5
            }
        }

        matches = [
            {'match_id': 'M001', 'winner': 'BeyA', 'loser': 'BeyB', 'winner_score': 4, 'loser_score': 2}
        ]

        elo_history = {
            'M001': {'BeyA': 1000, 'BeyB': 1100}
        }

        result = calculate_type_stats(bey_types, leaderboard, matches, elo_history)

        assert 'attack' in result
        assert result['attack']['bey_count'] == 2
        assert result['attack']['avg_elo'] > 0

    def test_filters_unknown_types(self):
        """Test that unknown types are filtered out."""
        bey_types = {
            'BeyA': 'unknown',
            'BeyB': 'defense',
        }

        leaderboard = {
            'BeyA': {'elo': 1000, 'wins': 5, 'losses': 5, 'matches': 10, 'winrate': 0.5, 'avg_point_diff': 0},
            'BeyB': {'elo': 1100, 'wins': 7, 'losses': 3, 'matches': 10, 'winrate': 0.7, 'avg_point_diff': 1.0}
        }

        matches = []
        elo_history = {}

        result = calculate_type_stats(bey_types, leaderboard, matches, elo_history)

        assert 'unknown' not in result
        assert 'defense' in result

    def test_requires_minimum_matches(self):
        """Test that Beys with insufficient matches are filtered out."""
        bey_types = {
            'BeyA': 'attack',
        }

        leaderboard = {
            'BeyA': {'elo': 1000, 'wins': 1, 'losses': 1, 'matches': MIN_MATCHES_FOR_TYPE - 1, 'winrate': 0.5, 'avg_point_diff': 0}
        }

        matches = []
        elo_history = {}

        result = calculate_type_stats(bey_types, leaderboard, matches, elo_history)

        assert len(result) == 0


class TestCalculateMatchupMatrix:
    """Tests for the calculate_matchup_matrix function."""

    def test_basic_matchup_matrix_calculation(self):
        """Test basic matchup matrix calculation."""
        bey_types = {
            'BeyA': 'attack',
            'BeyB': 'defense',
        }

        matches = [
            {'match_id': 'M001', 'winner': 'BeyA', 'loser': 'BeyB', 'winner_score': 4, 'loser_score': 2},
            {'match_id': 'M002', 'winner': 'BeyA', 'loser': 'BeyB', 'winner_score': 4, 'loser_score': 1},
            {'match_id': 'M003', 'winner': 'BeyB', 'loser': 'BeyA', 'winner_score': 4, 'loser_score': 2},
        ]

        result = calculate_matchup_matrix(bey_types, matches)

        assert 'attack' in result
        assert 'defense' in result['attack']
        assert result['attack']['defense']['total'] == 3
        assert result['attack']['defense']['wins'] == 2
        assert abs(result['attack']['defense']['winrate'] - 0.6667) < 0.01


class TestGenerateMetaInsights:
    """Tests for the generate_meta_insights function."""

    def test_generates_insights(self):
        """Should generate meta insights from type stats."""
        type_stats = {
            'attack': {
                'id': 'attack',
                'name': 'Attack',
                'avg_elo': 1100,
                'avg_winrate': 0.6,
                'upset_rate': 0.2,
                'total_matches': 20
            },
            'defense': {
                'id': 'defense',
                'name': 'Defense',
                'avg_elo': 1000,
                'avg_winrate': 0.5,
                'upset_rate': 0.1,
                'total_matches': 10
            }
        }

        matchup_matrix = {}
        insights = generate_meta_insights(type_stats, matchup_matrix)

        assert 'dominant_type' in insights
        assert insights['dominant_type']['id'] == 'attack'
