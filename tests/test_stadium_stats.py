"""
Tests for stadium_stats.py module
"""

import os
import json
import pytest
from src.stadium_stats import (
    normalize_stadium_name,
    load_matches,
    load_elo_history,
    load_rounds,
    calculate_stadium_overview,
    calculate_bey_performance_per_stadium,
    calculate_archetype_effectiveness_per_stadium,
    calculate_finish_type_statistics_per_stadium,
    calculate_elo_behavior_per_stadium,
    calculate_comparative_analysis
)


class TestStadiumNameNormalization:
    """Test stadium name normalization."""
    
    def test_normalize_xtreme(self):
        assert normalize_stadium_name("Xtreme") == "Xtreme Stadium"
        assert normalize_stadium_name("xtreme") == "Xtreme Stadium"
    
    def test_normalize_drop_attack(self):
        assert normalize_stadium_name("Drop Attack") == "Drop Attack Beystadium"
        assert normalize_stadium_name("DropAttack") == "Drop Attack Beystadium"
        assert normalize_stadium_name("drop_attack") == "Drop Attack Beystadium"
    
    def test_normalize_empty(self):
        assert normalize_stadium_name("") == "Xtreme Stadium"
        assert normalize_stadium_name(None) == "Xtreme Stadium"
    
    def test_normalize_unknown(self):
        assert normalize_stadium_name("Unknown Stadium") == "Unknown Stadium"


class TestDataLoading:
    """Test data loading functions."""
    
    def test_load_matches(self):
        """Test that matches load correctly with arena information."""
        matches = load_matches()
        assert isinstance(matches, list)
        assert len(matches) > 0
        
        # Check first match has required fields
        first_match = matches[0]
        assert 'match_id' in first_match
        assert 'bey_a' in first_match
        assert 'bey_b' in first_match
        assert 'score_a' in first_match
        assert 'score_b' in first_match
        assert 'stadium' in first_match
        
        # Stadium should be normalized
        assert first_match['stadium'] in ['Xtreme Stadium', 'Drop Attack Beystadium']
    
    def test_load_elo_history(self):
        """Test ELO history loading with arena column."""
        history = load_elo_history()
        assert isinstance(history, list)
        assert len(history) > 0
        
        first_entry = history[0]
        assert 'stadium' in first_entry
        assert 'old_elo_a' in first_entry
        assert 'new_elo_a' in first_entry
        assert isinstance(first_entry['old_elo_a'], float)
    
    def test_load_rounds(self):
        """Test rounds loading."""
        rounds = load_rounds()
        assert isinstance(rounds, list)
        # Rounds file exists, so should have data
        if len(rounds) > 0:
            first_round = rounds[0]
            assert 'match_id' in first_round
            assert 'finish_type' in first_round
            assert 'points_awarded' in first_round


class TestStadiumOverview:
    """Test stadium overview calculations."""
    
    def test_calculate_stadium_overview(self):
        """Test stadium overview calculation."""
        matches = load_matches()
        elo_history = load_elo_history()
        
        overview = calculate_stadium_overview(matches, elo_history)
        
        assert isinstance(overview, dict)
        assert len(overview) > 0
        
        # Check first stadium has required fields
        first_stadium = list(overview.values())[0]
        assert 'total_matches' in first_stadium
        assert 'average_match_score' in first_stadium
        assert 'match_score_distribution' in first_stadium
        assert first_stadium['total_matches'] > 0
        
        # Check distribution stats
        dist = first_stadium['match_score_distribution']
        assert 'min' in dist
        assert 'max' in dist
        assert 'median' in dist
        assert dist['min'] <= dist['max']


class TestBeyPerformance:
    """Test Bey performance calculations."""
    
    def test_calculate_bey_performance(self):
        """Test bey performance per stadium."""
        matches = load_matches()
        elo_history = load_elo_history()
        
        performance = calculate_bey_performance_per_stadium(matches, elo_history)
        
        assert isinstance(performance, dict)
        
        # Find first non-rankings key
        stadiums = [k for k in performance.keys() if not k.endswith('_rankings')]
        assert len(stadiums) > 0
        
        first_stadium = stadiums[0]
        stadium_data = performance[first_stadium]
        
        # Check there's bey data
        assert len(stadium_data) > 0
        
        # Check first bey has required stats
        first_bey = list(stadium_data.values())[0]
        assert 'matches' in first_bey
        assert 'wins' in first_bey
        assert 'losses' in first_bey
        assert 'winrate' in first_bey
        assert 'avg_elo_change' in first_bey
        assert 0 <= first_bey['winrate'] <= 1
    
    def test_rankings_generated(self):
        """Test that rankings are generated."""
        matches = load_matches()
        elo_history = load_elo_history()
        
        performance = calculate_bey_performance_per_stadium(matches, elo_history)
        
        # Check rankings exist
        rankings_keys = [k for k in performance.keys() if k.endswith('_rankings')]
        assert len(rankings_keys) > 0
        
        first_rankings = performance[rankings_keys[0]]
        assert 'best_performers' in first_rankings
        assert 'worst_performers' in first_rankings


