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
    get_tier_adaptation,
    schedule_round_robin,
    POINTS_WIN,
    POINTS_DOMINANT_WIN,
    POINTS_LOSS,
    AUTO_PROMOTION,
    AUTO_RELEGATION,
    TIERS,
    BEYS_PER_TIER,
    TOTAL_BEYS_IN_LEAGUE,
    RELEGATION_MATCH_POSITION_HIGH,
    QUALIFICATION_SLOTS
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
        beys = [(f"Bey{i}", 1500 - i * 10) for i in range(42)]
        season_data = initialize_season("S2", beys)

        assert season_data["season_id"] == "S2"
        assert season_data["status"] == "active"
        # 4-tier system: Top 32 in league, remaining in qualification pool
        assert len(season_data["tier_assignments"]) == TOTAL_BEYS_IN_LEAGUE
        assert len(season_data.get("qualification_pool", [])) == 42 - TOTAL_BEYS_IN_LEAGUE

    def test_tier_assignment_by_elo(self):
        """Beys should be assigned to tiers based on ELO ranking."""
        beys = [(f"Bey{i}", 2000 - i * 10) for i in range(TOTAL_BEYS_IN_LEAGUE + 8)]
        season_data = initialize_season("S2", beys)

        # Top BEYS_PER_TIER should be in Tier 1
        for i in range(BEYS_PER_TIER):
            bey_name = f"Bey{i}"
            assert season_data["tier_assignments"][bey_name]["tier"] == 1

        # Next BEYS_PER_TIER should be in Tier 2
        for i in range(BEYS_PER_TIER, 2 * BEYS_PER_TIER):
            bey_name = f"Bey{i}"
            assert season_data["tier_assignments"][bey_name]["tier"] == 2

        # Next BEYS_PER_TIER should be in Tier 3
        for i in range(2 * BEYS_PER_TIER, 3 * BEYS_PER_TIER):
            bey_name = f"Bey{i}"
            assert season_data["tier_assignments"][bey_name]["tier"] == 3

        # Next BEYS_PER_TIER should be in Tier 4
        for i in range(3 * BEYS_PER_TIER, TOTAL_BEYS_IN_LEAGUE):
            bey_name = f"Bey{i}"
            assert season_data["tier_assignments"][bey_name]["tier"] == 4

        # Remaining should be in qualification pool (not in tier assignments)
        qual_pool_beys = [entry["bey"] for entry in season_data.get("qualification_pool", [])]
        for i in range(TOTAL_BEYS_IN_LEAGUE, TOTAL_BEYS_IN_LEAGUE + 8):
            bey_name = f"Bey{i}"
            assert bey_name not in season_data["tier_assignments"]
            assert bey_name in qual_pool_beys

    def test_invalid_bey_count(self):
        """Should not raise error for exactly TOTAL_BEYS_IN_LEAGUE beys."""
        beys = [(f"Bey{i}", 1500) for i in range(TOTAL_BEYS_IN_LEAGUE)]
        season_data = initialize_season("S2", beys)
        assert len(season_data["tier_assignments"]) == TOTAL_BEYS_IN_LEAGUE
        assert len(season_data.get("qualification_pool", [])) == 0


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
                for i in range(1, BEYS_PER_TIER + 1)
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
                for i in range(1, BEYS_PER_TIER + 1)
            ]
        }

        season_data = {}
        pr = get_promotion_relegation(season_data, league_tables)

        # Should have 2 relegations from Tier 1
        tier1_relegations = [r for r in pr["automatic_relegation"] if r["from_tier"] == 1]
        assert len(tier1_relegations) == AUTO_RELEGATION
        assert tier1_relegations[0]["bey"] == f"T1-Bey{BEYS_PER_TIER}"
        assert tier1_relegations[1]["bey"] == f"T1-Bey{BEYS_PER_TIER - 1}"

    def test_relegation_matches(self):
        """RELEGATION_MATCH_POSITION_HIGH vs 3rd relegation matches should be scheduled."""
        league_tables = {
            1: [{"bey": f"T1-Bey{i}", "position": i, "elo": 1500}
                for i in range(1, BEYS_PER_TIER + 1)],
            2: [{"bey": f"T2-Bey{i}", "position": i, "elo": 1400}
                for i in range(1, BEYS_PER_TIER + 1)]
        }

        season_data = {}
        pr = get_promotion_relegation(season_data, league_tables)

        # Should have relegation match between Tier 1 RELEGATION_MATCH_POSITION_HIGH and Tier 2 3rd
        assert len(pr["relegation_matches"]) >= 1

        t1_t2_match = [m for m in pr["relegation_matches"]
                       if m["higher_tier"] == 1 and m["lower_tier"] == 2]
        assert len(t1_t2_match) == 1
        assert t1_t2_match[0]["higher_bey"] == f"T1-Bey{RELEGATION_MATCH_POSITION_HIGH}"
        assert t1_t2_match[0]["lower_bey"] == "T2-Bey3"


class TestRoundRobinScheduling:
    """Tests for round-robin match scheduling."""

    def test_schedule_8_beys(self):
        """8 beys should generate 28 matches (8 * 7 / 2)."""
        beys = [f"Bey{i}" for i in range(1, BEYS_PER_TIER + 1)]
        matches = schedule_round_robin(beys)
        assert len(matches) == BEYS_PER_TIER * (BEYS_PER_TIER - 1) // 2

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


