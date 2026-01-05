"""
Unit tests for matchup_matrix.py module.
Tests the Matchup Matrix functionality for Bey-vs-Bey analysis.
"""
import sys
import os
import json
import csv
import tempfile
import shutil

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from matchup_matrix import (
    calculate_matchup_matrix,
    build_matrix_output,
    identify_hard_counters,
)


class TestMatchupMatrix:
    """Tests for matchup matrix calculation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Sample match data
        self.sample_matches = [
            {'BeyA': 'BeyX', 'BeyB': 'BeyY', 'ScoreA': '4', 'ScoreB': '2'},
            {'BeyA': 'BeyX', 'BeyB': 'BeyY', 'ScoreA': '3', 'ScoreB': '5'},
            {'BeyA': 'BeyX', 'BeyB': 'BeyZ', 'ScoreA': '5', 'ScoreB': '0'},
            {'BeyA': 'BeyY', 'BeyB': 'BeyZ', 'ScoreA': '4', 'ScoreB': '1'},
            {'BeyA': 'BeyY', 'BeyB': 'BeyZ', 'ScoreA': '3', 'ScoreB': '2'},
        ]
        
        # Sample metadata
        self.sample_elo_map = {
            'BeyX': 1500,
            'BeyY': 1450,
            'BeyZ': 1400
        }
        
        self.sample_tier_map = {
            'BeyX': 'S',
            'BeyY': 'A',
            'BeyZ': 'B'
        }
        
        self.sample_archetype_map = {
            'BeyX': 'Attacker',
            'BeyY': 'Defender',
            'BeyZ': 'Stamina'
        }
    
    def test_calculate_matchup_matrix_basic(self):
        """Test basic matchup matrix calculation."""
        matrix = calculate_matchup_matrix(self.sample_matches)
        
        # Check that all beys are in the matrix
        assert 'BeyX' in matrix
        assert 'BeyY' in matrix
        assert 'BeyZ' in matrix
        
        # Check BeyX vs BeyY matchup (1-1 record)
        assert matrix['BeyX']['BeyY']['wins'] == 1
        assert matrix['BeyX']['BeyY']['losses'] == 1
        assert matrix['BeyX']['BeyY']['total_matches'] == 2
    
    def test_calculate_matchup_matrix_symmetric(self):
        """Test that matchup matrix is symmetric."""
        matrix = calculate_matchup_matrix(self.sample_matches)
        
        # BeyX vs BeyY should be inverse of BeyY vs BeyX
        assert matrix['BeyX']['BeyY']['wins'] == matrix['BeyY']['BeyX']['losses']
        assert matrix['BeyX']['BeyY']['losses'] == matrix['BeyY']['BeyX']['wins']
        assert matrix['BeyX']['BeyY']['total_matches'] == matrix['BeyY']['BeyX']['total_matches']
    
    def test_calculate_matchup_matrix_scores(self):
        """Test score tracking in matchup matrix."""
        matrix = calculate_matchup_matrix(self.sample_matches)
        
        # Check score tracking for BeyX vs BeyY
        # BeyX: 4+3=7 scored, 2+5=7 conceded
        assert matrix['BeyX']['BeyY']['score_for'] == 7
        assert matrix['BeyX']['BeyY']['score_against'] == 7
    
    def test_calculate_matchup_matrix_no_ties(self):
        """Test that ties are ignored."""
        matches_with_tie = self.sample_matches + [
            {'BeyA': 'BeyX', 'BeyB': 'BeyY', 'ScoreA': '3', 'ScoreB': '3'}
        ]
        
        matrix = calculate_matchup_matrix(matches_with_tie)
        
        # Tie should not affect match count
        assert matrix['BeyX']['BeyY']['total_matches'] == 2
    
    def test_build_matrix_output_structure(self):
        """Test output structure of build_matrix_output."""
        matchup_data = calculate_matchup_matrix(self.sample_matches)
        output = build_matrix_output(
            matchup_data,
            self.sample_elo_map,
            self.sample_tier_map,
            self.sample_archetype_map
        )
        
        # Check output structure
        assert 'beys' in output
        assert 'matrix' in output
        assert isinstance(output['beys'], list)
        assert isinstance(output['matrix'], dict)
    
    def test_build_matrix_output_beys_list(self):
        """Test beys list in output."""
        matchup_data = calculate_matchup_matrix(self.sample_matches)
        output = build_matrix_output(
            matchup_data,
            self.sample_elo_map,
            self.sample_tier_map,
            self.sample_archetype_map
        )
        
        # Check beys list has correct structure
        assert len(output['beys']) == 3
        
        for bey in output['beys']:
            assert 'name' in bey
            assert 'elo' in bey
            assert 'tier' in bey
            assert 'archetype' in bey
    
    def test_build_matrix_output_winrate_calculation(self):
        """Test winrate calculation in output matrix."""
        matchup_data = calculate_matchup_matrix(self.sample_matches)
        output = build_matrix_output(
            matchup_data,
            self.sample_elo_map,
            self.sample_tier_map,
            self.sample_archetype_map
        )
        
        # BeyX vs BeyY: 1 win out of 2 matches = 0.5 winrate
        assert output['matrix']['BeyX']['BeyY']['winrate'] == 0.5
        assert output['matrix']['BeyX']['BeyY']['matches'] == 2
    
    def test_build_matrix_output_avg_diff_calculation(self):
        """Test average point differential calculation."""
        matchup_data = calculate_matchup_matrix(self.sample_matches)
        output = build_matrix_output(
            matchup_data,
            self.sample_elo_map,
            self.sample_tier_map,
            self.sample_archetype_map
        )
        
        # BeyX vs BeyY: (4-2) + (3-5) = 2 - 2 = 0, avg = 0
        assert output['matrix']['BeyX']['BeyY']['avg_diff'] == 0.0
        
        # BeyX vs BeyZ: (5-0) = 5, avg = 5
        assert output['matrix']['BeyX']['BeyZ']['avg_diff'] == 5.0
    
    def test_build_matrix_output_self_matchup(self):
        """Test self-matchup handling."""
        matchup_data = calculate_matchup_matrix(self.sample_matches)
        output = build_matrix_output(
            matchup_data,
            self.sample_elo_map,
            self.sample_tier_map,
            self.sample_archetype_map
        )
        
        # Self-matchup should have None values
        assert output['matrix']['BeyX']['BeyX']['winrate'] is None
        assert output['matrix']['BeyX']['BeyX']['matches'] == 0
        assert output['matrix']['BeyX']['BeyX']['avg_diff'] is None
    
    def test_build_matrix_output_no_matchup(self):
        """Test handling of beys that never faced each other."""
        # Add a bey that never played
        extended_matches = self.sample_matches.copy()
        matchup_data = calculate_matchup_matrix(extended_matches)
        
        # Add a new bey with no matches against others
        matchup_data['BeyNew'] = {}
        
        extended_elo = {**self.sample_elo_map, 'BeyNew': 1500}
        extended_tier = {**self.sample_tier_map, 'BeyNew': 'C'}
        extended_archetype = {**self.sample_archetype_map, 'BeyNew': 'Unknown'}
        
        output = build_matrix_output(
            matchup_data,
            extended_elo,
            extended_tier,
            extended_archetype
        )
        
        # BeyNew vs BeyX should have no data
        assert output['matrix']['BeyNew']['BeyX']['winrate'] is None
        assert output['matrix']['BeyNew']['BeyX']['matches'] == 0
    
    def test_identify_hard_counters_basic(self):
        """Test hard counter identification."""
        # Create matchup data with a clear hard counter
        matches = [
            {'BeyA': 'Counter', 'BeyB': 'Target', 'ScoreA': '5', 'ScoreB': '0'},
            {'BeyA': 'Counter', 'BeyB': 'Target', 'ScoreA': '4', 'ScoreB': '1'},
            {'BeyA': 'Counter', 'BeyB': 'Target', 'ScoreA': '5', 'ScoreB': '1'},
            {'BeyA': 'Counter', 'BeyB': 'Target', 'ScoreA': '5', 'ScoreB': '2'},
            {'BeyA': 'Counter', 'BeyB': 'Target', 'ScoreA': '4', 'ScoreB': '0'},
        ]
        
        matchup_data = calculate_matchup_matrix(matches)
        elo_map = {'Counter': 1500, 'Target': 1450}
        tier_map = {'Counter': 'S', 'Target': 'A'}
        archetype_map = {'Counter': 'Attacker', 'Target': 'Defender'}
        
        output = build_matrix_output(matchup_data, elo_map, tier_map, archetype_map)
        hard_counters = identify_hard_counters(output, min_matches=5, winrate_threshold=0.7)
        
        # Should identify Counter as hard counter to Target
        assert len(hard_counters) > 0
        assert hard_counters[0]['counter'] == 'Counter'
        assert hard_counters[0]['counters'] == 'Target'
        assert hard_counters[0]['winrate'] == 1.0
    
    def test_identify_hard_counters_min_matches(self):
        """Test minimum match threshold for hard counters."""
        # Create matchup with high winrate but few matches
        matches = [
            {'BeyA': 'BeyA', 'BeyB': 'BeyB', 'ScoreA': '5', 'ScoreB': '0'},
            {'BeyA': 'BeyA', 'BeyB': 'BeyB', 'ScoreA': '4', 'ScoreB': '1'},
        ]
        
        matchup_data = calculate_matchup_matrix(matches)
        elo_map = {'BeyA': 1500, 'BeyB': 1450}
        tier_map = {'BeyA': 'S', 'BeyB': 'A'}
        archetype_map = {'BeyA': 'Attacker', 'BeyB': 'Defender'}
        
        output = build_matrix_output(matchup_data, elo_map, tier_map, archetype_map)
        
        # Should not identify as hard counter (only 2 matches, need 5)
        hard_counters = identify_hard_counters(output, min_matches=5, winrate_threshold=0.7)
        assert len(hard_counters) == 0
    
    def test_identify_hard_counters_threshold(self):
        """Test winrate threshold for hard counters."""
        # Create matchup with moderate winrate
        matches = [
            {'BeyA': 'BeyA', 'BeyB': 'BeyB', 'ScoreA': '5', 'ScoreB': '0'},
            {'BeyA': 'BeyA', 'BeyB': 'BeyB', 'ScoreA': '4', 'ScoreB': '1'},
            {'BeyA': 'BeyA', 'BeyB': 'BeyB', 'ScoreA': '3', 'ScoreB': '5'},
            {'BeyA': 'BeyA', 'BeyB': 'BeyB', 'ScoreA': '4', 'ScoreB': '1'},
            {'BeyA': 'BeyA', 'BeyB': 'BeyB', 'ScoreA': '5', 'ScoreB': '2'},
        ]
        
        matchup_data = calculate_matchup_matrix(matches)
        elo_map = {'BeyA': 1500, 'BeyB': 1450}
        tier_map = {'BeyA': 'S', 'BeyB': 'A'}
        archetype_map = {'BeyA': 'Attacker', 'BeyB': 'Defender'}
        
        output = build_matrix_output(matchup_data, elo_map, tier_map, archetype_map)
        
        # 4 wins out of 5 = 80% winrate
        hard_counters = identify_hard_counters(output, min_matches=5, winrate_threshold=0.7)
        assert len(hard_counters) > 0
        
        # Should not pass higher threshold
        hard_counters_high = identify_hard_counters(output, min_matches=5, winrate_threshold=0.9)
        assert len(hard_counters_high) == 0
