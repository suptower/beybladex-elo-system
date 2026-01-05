"""
Unit tests for milestones.py module.
Tests milestone calculation functions.
"""
import sys
import os
import json

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from milestones import (
    calculate_streaks,
    calculate_total_wins,
    calculate_win_rates,
    calculate_finish_stats,
    calculate_elo_extremes,
    calculate_upset_stats,
    calculate_longevity_stats,
    calculate_stability,
    MIN_MATCHES_FOR_WINRATE
)


class TestCalculateStreaks:
    """Tests for streak calculation."""

    def test_win_streak_simple(self):
        """Test simple win streak calculation."""
        matches = [
            {'BeyA': 'BeyX', 'BeyB': 'BeyY', 'ScoreA': '4', 'ScoreB': '0'},
            {'BeyA': 'BeyX', 'BeyB': 'BeyZ', 'ScoreA': '4', 'ScoreB': '1'},
            {'BeyA': 'BeyX', 'BeyB': 'BeyY', 'ScoreA': '4', 'ScoreB': '2'},
        ]
        result = calculate_streaks(matches)
        assert result['longest_win_streak']['BeyX'] == 3

    def test_losing_streak_simple(self):
        """Test simple losing streak calculation."""
        matches = [
            {'BeyA': 'BeyX', 'BeyB': 'BeyY', 'ScoreA': '0', 'ScoreB': '4'},
            {'BeyA': 'BeyX', 'BeyB': 'BeyZ', 'ScoreA': '1', 'ScoreB': '4'},
            {'BeyA': 'BeyX', 'BeyB': 'BeyY', 'ScoreA': '0', 'ScoreB': '4'},
        ]
        result = calculate_streaks(matches)
        assert result['longest_losing_streak']['BeyX'] == 3

    def test_streak_reset_on_loss(self):
        """Test that win streak resets on loss."""
        matches = [
            {'BeyA': 'BeyX', 'BeyB': 'BeyY', 'ScoreA': '4', 'ScoreB': '0'},
            {'BeyA': 'BeyX', 'BeyB': 'BeyZ', 'ScoreA': '4', 'ScoreB': '1'},
            {'BeyA': 'BeyX', 'BeyB': 'BeyY', 'ScoreA': '0', 'ScoreB': '4'},
            {'BeyA': 'BeyX', 'BeyB': 'BeyZ', 'ScoreA': '4', 'ScoreB': '0'},
        ]
        result = calculate_streaks(matches)
        assert result['longest_win_streak']['BeyX'] == 2


class TestCalculateTotalWins:
    """Tests for total wins calculation."""

    def test_total_wins_single_bey(self):
        """Test total wins for a single Bey."""
        matches = [
            {'BeyA': 'BeyX', 'BeyB': 'BeyY', 'ScoreA': '4', 'ScoreB': '0'},
            {'BeyA': 'BeyX', 'BeyB': 'BeyZ', 'ScoreA': '4', 'ScoreB': '1'},
            {'BeyA': 'BeyY', 'BeyB': 'BeyX', 'ScoreA': '0', 'ScoreB': '4'},
        ]
        result = calculate_total_wins(matches)
        assert result['BeyX'] == 3

    def test_total_wins_multiple_beys(self):
        """Test total wins for multiple Beys."""
        matches = [
            {'BeyA': 'BeyX', 'BeyB': 'BeyY', 'ScoreA': '4', 'ScoreB': '0'},
            {'BeyA': 'BeyY', 'BeyB': 'BeyZ', 'ScoreA': '4', 'ScoreB': '1'},
            {'BeyA': 'BeyZ', 'BeyB': 'BeyX', 'ScoreA': '4', 'ScoreB': '0'},
        ]
        result = calculate_total_wins(matches)
        assert result['BeyX'] == 1
        assert result['BeyY'] == 1
        assert result['BeyZ'] == 1


