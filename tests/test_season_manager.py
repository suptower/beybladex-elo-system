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
    AUTO_PROMOTIONS_PER_TIER,
    AUTO_RELEGATIONS_PER_TIER
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
        season_data = initialize_season("S2", beys)

        assert season_data["season_id"] == "S2"
        assert season_data["status"] == "active"
        # 4-tier system: Top 32 in league, bottom 8 in qualification pool
        assert len(season_data["tier_assignments"]) == 32
        assert len(season_data.get("qualification_pool", [])) == 8

    def test_tier_assignment_by_elo(self):
        """Beys should be assigned to tiers based on ELO ranking."""
        beys = [(f"Bey{i}", 2000 - i * 10) for i in range(40)]
        season_data = initialize_season("S2", beys)

        # Top 8 should be in Tier 1
        for i in range(8):
            bey_name = f"Bey{i}"
            assert season_data["tier_assignments"][bey_name]["tier"] == 1

        # Next 8 should be in Tier 2
        for i in range(8, 16):
            bey_name = f"Bey{i}"
            assert season_data["tier_assignments"][bey_name]["tier"] == 2

        # Beys 16-23 should be in Tier 3
        for i in range(16, 24):
            bey_name = f"Bey{i}"
            assert season_data["tier_assignments"][bey_name]["tier"] == 3

        # Beys 24-31 should be in Tier 4
        for i in range(24, 32):
            bey_name = f"Bey{i}"
            assert season_data["tier_assignments"][bey_name]["tier"] == 4

        # Bottom 8 should be in qualification pool (not in tier assignments)
        qual_pool_beys = [entry["bey"] for entry in season_data.get("qualification_pool", [])]
        for i in range(32, 40):
            bey_name = f"Bey{i}"
            assert bey_name not in season_data["tier_assignments"]
            assert bey_name in qual_pool_beys

    def test_invalid_bey_count(self):
        """Exactly 32 beys should produce a full 4-tier league with no qualification pool."""
        beys = [(f"Bey{i}", 1500) for i in range(32)]
        season_data = initialize_season("S2", beys)
        assert len(season_data["tier_assignments"]) == 32
        assert len(season_data.get("qualification_pool", [])) == 0

    def test_initialize_season_legacy_s1(self):
        """S1 should use legacy 3×10 format: top 30 in league, rest in qualification pool."""
        beys = [(f"Bey{i}", 1500 - i * 10) for i in range(40)]
        season_data = initialize_season("S1", beys)

        assert season_data["season_id"] == "S1"
        # Legacy 3-tier system: Top 30 in league, bottom 10 in qualification pool
        assert len(season_data["tier_assignments"]) == 30
        assert len(season_data.get("qualification_pool", [])) == 10
        # Top 10 should be in Tier 1
        for i in range(10):
            assert season_data["tier_assignments"][f"Bey{i}"]["tier"] == 1


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
        """Tier II rank 1 should be promoted automatically; Tier III ranks 1-2 promoted."""
        league_tables = {
            2: [
                {"bey": f"T2-Bey{i}", "position": i, "elo": 1400}
                for i in range(1, 9)
            ],
            3: [
                {"bey": f"T3-Bey{i}", "position": i, "elo": 1300}
                for i in range(1, 9)
            ]
        }

        season_data = {}
        pr = get_promotion_relegation(season_data, league_tables)

        # Should have 1 auto-promotion from Tier 2 (rank 1 only)
        tier2_promotions = [p for p in pr["automatic_promotion"] if p["from_tier"] == 2]
        assert len(tier2_promotions) == AUTO_PROMOTIONS_PER_TIER[2]
        assert tier2_promotions[0]["bey"] == "T2-Bey1"

        # Should have 2 auto-promotions from Tier 3 (ranks 1-2)
        tier3_promotions = [p for p in pr["automatic_promotion"] if p["from_tier"] == 3]
        assert len(tier3_promotions) == AUTO_PROMOTIONS_PER_TIER[3]
        assert tier3_promotions[0]["bey"] == "T3-Bey1"
        assert tier3_promotions[1]["bey"] == "T3-Bey2"

    def test_automatic_relegation(self):
        """Tier I rank 8 should be relegated; Tier II ranks 7-8 relegated."""
        league_tables = {
            1: [
                {"bey": f"T1-Bey{i}", "position": i, "elo": 1500}
                for i in range(1, 9)
            ],
            2: [
                {"bey": f"T2-Bey{i}", "position": i, "elo": 1400}
                for i in range(1, 9)
            ]
        }

        season_data = {}
        pr = get_promotion_relegation(season_data, league_tables)

        # Should have 1 auto-relegation from Tier 1 (rank 8 only)
        tier1_relegations = [r for r in pr["automatic_relegation"] if r["from_tier"] == 1]
        assert len(tier1_relegations) == AUTO_RELEGATIONS_PER_TIER[1]
        assert tier1_relegations[0]["bey"] == "T1-Bey8"

        # Should have 2 auto-relegations from Tier 2 (ranks 7-8)
        tier2_relegations = [r for r in pr["automatic_relegation"] if r["from_tier"] == 2]
        assert len(tier2_relegations) == AUTO_RELEGATIONS_PER_TIER[2]
        assert tier2_relegations[0]["bey"] == "T2-Bey8"
        assert tier2_relegations[1]["bey"] == "T2-Bey7"

    def test_relegation_matches(self):
        """Playoff matches should be scheduled at correct positions."""
        league_tables = {
            1: [{"bey": f"T1-Bey{i}", "position": i, "elo": 1500} for i in range(1, 9)],
            2: [{"bey": f"T2-Bey{i}", "position": i, "elo": 1400} for i in range(1, 9)]
        }

        season_data = {}
        pr = get_promotion_relegation(season_data, league_tables)

        # Should have playoff match between Tier 1 rank 7 and Tier 2 rank 2
        t1_t2_match = [m for m in pr["relegation_matches"]
                       if m["higher_tier"] == 1 and m["lower_tier"] == 2]
        assert len(t1_t2_match) == 1
        assert t1_t2_match[0]["higher_bey"] == "T1-Bey7"
        assert t1_t2_match[0]["lower_bey"] == "T2-Bey2"

    def test_tier4_qualification_candidates(self):
        """Tier IV ranks 5-8 should enter qualification pool."""
        league_tables = {
            4: [{"bey": f"T4-Bey{i}", "position": i, "elo": 1200} for i in range(1, 9)]
        }

        season_data = {}
        pr = get_promotion_relegation(season_data, league_tables)

        # Positions 5-8 should be qualification candidates
        assert len(pr["qualification_candidates"]) == 4
        candidate_positions = [c["position"] for c in pr["qualification_candidates"]]
        assert 5 in candidate_positions
        assert 8 in candidate_positions


class TestRoundRobinScheduling:
    """Tests for round-robin match scheduling."""

    def test_schedule_8_beys(self):
        """8 beys should generate 28 matches (8 * 7 / 2)."""
        beys = [f"Bey{i}" for i in range(1, 9)]
        matches = schedule_round_robin(beys)
        assert len(matches) == 28

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
