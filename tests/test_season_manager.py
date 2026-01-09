"""
Unit tests for season_manager.py module.
Tests season initialization, points calculation, league tables, and promotion/relegation logic.
"""
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from season_manager import (
    calculate_season_points,
    initialize_season,
    get_league_table,
    get_promotion_relegation,
    schedule_round_robin,
    POINTS_WIN,
    POINTS_DOMINANT_WIN,
    POINTS_LOSS,
    TIERS,
    BEYS_PER_TIER,
    AUTO_PROMOTION,
    AUTO_RELEGATION
)


class TestSeasonPointsCalculation:
    """Tests for season points calculation."""
    
    def test_regular_win(self):
        """Regular win should give 3 points to winner, 0 to loser."""
        sp_a, sp_b = calculate_season_points(4, 3)
        assert sp_a == POINTS_WIN
        assert sp_b == POINTS_LOSS
    
    def test_dominant_win_4_0(self):
        """4-0 win should be dominant (4 points)."""
        sp_a, sp_b = calculate_season_points(4, 0)
        assert sp_a == POINTS_DOMINANT_WIN
        assert sp_b == POINTS_LOSS
    
    def test_dominant_win_5_0(self):
        """5-0 win should be dominant (4 points)."""
        sp_a, sp_b = calculate_season_points(5, 0)
        assert sp_a == POINTS_DOMINANT_WIN
        assert sp_b == POINTS_LOSS
    
    def test_dominant_win_6_0(self):
        """6-0 win should be dominant (4 points)."""
        sp_a, sp_b = calculate_season_points(6, 0)
        assert sp_a == POINTS_DOMINANT_WIN
        assert sp_b == POINTS_LOSS
    
    def test_non_dominant_4_1(self):
        """4-1 win should not be dominant (3 points)."""
        sp_a, sp_b = calculate_season_points(4, 1)
        assert sp_a == POINTS_WIN
        assert sp_b == POINTS_LOSS
    
    def test_non_dominant_4_2(self):
        """4-2 win should not be dominant (3 points)."""
        sp_a, sp_b = calculate_season_points(4, 2)
        assert sp_a == POINTS_WIN
        assert sp_b == POINTS_LOSS
    
    def test_close_match(self):
        """Close match should give 3 points to winner."""
        sp_a, sp_b = calculate_season_points(4, 3)
        assert sp_a == POINTS_WIN
        assert sp_b == POINTS_LOSS
    
    def test_loser_perspective(self):
        """Loser always gets 0 points."""
        sp_a, sp_b = calculate_season_points(2, 5)
        assert sp_a == POINTS_LOSS
        assert sp_b == POINTS_WIN
    
    def test_draw(self):
        """Draw should give 0 points to both (edge case)."""
        sp_a, sp_b = calculate_season_points(3, 3)
        assert sp_a == 0
        assert sp_b == 0


class TestSeasonInitialization:
    """Tests for season initialization with tier assignments."""
    
    def test_initialize_season_basic(self):
        """Should create season with correct tier assignments."""
        beys = [(f"Bey{i}", 1500 - i * 10) for i in range(40)]
        season_data = initialize_season("S1", beys)
        
        assert season_data["season_id"] == "S1"
        assert season_data["status"] == "active"
        assert len(season_data["tier_assignments"]) == 40
    
    def test_tier_assignment_by_elo(self):
        """Beys should be assigned to tiers based on ELO ranking."""
        beys = [(f"Bey{i}", 2000 - i * 10) for i in range(40)]
        season_data = initialize_season("S1", beys)
        
        # Top 10 should be in Tier 1
        for i in range(10):
            bey_name = f"Bey{i}"
            assert season_data["tier_assignments"][bey_name]["tier"] == 1
        
        # Next 10 should be in Tier 2
        for i in range(10, 20):
            bey_name = f"Bey{i}"
            assert season_data["tier_assignments"][bey_name]["tier"] == 2
        
        # Beys 20-29 should be in Tier 3
        for i in range(20, 30):
            bey_name = f"Bey{i}"
            assert season_data["tier_assignments"][bey_name]["tier"] == 3
        
        # Bottom 10 should be in Tier 4
        for i in range(30, 40):
            bey_name = f"Bey{i}"
            assert season_data["tier_assignments"][bey_name]["tier"] == 4
    
    def test_invalid_bey_count(self):
        """Should raise error if not exactly 40 beys."""
        beys = [(f"Bey{i}", 1500) for i in range(30)]
        try:
            initialize_season("S1", beys)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Expected 40 beys" in str(e)