class TestCalculateWinRates:
    """Tests for win rate calculation."""

    def test_win_rate_below_threshold(self):
        """Test that Beys below minimum match threshold are excluded."""
        matches = [
            {'BeyA': 'BeyX', 'BeyB': 'BeyY', 'ScoreA': '4', 'ScoreB': '0'},
            {'BeyA': 'BeyX', 'BeyB': 'BeyZ', 'ScoreA': '4', 'ScoreB': '1'},
        ]
        result = calculate_win_rates(matches)
        # BeyX only has 2 matches, below MIN_MATCHES_FOR_WINRATE (20)
        assert 'BeyX' not in result

    def test_win_rate_calculation(self):
        """Test win rate calculation for qualifying Beys."""
        # Create enough matches to meet threshold
        matches = []
        for i in range(MIN_MATCHES_FOR_WINRATE):
            score_a = '4' if i < MIN_MATCHES_FOR_WINRATE // 2 else '0'
            score_b = '0' if i < MIN_MATCHES_FOR_WINRATE // 2 else '4'
            matches.append({
                'BeyA': 'BeyX',
                'BeyB': f'BeyY{i}',
                'ScoreA': score_a,
                'ScoreB': score_b
            })
        
        result = calculate_win_rates(matches)
        assert 'BeyX' in result
        win_rate, total = result['BeyX']
        assert total == MIN_MATCHES_FOR_WINRATE
        assert win_rate == 50.0  # 50% win rate


class TestCalculateFinishStats:
    """Tests for finish statistics calculation."""

    def test_spin_finishes(self):
        """Test spin finish counting."""
        rounds = [
            {'winner': 'BeyX', 'finish_type': 'spin'},
            {'winner': 'BeyX', 'finish_type': 'spin'},
            {'winner': 'BeyY', 'finish_type': 'spin'},
        ]
        result = calculate_finish_stats(rounds)
        assert result['spin_finishes']['BeyX'] == 2
        assert result['spin_finishes']['BeyY'] == 1

    def test_finish_diversity(self):
        """Test finish diversity calculation."""
        rounds = [
            {'winner': 'BeyX', 'finish_type': 'spin'},
            {'winner': 'BeyX', 'finish_type': 'burst'},
            {'winner': 'BeyX', 'finish_type': 'pocket'},
            {'winner': 'BeyX', 'finish_type': 'extreme'},
            {'winner': 'BeyY', 'finish_type': 'spin'},
        ]
        result = calculate_finish_stats(rounds)
        assert result['finish_diversity']['BeyX'] == 100.0  # All 4 types
        assert result['finish_diversity']['BeyY'] == 0.0  # Only 1 type


class TestCalculateEloExtremes:
    """Tests for ELO extremes calculation."""

    def test_highest_elo(self):
        """Test highest ELO tracking."""
        elo_history = [
            {'BeyA': 'BeyX', 'BeyB': 'BeyY', 'PostA': '1050', 'PostB': '950'},
            {'BeyA': 'BeyX', 'BeyB': 'BeyZ', 'PostA': '1080', 'PostB': '970'},
            {'BeyA': 'BeyX', 'BeyB': 'BeyY', 'PostA': '1040', 'PostB': '960'},
        ]
        result = calculate_elo_extremes(elo_history)
        assert result['highest_elo_ever']['BeyX'] == 1080

    def test_biggest_upclimb(self):
        """Test continuous upclimb calculation."""
        elo_history = [
            {'BeyA': 'BeyX', 'BeyB': 'BeyY', 'PostA': '950', 'PostB': '1050'},
            {'BeyA': 'BeyX', 'BeyB': 'BeyZ', 'PostA': '980', 'PostB': '1020'},
            {'BeyA': 'BeyX', 'BeyB': 'BeyY', 'PostA': '1030', 'PostB': '1000'},
        ]
        result = calculate_elo_extremes(elo_history)
        assert 'BeyX' in result['biggest_upclimb']
        climb, from_elo, to_elo = result['biggest_upclimb']['BeyX']
        assert climb == 80  # 950 to 1030

    def test_biggest_downfall(self):
        """Test continuous downfall calculation."""
        elo_history = [
            {'BeyA': 'BeyX', 'BeyB': 'BeyY', 'PostA': '1050', 'PostB': '950'},
            {'BeyA': 'BeyX', 'BeyB': 'BeyZ', 'PostA': '1020', 'PostB': '980'},
            {'BeyA': 'BeyX', 'BeyB': 'BeyY', 'PostA': '970', 'PostB': '1030'},
        ]
        result = calculate_elo_extremes(elo_history)
        assert 'BeyX' in result['biggest_downfall']
        fall, from_elo, to_elo = result['biggest_downfall']['BeyX']
        assert fall == 80  # 1050 to 970


