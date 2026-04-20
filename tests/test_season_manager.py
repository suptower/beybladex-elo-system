"""
Unit tests for season_manager.py module.
Tests season initialization, points calculation, league tables, and promotion/relegation logic.
"""
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'season'))

from season_manager import (
    calculate_season_points,
    initialize_season,
    initialize_season_from_results,
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

    def test_ppr_ppw_without_rounds_data(self):
        """PPR and PPW should be calculated from season_points and matches/wins."""
        matches = [
            {
                "match_type": "season",
                "season_id": "S1",
                "tier": 1,
                "match_id": "M001",
                "bey_a": "Winner",
                "bey_b": "Loser",
                "score_a": 4,
                "score_b": 2,
                "elo_a": 1500,
                "elo_b": 1400,
            }
        ]
        table = get_league_table(matches, 1, "S1")
        winner = table[0]  # Winner has 3 SP, 1 win, 1 match
        assert winner["ppr"] == round(POINTS_WIN / 1, 2)  # 3.0
        assert winner["ppw"] == round(POINTS_WIN / 1, 2)  # 3.0

        loser = table[1]  # Loser has 0 SP, 0 wins, 1 match
        assert loser["ppr"] == 0.0
        # Backend stores 0.0 when wins == 0; the UI displays "—" in this case.
        assert loser["ppw"] == 0.0

    def test_irw_irl_with_rounds_data(self):
        """IRW and IRL should be computed from rounds data when provided."""
        matches = [
            {
                "match_type": "season",
                "season_id": "S1",
                "tier": 1,
                "match_id": "M001",
                "bey_a": "Alpha",
                "bey_b": "Beta",
                "score_a": 4,
                "score_b": 2,
                "elo_a": 1500,
                "elo_b": 1400,
            }
        ]
        # Alpha wins 3 rounds, Beta wins 2 rounds
        rounds_data = {
            "M001": [
                {"round_number": 1, "winner": "Alpha", "finish_type": "spin", "points_awarded": 1},
                {"round_number": 2, "winner": "Beta",  "finish_type": "spin", "points_awarded": 1},
                {"round_number": 3, "winner": "Alpha", "finish_type": "burst", "points_awarded": 2},
                {"round_number": 4, "winner": "Alpha", "finish_type": "spin", "points_awarded": 1},
                {"round_number": 5, "winner": "Beta",  "finish_type": "spin", "points_awarded": 1},
            ]
        }
        table = get_league_table(matches, 1, "S1", rounds_data=rounds_data)
        alpha = next(e for e in table if e["bey"] == "Alpha")
        beta = next(e for e in table if e["bey"] == "Beta")

        assert alpha["irw"] == 3
        assert alpha["irl"] == 2
        assert beta["irw"] == 2
        assert beta["irl"] == 3

    def test_irw_irl_zero_without_rounds_data(self):
        """IRW and IRL should both be 0 when no rounds_data is provided."""
        matches = [
            {
                "match_type": "season",
                "season_id": "S1",
                "tier": 1,
                "match_id": "M001",
                "bey_a": "Alpha",
                "bey_b": "Beta",
                "score_a": 4,
                "score_b": 2,
                "elo_a": 1500,
                "elo_b": 1400,
            }
        ]
        table = get_league_table(matches, 1, "S1")
        for entry in table:
            assert entry["irw"] == 0
            assert entry["irl"] == 0

    def test_ppr_multiple_matches(self):
        """PPR should average season points across all matches played."""
        matches = [
            {
                "match_type": "season",
                "season_id": "S1",
                "tier": 1,
                "match_id": "M001",
                "bey_a": "Alpha",
                "bey_b": "Beta",
                "score_a": 4,
                "score_b": 0,  # Dominant win for Alpha
                "elo_a": 1500,
                "elo_b": 1400,
            },
            {
                "match_type": "season",
                "season_id": "S1",
                "tier": 1,
                "match_id": "M002",
                "bey_a": "Alpha",
                "bey_b": "Gamma",
                "score_a": 0,
                "score_b": 4,  # Alpha loses
                "elo_a": 1500,
                "elo_b": 1450,
            },
        ]
        table = get_league_table(matches, 1, "S1")
        alpha = next(e for e in table if e["bey"] == "Alpha")
        # Alpha: 4 SP + 0 SP = 4 SP across 2 matches → PPR = 2.0
        assert alpha["ppr"] == 2.0
        # Alpha won 1 match → PPW = 4 SP / 1 win = 4.0
        assert alpha["ppw"] == 4.0


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


class TestInitializeSeasonFromResults:
    """Tests for initialize_season_from_results()."""

    # ---------------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------------

    @staticmethod
    def _make_tier_assignments(tiers_beys: dict) -> dict:
        """Build a tier_assignments dict from {tier: [bey, ...]}."""
        ta = {}
        for tier, beys in tiers_beys.items():
            for bey in beys:
                ta[bey] = {"tier": tier, "start_elo": 1000.0}
        return ta

    @staticmethod
    def _make_elo_lookup(tier_assignments: dict) -> dict:
        """Build an elo_lookup from tier_assignments (uniform ELO for simplicity)."""
        return {bey: data["start_elo"] for bey, data in tier_assignments.items()}

    # ---------------------------------------------------------------------------
    # Basic promotion / relegation
    # ---------------------------------------------------------------------------

    def test_auto_promotion_moves_bey_up(self):
        """A bey in automatic_promotion should move from its current tier to tier-1."""
        ta = self._make_tier_assignments({
            1: ["T1A", "T1B"],
            2: ["T2A", "T2B"],
        })
        promo_relg = {
            "automatic_promotion": [
                {"bey": "T2A", "from_tier": 2, "to_tier": 1}
            ],
            "automatic_relegation": [],
            "relegation_matches": [],
            "qualification_candidates": [],
        }
        elo_lookup = self._make_elo_lookup(ta)
        season_data, warnings = initialize_season_from_results(
            "S2", ta, [], promo_relg, elo_lookup
        )
        assignments = season_data["tier_assignments"]
        assert assignments["T2A"]["tier"] == 1, "T2A should be promoted to tier 1"

    def test_auto_relegation_moves_bey_down(self):
        """A bey in automatic_relegation should move from its current tier to tier+1."""
        ta = self._make_tier_assignments({
            1: ["T1A", "T1B"],
            2: ["T2A", "T2B"],
        })
        promo_relg = {
            "automatic_promotion": [],
            "automatic_relegation": [
                {"bey": "T1B", "from_tier": 1, "to_tier": 2}
            ],
            "relegation_matches": [],
            "qualification_candidates": [],
        }
        elo_lookup = self._make_elo_lookup(ta)
        season_data, warnings = initialize_season_from_results(
            "S2", ta, [], promo_relg, elo_lookup
        )
        assignments = season_data["tier_assignments"]
        assert assignments["T1B"]["tier"] == 2, "T1B should be relegated to tier 2"

    def test_remaining_beys_keep_tier(self):
        """Beys not involved in any movement should stay in their original tier."""
        ta = self._make_tier_assignments({
            1: ["T1A", "T1B"],
            2: ["T2A", "T2B"],
        })
        promo_relg = {
            "automatic_promotion": [{"bey": "T2A", "from_tier": 2, "to_tier": 1}],
            "automatic_relegation": [{"bey": "T1B", "from_tier": 1, "to_tier": 2}],
            "relegation_matches": [],
            "qualification_candidates": [],
        }
        elo_lookup = self._make_elo_lookup(ta)
        season_data, warnings = initialize_season_from_results(
            "S2", ta, [], promo_relg, elo_lookup
        )
        assignments = season_data["tier_assignments"]
        assert assignments["T1A"]["tier"] == 1
        assert assignments["T2B"]["tier"] == 2

    # ---------------------------------------------------------------------------
    # Qualification candidates and pool filling
    # ---------------------------------------------------------------------------

    def test_qualification_candidates_removed_and_replaced(self):
        """Qualification candidates should leave their tier and be replaced from the pool."""
        # Use full 8-bey tiers (S2 format) so only the expected tier has a vacancy.
        t1 = [f"T1_{i}" for i in range(8)]
        t2 = [f"T2_{i}" for i in range(8)]
        t3 = [f"T3_{i}" for i in range(8)]
        t4 = [f"T4_{i}" for i in range(7)] + ["QualOut"]
        ta = self._make_tier_assignments({1: t1, 2: t2, 3: t3, 4: t4})
        promo_relg = {
            "automatic_promotion": [],
            "automatic_relegation": [],
            "relegation_matches": [],
            "qualification_candidates": [
                {"bey": "QualOut", "tier": 4, "position": 8}
            ],
        }
        prev_qual_pool = [{"bey": "PoolBey", "elo": 950.0}]
        elo_lookup = {**self._make_elo_lookup(ta), "PoolBey": 950.0}
        season_data, warnings = initialize_season_from_results(
            "S2", ta, prev_qual_pool, promo_relg, elo_lookup
        )
        assignments = season_data["tier_assignments"]
        # QualOut should no longer be in any tier
        assert "QualOut" not in assignments
        # PoolBey should have been placed in tier 4 to fill the vacancy
        assert "PoolBey" in assignments
        assert assignments["PoolBey"]["tier"] == 4

    def test_qual_candidates_drop_to_qual_pool_if_no_fill_available(self):
        """If no fill-in bey is available, the tier stays short and a warning is issued."""
        # Full tiers except for a single qual candidate with no pool bey to replace it.
        t1 = [f"T1_{i}" for i in range(8)]
        t2 = [f"T2_{i}" for i in range(8)]
        t3 = [f"T3_{i}" for i in range(8)]
        t4 = [f"T4_{i}" for i in range(7)] + ["QualOut"]
        ta = self._make_tier_assignments({1: t1, 2: t2, 3: t3, 4: t4})
        promo_relg = {
            "automatic_promotion": [],
            "automatic_relegation": [],
            "relegation_matches": [],
            "qualification_candidates": [
                {"bey": "QualOut", "tier": 4, "position": 8}
            ],
        }
        elo_lookup = self._make_elo_lookup(ta)
        season_data, warnings = initialize_season_from_results(
            "S2", ta, [], promo_relg, elo_lookup
        )
        assignments = season_data["tier_assignments"]
        assert "QualOut" not in assignments
        # A warning about the shortage should exist
        shortage_warnings = [w for w in warnings if "short" in w.lower()]
        assert len(shortage_warnings) > 0

    # ---------------------------------------------------------------------------
    # Relegation playoff warning
    # ---------------------------------------------------------------------------

    def test_relegation_playoff_beys_stay_and_warning_issued(self):
        """Playoff beys should stay in their current tier and produce a warning."""
        ta = self._make_tier_assignments({
            1: ["T1A", "PlayoffHigh"],
            2: ["T2A", "PlayoffLow"],
        })
        promo_relg = {
            "automatic_promotion": [],
            "automatic_relegation": [],
            "relegation_matches": [
                {
                    "higher_bey": "PlayoffHigh",
                    "higher_tier": 1,
                    "higher_position": 7,
                    "lower_bey": "PlayoffLow",
                    "lower_tier": 2,
                    "lower_position": 2,
                }
            ],
            "qualification_candidates": [],
        }
        elo_lookup = self._make_elo_lookup(ta)
        season_data, warnings = initialize_season_from_results(
            "S2", ta, [], promo_relg, elo_lookup
        )
        assignments = season_data["tier_assignments"]
        assert assignments["PlayoffHigh"]["tier"] == 1
        assert assignments["PlayoffLow"]["tier"] == 2
        playoff_warnings = [w for w in warnings if "playoff" in w.lower()]
        assert len(playoff_warnings) > 0

    # ---------------------------------------------------------------------------
    # Output structure
    # ---------------------------------------------------------------------------

    def test_output_structure(self):
        """The returned season_data should have the required keys."""
        ta = self._make_tier_assignments({1: ["BeyA"], 2: ["BeyB"]})
        promo_relg = {
            "automatic_promotion": [],
            "automatic_relegation": [],
            "relegation_matches": [],
            "qualification_candidates": [],
        }
        elo_lookup = self._make_elo_lookup(ta)
        season_data, _ = initialize_season_from_results(
            "S3", ta, [], promo_relg, elo_lookup
        )
        required_keys = {
            "season_id", "start_date", "status", "tier_assignments",
            "qualification_pool", "league_champion", "cup_winner", "tiers"
        }
        assert required_keys.issubset(set(season_data.keys()))
        assert season_data["season_id"] == "S3"
        assert season_data["status"] == "active"

    def test_tiers_block_matches_tier_assignments(self):
        """tiers.<N>.beys must list exactly the beys assigned to that tier."""
        ta = self._make_tier_assignments({1: ["T1A", "T1B"], 2: ["T2A", "T2B"]})
        promo_relg = {
            "automatic_promotion": [{"bey": "T2A", "from_tier": 2, "to_tier": 1}],
            "automatic_relegation": [{"bey": "T1B", "from_tier": 1, "to_tier": 2}],
            "relegation_matches": [],
            "qualification_candidates": [],
        }
        elo_lookup = self._make_elo_lookup(ta)
        season_data, _ = initialize_season_from_results(
            "S2", ta, [], promo_relg, elo_lookup
        )
        assignments = season_data["tier_assignments"]
        tiers_block = season_data["tiers"]
        for tier_str, info in tiers_block.items():
            tier_num = int(tier_str)
            beys_in_tier = {bey for bey, d in assignments.items() if d["tier"] == tier_num}
            assert set(info["beys"]) == beys_in_tier, (
                f"tiers.{tier_str}.beys does not match tier_assignments for tier {tier_num}"
            )

    def test_start_elo_set_from_lookup(self):
        """start_elo should be pulled from elo_lookup for each bey."""
        ta = self._make_tier_assignments({1: ["Alpha"], 2: ["Beta"]})
        promo_relg = {
            "automatic_promotion": [],
            "automatic_relegation": [],
            "relegation_matches": [],
            "qualification_candidates": [],
        }
        elo_lookup = {"Alpha": 1234.5, "Beta": 987.0}
        season_data, _ = initialize_season_from_results(
            "S2", ta, [], promo_relg, elo_lookup
        )
        assert season_data["tier_assignments"]["Alpha"]["start_elo"] == 1234.5
        assert season_data["tier_assignments"]["Beta"]["start_elo"] == 987.0

    def test_returns_are_tuple(self):
        """Function must return a (dict, list) tuple."""
        ta = self._make_tier_assignments({1: ["A"]})
        promo_relg = {
            "automatic_promotion": [],
            "automatic_relegation": [],
            "relegation_matches": [],
            "qualification_candidates": [],
        }
        result = initialize_season_from_results("S2", ta, [], promo_relg, {})
        assert isinstance(result, tuple) and len(result) == 2
        assert isinstance(result[0], dict)
        assert isinstance(result[1], list)
