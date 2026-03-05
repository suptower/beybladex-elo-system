"""
Unit tests for archetype_analytics.py module.
Tests the archetype effectiveness analytics functions.
"""
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'analytics'))

from archetype_analytics import (
    calculate_archetype_stats,
    calculate_matchup_matrix,
    generate_meta_insights,
)


class TestCalculateArchetypeStats:
    """Tests for the calculate_archetype_stats function."""

    def test_basic_archetype_stats_calculation(self):
        """Test basic archetype stats calculation with valid data."""
        rpg_stats = {
            'BeyA': {
                'archetype': {
                    'id': 'glass_cannon',
                    'name': 'Glass Cannon',
                    'category': 'offense',
                    'icon': '💥',
                    'color': '#ef4444'
                }
            },
            'BeyB': {
                'archetype': {
                    'id': 'glass_cannon',
                    'name': 'Glass Cannon',
                    'category': 'offense',
                    'icon': '💥',
                    'color': '#ef4444'
                }
            }
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
            'M001': {'BeyA': 1000, 'BeyB': 1100}  # BeyA upset win
        }

        result = calculate_archetype_stats(rpg_stats, leaderboard, matches, elo_history)

        assert 'glass_cannon' in result
        assert result['glass_cannon']['bey_count'] == 2
        assert result['glass_cannon']['avg_elo'] > 0
        assert result['glass_cannon']['avg_winrate'] > 0

    def test_filters_unknown_archetypes(self):
        """Test that unknown archetypes are filtered out."""
        rpg_stats = {
            'BeyA': {
                'archetype': {
                    'id': 'unknown',
                    'name': 'Unknown',
                    'category': 'unknown',
                    'icon': '❓',
                    'color': '#6b7280'
                }
            },
            'BeyB': {
                'archetype': {
                    'id': 'glass_cannon',
                    'name': 'Glass Cannon',
                    'category': 'offense',
                    'icon': '💥',
                    'color': '#ef4444'
                }
            }
        }

        leaderboard = {
            'BeyA': {'elo': 1000, 'wins': 5, 'losses': 5, 'matches': 10, 'winrate': 0.5, 'avg_point_diff': 0},
            'BeyB': {'elo': 1100, 'wins': 7, 'losses': 3, 'matches': 10, 'winrate': 0.7, 'avg_point_diff': 1.0}
        }

        matches = []
        elo_history = {}

        result = calculate_archetype_stats(rpg_stats, leaderboard, matches, elo_history)

        assert 'unknown' not in result
        assert 'glass_cannon' in result

    def test_requires_minimum_matches(self):
        """Test that Beys with insufficient matches are filtered out."""
        rpg_stats = {
            'BeyA': {
                'archetype': {
                    'id': 'glass_cannon',
                    'name': 'Glass Cannon',
                    'category': 'offense',
                    'icon': '💥',
                    'color': '#ef4444'
                }
            }
        }

        leaderboard = {
            'BeyA': {'elo': 1000, 'wins': 1, 'losses': 1, 'matches': 2, 'winrate': 0.5, 'avg_point_diff': 0}
        }

        matches = []
        elo_history = {}

        result = calculate_archetype_stats(rpg_stats, leaderboard, matches, elo_history)

        # Should not include archetype with insufficient matches
        assert len(result) == 0

    def test_calculates_upset_rate_correctly(self):
        """Test that upset rate is calculated correctly."""
        rpg_stats = {
            'BeyA': {
                'archetype': {
                    'id': 'glass_cannon',
                    'name': 'Glass Cannon',
                    'category': 'offense',
                    'icon': '💥',
                    'color': '#ef4444'
                }
            }
        }

        leaderboard = {
            'BeyA': {'elo': 1100, 'wins': 10, 'losses': 0, 'matches': 10, 'winrate': 1.0, 'avg_point_diff': 2.0}
        }

        matches = [
            {'match_id': 'M001', 'winner': 'BeyA', 'loser': 'BeyB', 'winner_score': 4, 'loser_score': 2},
            {'match_id': 'M002', 'winner': 'BeyA', 'loser': 'BeyC', 'winner_score': 4, 'loser_score': 1},
        ]

        elo_history = {
            'M001': {'BeyA': 1000, 'BeyB': 1200},  # Upset win
            'M002': {'BeyA': 1100, 'BeyC': 1000},  # Not an upset
        }

        result = calculate_archetype_stats(rpg_stats, leaderboard, matches, elo_history)

        assert 'glass_cannon' in result
        assert result['glass_cannon']['upset_rate'] == 0.5  # 1 upset out of 2 matches