class TestCalculateLongevityStats:
    """Tests for longevity statistics calculation."""

    def test_matches_played(self):
        """Test counting total matches played."""
        matches = [
            {'BeyA': 'BeyX', 'BeyB': 'BeyY', 'Date': '2025-01-01'},
            {'BeyA': 'BeyX', 'BeyB': 'BeyZ', 'Date': '2025-01-01'},
            {'BeyA': 'BeyY', 'BeyB': 'BeyX', 'Date': '2025-01-02'},
        ]
        result = calculate_longevity_stats(matches)
        assert result['most_matches_played']['BeyX'] == 3
        assert result['most_matches_played']['BeyY'] == 2


class TestCalculateStability:
    """Tests for stability calculation."""

    def test_stability_calculation(self):
        """Test ELO variance calculation."""
        elo_history = [
            {'BeyA': 'BeyX', 'BeyB': 'BeyY', 'PostA': '1000', 'PostB': '1000'},
            {'BeyA': 'BeyX', 'BeyB': 'BeyZ', 'PostA': '1010', 'PostB': '990'},
            {'BeyA': 'BeyX', 'BeyB': 'BeyY', 'PostA': '990', 'PostB': '1010'},
        ]
        result = calculate_stability(elo_history)
        assert 'BeyX' in result
        # Low variance means more stable
        assert result['BeyX'] < 200  # Should have low variance

    def test_minimum_matches_for_stability(self):
        """Test that stability requires at least 2 matches."""
        elo_history = [
            {'BeyA': 'BeyX', 'BeyB': 'BeyY', 'PostA': '1000', 'PostB': '1000'},
        ]
        result = calculate_stability(elo_history)
        # BeyX only has 1 ELO value, not enough for variance
        assert 'BeyX' not in result


class TestMilestonesOutput:
    """Integration tests for milestones output format."""

    def test_milestones_json_structure(self):
        """Test that generated milestones.json has expected structure."""
        milestones_file = './docs/data/milestones.json'
        
        if not os.path.exists(milestones_file):
            # Skip if file doesn't exist (not yet generated)
            return
        
        with open(milestones_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check top-level categories exist
        assert 'match_and_win_records' in data
        assert 'finish_specialists' in data
        assert 'elo_performance_extremes' in data
        assert 'upsets_and_clutch' in data
        assert 'consistency_and_longevity' in data
        assert 'metadata' in data
        
        # Check specific milestones exist
        assert 'longest_win_streak' in data['match_and_win_records']
        assert 'most_spin_finishes' in data['finish_specialists']
        assert 'highest_elo_ever' in data['elo_performance_extremes']
        assert 'best_upsetter' in data['upsets_and_clutch']
        assert 'most_matches_played' in data['consistency_and_longevity']
        
    def test_milestone_entries_have_required_fields(self):
        """Test that milestone entries have bey and value fields."""
        milestones_file = './docs/data/milestones.json'
        
        if not os.path.exists(milestones_file):
            return
        
        with open(milestones_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check a few milestone entries
        win_streak = data['match_and_win_records']['longest_win_streak']
        if len(win_streak) > 0:
            entry = win_streak[0]
            assert 'bey' in entry
            assert 'value' in entry