class TestLeagueTable:
    """Tests for league table generation."""
    
    def test_empty_table(self):
        """Empty matches should return empty table."""
        matches = []
        table = get_league_table(matches, 1, "S1")
        assert len(table) == 0
    
    def test_basic_table(self):
        """Should correctly calculate standings."""
        matches = [
            {
                "match_type": "season",
                "season_id": "S1",
                "tier": 1,
                "bey_a": "BeyA",
                "bey_b": "BeyB",
                "score_a": 4,
                "score_b": 0,
                "elo_a": 1500,
                "elo_b": 1400
            },
            {
                "match_type": "season",
                "season_id": "S1",
                "tier": 1,
                "bey_a": "BeyA",
                "bey_b": "BeyC",
                "score_a": 4,
                "score_b": 2,
                "elo_a": 1500,
                "elo_b": 1450
            }
        ]
        
        table = get_league_table(matches, 1, "S1")
        assert len(table) == 3  # BeyA, BeyB, BeyC
        
        # BeyA should be first (2 wins, 4+4=8 season points)
        assert table[0]["bey"] == "BeyA"
        assert table[0]["wins"] == 2
        assert table[0]["losses"] == 0
        assert table[0]["position"] == 1
    
    def test_table_sorting_by_season_points(self):
        """Table should be sorted by season points first."""
        matches = [
            {
                "match_type": "season",
                "season_id": "S1",
                "tier": 1,
                "bey_a": "Winner",
                "bey_b": "Loser",
                "score_a": 4,
                "score_b": 0,
                "elo_a": 1400,
                "elo_b": 1500
            }
        ]
        
        table = get_league_table(matches, 1, "S1")
        assert table[0]["bey"] == "Winner"
        assert table[0]["season_points"] == POINTS_DOMINANT_WIN
        assert table[1]["bey"] == "Loser"
        assert table[1]["season_points"] == POINTS_LOSS
    
    def test_point_difference_calculation(self):
        """Point difference should be calculated correctly."""
        matches = [
            {
                "match_type": "season",
                "season_id": "S1",
                "tier": 1,
                "bey_a": "BeyA",
                "bey_b": "BeyB",
                "score_a": 5,
                "score_b": 2,
                "elo_a": 1500,
                "elo_b": 1400
            }
        ]
        
        table = get_league_table(matches, 1, "S1")
        assert table[0]["point_diff"] == 3  # 5 - 2
        assert table[1]["point_diff"] == -3  # 2 - 5


class TestPromotionRelegation:
    """Tests for promotion and relegation logic."""
    
    def test_automatic_promotion(self):
        """Top 2 from Tier 2-4 should be promoted."""
        league_tables = {
            2: [
                {"bey": f"T2-Bey{i}", "position": i, "elo": 1400} 
                for i in range(1, 11)
            ]
        }
        
        season_data = {}
        pr = get_promotion_relegation(season_data, league_tables)
        
        # Should have 2 promotions from Tier 2
        tier2_promotions = [p for p in pr["automatic_promotion"] if p["from_tier"] == 2]
        assert len(tier2_promotions) == AUTO_PROMOTION
        assert tier2_promotions[0]["bey"] == "T2-Bey1"
        assert tier2_promotions[1]["bey"] == "T2-Bey2"
    
    def test_automatic_relegation(self):
        """Bottom 2 from Tier 1-3 should be relegated."""
        league_tables = {
            1: [
                {"bey": f"T1-Bey{i}", "position": i, "elo": 1500}
                for i in range(1, 11)
            ]
        }
        
        season_data = {}
        pr = get_promotion_relegation(season_data, league_tables)
        
        # Should have 2 relegations from Tier 1
        tier1_relegations = [r for r in pr["automatic_relegation"] if r["from_tier"] == 1]
        assert len(tier1_relegations) == AUTO_RELEGATION
        assert tier1_relegations[0]["bey"] == "T1-Bey10"
        assert tier1_relegations[1]["bey"] == "T1-Bey9"
    
    def test_relegation_matches(self):
        """8th vs 3rd relegation matches should be scheduled."""
        league_tables = {
            1: [{"bey": f"T1-Bey{i}", "position": i, "elo": 1500} for i in range(1, 11)],
            2: [{"bey": f"T2-Bey{i}", "position": i, "elo": 1400} for i in range(1, 11)]
        }
        
        season_data = {}
        pr = get_promotion_relegation(season_data, league_tables)
        
        # Should have relegation match between Tier 1 8th and Tier 2 3rd
        assert len(pr["relegation_matches"]) >= 1
        
        t1_t2_match = [m for m in pr["relegation_matches"] 
                      if m["higher_tier"] == 1 and m["lower_tier"] == 2]
        assert len(t1_t2_match) == 1
        assert t1_t2_match[0]["higher_bey"] == "T1-Bey8"
        assert t1_t2_match[0]["lower_bey"] == "T2-Bey3"


class TestRoundRobinScheduling:
    """Tests for round-robin match scheduling."""
    
    def test_schedule_10_beys(self):
        """10 beys should generate 45 matches (10 * 9 / 2)."""
        beys = [f"Bey{i}" for i in range(1, 11)]
        matches = schedule_round_robin(beys)
        assert len(matches) == 45
    
    def test_each_pair_once(self):
        """Each pair should meet exactly once."""
        beys = ["A", "B", "C", "D"]
        matches = schedule_round_robin(beys)
        
        # Convert to set of frozensets for comparison
        pairs = {frozenset([a, b]) for a, b in matches}
        
        # Should have 6 unique pairs
        assert len(pairs) == 6
        assert frozenset(["A", "B"]) in pairs
        assert frozenset(["A", "C"]) in pairs
        assert frozenset(["A", "D"]) in pairs
        assert frozenset(["B", "C"]) in pairs
        assert frozenset(["B", "D"]) in pairs
        assert frozenset(["C", "D"]) in pairs
    
    def test_empty_list(self):
        """Empty list should return no matches."""
        matches = schedule_round_robin([])
        assert len(matches) == 0
    
    def test_single_bey(self):
        """Single bey should return no matches."""
        matches = schedule_round_robin(["Bey1"])
        assert len(matches) == 0