class TestCalculateMatchupMatrix:
    """Tests for the calculate_matchup_matrix function."""

    def test_basic_matchup_matrix_calculation(self):
        """Test basic matchup matrix calculation."""
        rpg_stats = {
            'BeyA': {
                'archetype': {
                    'id': 'glass_cannon',
                    'name': 'Glass Cannon',
                    'category': 'offense',
                    'icon': '💥',
                    'color': '#ef4444'
                }
            },
            'BeyB': {
                'archetype': {
                    'id': 'iron_wall',
                    'name': 'Iron Wall',
                    'category': 'defense',
                    'icon': '🛡️',
                    'color': '#3b82f6'
                }
            }
        }

        matches = [
            {'match_id': 'M001', 'winner': 'BeyA', 'loser': 'BeyB', 'winner_score': 4, 'loser_score': 2},
            {'match_id': 'M002', 'winner': 'BeyA', 'loser': 'BeyB', 'winner_score': 4, 'loser_score': 1},
            {'match_id': 'M003', 'winner': 'BeyB', 'loser': 'BeyA', 'winner_score': 4, 'loser_score': 2},
        ]

        elo_history = {}

        result = calculate_matchup_matrix(rpg_stats, matches, elo_history)

        assert 'glass_cannon' in result
        assert 'iron_wall' in result['glass_cannon']
        assert result['glass_cannon']['iron_wall']['total'] == 3
        assert result['glass_cannon']['iron_wall']['wins'] == 2
        assert abs(result['glass_cannon']['iron_wall']['winrate'] - 0.6667) < 0.01

    def test_filters_unknown_archetypes(self):
        """Test that matches with unknown archetypes are filtered out."""
        rpg_stats = {
            'BeyA': {
                'archetype': {
                    'id': 'glass_cannon',
                    'name': 'Glass Cannon',
                    'category': 'offense',
                    'icon': '💥',
                    'color': '#ef4444'
                }
            },
            'BeyB': {
                'archetype': {
                    'id': 'unknown',
                    'name': 'Unknown',
                    'category': 'unknown',
                    'icon': '❓',
                    'color': '#6b7280'
                }
            }
        }

        matches = [
            {'match_id': 'M001', 'winner': 'BeyA', 'loser': 'BeyB', 'winner_score': 4, 'loser_score': 2}
        ]

        elo_history = {}

        result = calculate_matchup_matrix(rpg_stats, matches, elo_history)

        # Should not include matchups with unknown archetypes
        assert len(result) == 0


