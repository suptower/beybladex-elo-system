#!/usr/bin/env python3
"""
Test script for challonge_scraper.py

Tests the core functionality of the Challonge scraper without requiring network access.
"""

import sys
import os

# Add scripts directory to path
script_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts')
sys.path.insert(0, script_dir)

from challonge_scraper import ChallongeScraper
from bs4 import BeautifulSoup


def test_extract_tournament_id():
    """Test tournament ID extraction"""
    scraper1 = ChallongeScraper('https://challonge.com/om3hx2e9')
    assert scraper1.tournament_id == 'om3hx2e9', f"Expected 'om3hx2e9', got '{scraper1.tournament_id}'"
    
    scraper2 = ChallongeScraper('om3hx2e9')
    assert scraper2.tournament_id == 'om3hx2e9', f"Expected 'om3hx2e9', got '{scraper2.tournament_id}'"
    
    scraper3 = ChallongeScraper('https://challonge.com/zjbg6ab3/')
    assert scraper3.tournament_id == 'zjbg6ab3', f"Expected 'zjbg6ab3', got '{scraper3.tournament_id}'"
    
    print("✓ test_extract_tournament_id passed")


def test_extract_score():
    """Test score extraction from text"""
    scraper = ChallongeScraper('test')
    
    assert scraper._extract_score('5') == 5
    assert scraper._extract_score('10') == 10
    assert scraper._extract_score('Score: 3') == 3
    assert scraper._extract_score('(4)') == 4
    assert scraper._extract_score('abc') == 0
    assert scraper._extract_score('') == 0
    
    print("✓ test_extract_score passed")


def test_map_to_beyblade_names():
    """Test mapping player names to Beyblade names"""
    scraper = ChallongeScraper('test')
    
    bey_list = ['FoxBrush', 'ImpactDrake', 'DranSword', 'ViperTail']
    
    # Exact match
    assert scraper.map_to_beyblade_names('FoxBrush', bey_list) == 'FoxBrush'
    
    # Case-insensitive match
    assert scraper.map_to_beyblade_names('foxbrush', bey_list) == 'FoxBrush'
    assert scraper.map_to_beyblade_names('FOXBRUSH', bey_list) == 'FoxBrush'
    assert scraper.map_to_beyblade_names('dransword', bey_list) == 'DranSword'
    
    # Partial match
    assert scraper.map_to_beyblade_names('Fox', bey_list) == 'FoxBrush'
    
    # No match - return original
    assert scraper.map_to_beyblade_names('Unknown', bey_list) == 'Unknown'
    
    print("✓ test_map_to_beyblade_names passed")


def test_parse_match_element():
    """Test parsing match elements from HTML"""
    scraper = ChallongeScraper('test')
    
    # Create mock HTML for a match
    html = """
    <div class="match">
        <span class="player">FoxBrush</span>
        <span class="player">DranSword</span>
        <span class="score">5</span>
        <span class="score">3</span>
    </div>
    """
    
    soup = BeautifulSoup(html, 'html.parser')
    match_elem = soup.find('div', class_='match')
    
    match_data = scraper._parse_match_element(match_elem)
    
    assert match_data is not None, "Match data should not be None"
    assert match_data['player1'] == 'FoxBrush'
    assert match_data['player2'] == 'DranSword'
    assert match_data['score1'] == 5
    assert match_data['score2'] == 3
    
    print("✓ test_parse_match_element passed")


def test_csv_row_generation():
    """Test CSV row generation"""
    scraper = ChallongeScraper('test')
    
    matches = [
        {'player1': 'FoxBrush', 'player2': 'DranSword', 'score1': 5, 'score2': 3},
        {'player1': 'ImpactDrake', 'player2': 'ViperTail', 'score1': 4, 'score2': 2}
    ]
    
    # Create a temporary test file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        temp_file = f.name
    
    try:
        # Export with dry run to test without writing
        scraper.export_to_csv(matches, temp_file, tournament_date='2025-09-15', dry_run=True)
        print("✓ test_csv_row_generation passed")
    finally:
        # Clean up
        if os.path.exists(temp_file):
            os.remove(temp_file)


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("Running Challonge Scraper Tests")
    print("="*60 + "\n")
    
    try:
        test_extract_tournament_id()
        test_extract_score()
        test_map_to_beyblade_names()
        test_parse_match_element()
        test_csv_row_generation()
        
        print("\n" + "="*60)
        print("All tests passed! ✓")
        print("="*60 + "\n")
        return 0
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