class TestTierAdaptation:
    """Tests for get_tier_adaptation – handling cross-season structure changes."""

    def _make_table(self, tier: int, count: int, elo_base: int = 1000) -> list:
        """Helper: create a simple league table for a tier."""
        return [
            {"bey": f"T{tier}-Bey{i}", "position": i, "elo": elo_base - i * 10}
            for i in range(1, count + 1)
        ]

    def test_basic_adaptation_3x10_to_4x8(self):
        """Transitioning from 3 tiers of 10 to 4 tiers of 8.

        The old league has 30 beys but the new structure has 32 slots.
        All 30 old beys are assigned; the 2 vacant slots will be filled
        by qualification tournament winners.
        """
        old_tables = {
            1: self._make_table(1, 10, 1500),
            2: self._make_table(2, 10, 1400),
            3: self._make_table(3, 10, 1300),
        }
        result = get_tier_adaptation(old_tables, new_tiers=4, new_beys_per_tier=8)
        # All 30 beys from the old league are placed; none overflow to qualification
        assert result["total_beys_assigned"] == 30
        assert len(result["new_tier_assignments"]) == 30
        assert len(result["qualification_pool"]) == 0

    def test_adaptation_assigns_top_beys_to_tier1(self):
        """Top 8 beys (T1-Bey1..8) should be assigned to new Tier 1."""
        old_tables = {
            1: self._make_table(1, 10, 1500),
            2: self._make_table(2, 10, 1400),
            3: self._make_table(3, 10, 1300),
        }
        result = get_tier_adaptation(old_tables, new_tiers=4, new_beys_per_tier=8)
        assignments = result["new_tier_assignments"]

        for i in range(1, BEYS_PER_TIER + 1):
            assert assignments[f"T1-Bey{i}"]["new_tier"] == 1

    def test_adaptation_tier1_bottom_falls_to_tier2(self):
        """Old Tier 1 positions 9 and 10 should drop to new Tier 2."""
        old_tables = {
            1: self._make_table(1, 10, 1500),
            2: self._make_table(2, 10, 1400),
            3: self._make_table(3, 10, 1300),
        }
        result = get_tier_adaptation(old_tables, new_tiers=4, new_beys_per_tier=8)
        assignments = result["new_tier_assignments"]

        # Old T1-Bey9 and T1-Bey10 become global ranks 9 and 10 → new Tier 2
        assert assignments["T1-Bey9"]["new_tier"] == 2
        assert assignments["T1-Bey10"]["new_tier"] == 2

    def test_adaptation_old_tier2_top_promotes(self):
        """Old Tier 2 positions 1 and 2 should rise to new Tier 2 (from old Tier 2)."""
        old_tables = {
            1: self._make_table(1, 10, 1500),
            2: self._make_table(2, 10, 1400),
            3: self._make_table(3, 10, 1300),
        }
        result = get_tier_adaptation(old_tables, new_tiers=4, new_beys_per_tier=8)
        assignments = result["new_tier_assignments"]

        # T2-Bey1 (global rank 11) → new Tier 2
        # T2-Bey2 (global rank 12) → new Tier 2
        assert assignments["T2-Bey1"]["new_tier"] == 2
        assert assignments["T2-Bey2"]["new_tier"] == 2

    def test_adaptation_records_tier_changes(self):
        """Beys that move tier should appear in tier_changes."""
        old_tables = {
            1: self._make_table(1, 10, 1500),
            2: self._make_table(2, 10, 1400),
            3: self._make_table(3, 10, 1300),
        }
        result = get_tier_adaptation(old_tables, new_tiers=4, new_beys_per_tier=8)

        # Old Tier 3 beys gain a new Tier 4 (they move from tier 3 to tier 4)
        # but also some may be promoted. At minimum tier changes exist.
        assert isinstance(result["tier_changes"], list)
        changed_beys = {c["bey"] for c in result["tier_changes"]}
        # T1-Bey9 drops from old Tier 1 to new Tier 2
        assert "T1-Bey9" in changed_beys

    def test_adaptation_with_surplus_beys_to_qualification(self):
        """Beys beyond new_tiers * new_beys_per_tier go to qualification pool."""
        # 3 old tiers of 12 beys each = 36 beys; new structure takes 4*8=32
        old_tables = {
            1: self._make_table(1, 12, 1500),
            2: self._make_table(2, 12, 1400),
            3: self._make_table(3, 12, 1300),
        }
        result = get_tier_adaptation(old_tables, new_tiers=4, new_beys_per_tier=8)
        assert result["total_beys_assigned"] == 32
        assert len(result["qualification_pool"]) == 4  # 36 - 32

    def test_adaptation_stable_when_structure_unchanged(self):
        """When structure does not change, most beys should stay in same tier."""
        old_tables = {
            1: self._make_table(1, 8, 1500),
            2: self._make_table(2, 8, 1400),
            3: self._make_table(3, 8, 1300),
            4: self._make_table(4, 8, 1200),
        }
        result = get_tier_adaptation(old_tables, new_tiers=4, new_beys_per_tier=8)
        assert result["total_beys_assigned"] == 32
        # No tier changes expected when structure is the same
        assert len(result["tier_changes"]) == 0