class TestGenerateMetaInsights:
    """Tests for the generate_meta_insights function."""

    def test_identifies_dominant_archetype(self):
        """Test that dominant archetype is correctly identified."""
        archetype_stats = {
            'glass_cannon': {
                'id': 'glass_cannon',
                'name': 'Glass Cannon',
                'avg_elo': 1100,
                'avg_winrate': 0.65,
                'upset_rate': 0.3,
                'total_matches': 50
            },
            'iron_wall': {
                'id': 'iron_wall',
                'name': 'Iron Wall',
                'avg_elo': 1050,
                'avg_winrate': 0.55,
                'upset_rate': 0.2,
                'total_matches': 40
            }
        }

        matchup_matrix = {}

        result = generate_meta_insights(archetype_stats, matchup_matrix)

        assert result['dominant_archetype']['id'] == 'glass_cannon'
        assert result['dominant_archetype']['avg_elo'] == 1100

    def test_identifies_most_reliable(self):
        """Test that most reliable archetype is correctly identified."""
        archetype_stats = {
            'glass_cannon': {
                'id': 'glass_cannon',
                'name': 'Glass Cannon',
                'avg_elo': 1100,
                'avg_winrate': 0.65,
                'upset_rate': 0.4,  # High upset rate
                'total_matches': 50
            },
            'iron_wall': {
                'id': 'iron_wall',
                'name': 'Iron Wall',
                'avg_elo': 1050,
                'avg_winrate': 0.60,
                'upset_rate': 0.1,  # Low upset rate
                'total_matches': 40
            }
        }

        matchup_matrix = {}

        result = generate_meta_insights(archetype_stats, matchup_matrix)

        # Most reliable should be iron_wall (high winrate - low upset rate)
        assert result['most_reliable']['id'] == 'iron_wall'

    def test_identifies_most_volatile(self):
        """Test that most volatile archetype is correctly identified."""
        archetype_stats = {
            'glass_cannon': {
                'id': 'glass_cannon',
                'name': 'Glass Cannon',
                'avg_elo': 1100,
                'avg_winrate': 0.65,
                'upset_rate': 0.5,
                'total_matches': 50
            },
            'iron_wall': {
                'id': 'iron_wall',
                'name': 'Iron Wall',
                'avg_elo': 1050,
                'avg_winrate': 0.55,
                'upset_rate': 0.2,
                'total_matches': 40
            }
        }

        matchup_matrix = {}

        result = generate_meta_insights(archetype_stats, matchup_matrix)

        assert result['most_volatile']['id'] == 'glass_cannon'
        assert result['most_volatile']['upset_rate'] == 0.5

    def test_handles_empty_data(self):
        """Test that function handles empty data gracefully."""
        archetype_stats = {}
        matchup_matrix = {}

        result = generate_meta_insights(archetype_stats, matchup_matrix)

        assert result == {}

    def test_identifies_highest_winrate(self):
        """Test that highest winrate archetype is correctly identified."""
        archetype_stats = {
            'glass_cannon': {
                'id': 'glass_cannon',
                'name': 'Glass Cannon',
                'avg_elo': 1100,
                'avg_winrate': 0.75,  # Highest winrate
                'upset_rate': 0.3,
                'total_matches': 50
            },
            'iron_wall': {
                'id': 'iron_wall',
                'name': 'Iron Wall',
                'avg_elo': 1050,
                'avg_winrate': 0.55,
                'upset_rate': 0.2,
                'total_matches': 40
            }
        }

        matchup_matrix = {}

        result = generate_meta_insights(archetype_stats, matchup_matrix)

        assert result['highest_winrate']['id'] == 'glass_cannon'
        assert result['highest_winrate']['avg_winrate'] == 0.75

    def test_identifies_most_active(self):
        """Test that most active archetype is correctly identified."""
        archetype_stats = {
            'glass_cannon': {
                'id': 'glass_cannon',
                'name': 'Glass Cannon',
                'avg_elo': 1100,
                'avg_winrate': 0.65,
                'upset_rate': 0.3,
                'total_matches': 100  # Most matches
            },
            'iron_wall': {
                'id': 'iron_wall',
                'name': 'Iron Wall',
                'avg_elo': 1050,
                'avg_winrate': 0.55,
                'upset_rate': 0.2,
                'total_matches': 40
            }
        }

        matchup_matrix = {}

        result = generate_meta_insights(archetype_stats, matchup_matrix)

        assert result['most_active']['id'] == 'glass_cannon'
        assert result['most_active']['total_matches'] == 100