class TestArchetypeEffectiveness:
    """Test archetype effectiveness calculations."""
    
    def test_calculate_archetype_effectiveness(self):
        """Test archetype effectiveness per stadium."""
        matches = load_matches()
        
        # Try to load RPG stats
        try:
            with open('./docs/data/rpg_stats.json', 'r') as f:
                rpg_stats = json.load(f)
        except FileNotFoundError:
            pytest.skip("RPG stats file not available")
        
        effectiveness = calculate_archetype_effectiveness_per_stadium(matches, rpg_stats)
        
        assert isinstance(effectiveness, dict)
        
        # If there's data, check structure
        if len(effectiveness) > 0:
            first_stadium = list(effectiveness.keys())[0]
            stadium_data = effectiveness[first_stadium]
            
            if len(stadium_data) > 0:
                first_archetype = list(stadium_data.values())[0]
                assert 'matches' in first_archetype
                assert 'wins' in first_archetype
                assert 'winrate' in first_archetype
                assert 'avg_dominance' in first_archetype


class TestFinishTypeStats:
    """Test finish type statistics."""
    
    def test_calculate_finish_stats(self):
        """Test finish type statistics calculation."""
        matches = load_matches()
        rounds = load_rounds()
        
        if len(rounds) == 0:
            pytest.skip("No rounds data available")
        
        finish_stats = calculate_finish_type_statistics_per_stadium(matches, rounds)
        
        assert isinstance(finish_stats, dict)
        assert len(finish_stats) > 0
        
        first_stadium = list(finish_stats.values())[0]
        assert 'finish_counts' in first_stadium
        assert 'finish_percentages' in first_stadium
        assert 'total_rounds' in first_stadium
        
        # Check percentages add up to ~100
        percentages = first_stadium['finish_percentages']
        total_pct = sum(percentages.values())
        assert 99 <= total_pct <= 101  # Allow small rounding errors


class TestEloBehavior:
    """Test ELO behavior calculations."""
    
    def test_calculate_elo_behavior(self):
        """Test ELO behavior per stadium."""
        elo_history = load_elo_history()
        
        behavior = calculate_elo_behavior_per_stadium(elo_history)
        
        assert isinstance(behavior, dict)
        assert len(behavior) > 0
        
        first_stadium = list(behavior.values())[0]
        assert 'avg_elo_change' in first_stadium
        assert 'elo_volatility' in first_stadium
        assert 'upset_frequency' in first_stadium
        assert 'dominant_win_frequency' in first_stadium
        
        # Check reasonable ranges
        assert first_stadium['avg_elo_change'] >= 0
        assert first_stadium['elo_volatility'] >= 0
        assert 0 <= first_stadium['upset_frequency'] <= 100
        assert 0 <= first_stadium['dominant_win_frequency'] <= 100


class TestComparativeAnalysis:
    """Test comparative analysis."""
    
    def test_comparative_analysis_structure(self):
        """Test that comparative analysis has correct structure."""
        matches = load_matches()
        elo_history = load_elo_history()
        rounds = load_rounds()
        
        # Load RPG stats
        try:
            with open('./docs/data/rpg_stats.json', 'r') as f:
                rpg_stats = json.load(f)
        except FileNotFoundError:
            rpg_stats = {}
        
        bey_performance = calculate_bey_performance_per_stadium(matches, elo_history)
        archetype_effectiveness = calculate_archetype_effectiveness_per_stadium(matches, rpg_stats)
        finish_stats = calculate_finish_type_statistics_per_stadium(matches, rounds)
        elo_behavior = calculate_elo_behavior_per_stadium(elo_history)
        
        comparisons = calculate_comparative_analysis(
            bey_performance, 
            archetype_effectiveness, 
            finish_stats, 
            elo_behavior
        )
        
        assert isinstance(comparisons, list)
        
        # If comparisons exist, check structure
        if len(comparisons) > 0:
            first_comp = comparisons[0]
            assert 'stadium_a' in first_comp
            assert 'stadium_b' in first_comp
            assert 'bey_winrate_deltas' in first_comp
            assert 'archetype_shifts' in first_comp
            assert 'finish_type_shifts' in first_comp
            assert 'elo_volatility_delta' in first_comp


class TestStadiumAnalyticsJSON:
    """Test that the generated JSON file is valid."""
    
    def test_stadium_analytics_file_exists(self):
        """Test that stadium_analytics.json is generated."""
        assert os.path.exists('./docs/data/stadium_analytics.json')
    
    def test_stadium_analytics_valid_json(self):
        """Test that the file contains valid JSON."""
        with open('./docs/data/stadium_analytics.json', 'r') as f:
            data = json.load(f)
        
        assert isinstance(data, dict)
        assert 'generated_at' in data
        assert 'stadium_overview' in data
        assert 'bey_performance' in data
        assert 'archetype_effectiveness' in data
        assert 'finish_type_statistics' in data
        assert 'elo_behavior' in data
        assert 'comparative_analysis' in data
    
    def test_stadium_analytics_has_data(self):
        """Test that the analytics contain actual data."""
        with open('./docs/data/stadium_analytics.json', 'r') as f:
            data = json.load(f)
        
        # Should have at least one stadium
        assert len(data['stadium_overview']) > 0
        
        # Should have at least Xtreme Stadium
        stadiums = list(data['stadium_overview'].keys())
        assert any('Xtreme' in s for s in stadiums)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
