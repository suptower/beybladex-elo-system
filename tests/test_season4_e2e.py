"""
End-to-End Simulation Tests for Season 4 League Overhaul.

Verifies all 21 acceptance criteria specified in docs/guides/SEASON4_NEW_STRUCTURE.md:
- 3 regular tiers of exactly 8 Beys each (24 active).
- Phase 1 (28 RR) + Phase 2 (12 Swiss) = 40 matches per tier (120 total).
- 10 matches played per Bey; combined points standings.
- Challenge League: 24 Beys drawn from Qualification Pool into 4 groups of 6.
- Group Stage: 3 Swiss rounds per group (36 matches total), top 2 advance.
- Final Swiss Stage: 8 qualifiers reset to 0 points, 3 Swiss rounds (12 matches total).
- Total season match volume: 120 + 48 = 168 matches.
- Promotions / Relegations:
  - T1: #8 auto-relegates, #7 playoff vs T2 #2.
  - T2: #1 auto-promotes, #2 playoff vs T1 #7, #6 playoff vs T3 #3, #7-8 auto-relegate.
  - T3: #1-2 auto-promote, #3 playoff vs T2 #6, #4-8 to Qualification Pool.
  - Challenge League: Top 5 qualify for Tier III, ranks 6-8 return to pool.
- Next season tier composition: Tier III has exactly 8 Beys (2 auto-relegated from T2,
  1 playoff loser, 5 from Challenge League).
"""

import pytest
from typing import Dict, List, Tuple

from src.season.season_manager import (
    initialize_season,
    initialize_season_from_results,
    get_league_table,
    get_promotion_relegation,
    generate_season_archive,
    get_season_format,
    schedule_round_robin,
)
from src.season.challenge_league import (
    select_challenge_league_beys,
    assign_challenge_groups,
    calculate_league_table as calculate_cl_table,
    process_challenge_league,
)


@pytest.fixture
def pool_of_58_beys() -> List[Tuple[str, float]]:
    """Generate a realistic leaderboard of 58 Beys with descending ELOs."""
    beys = []
    # Tier I candidates
    t1_names = [
        "ImpactDrake", "DranSword", "FoxBrush", "SilverWolf",
        "TuskMammoth", "SharkScale", "ValkyrieVolt", "WeissTiger"
    ]
    # Tier II candidates
    t2_names = [
        "HellsChain", "DranBrave", "ViperTail", "CobaltDragoon",
        "ScorpioSpear", "CerberusFlame", "WizardArc", "PhoenixWing"
    ]
    # Tier III candidates
    t3_names = [
        "LeonCrest", "TriceraPress", "HellsReaper", "RhinoReaper",
        "GolemRock", "DranDagger", "HellsHammer", "WyvernHover"
    ]
    # Pool candidates (34 beys)
    pool_names = [
        "HellsBrave", "ShelterDrake", "TyrannoRoar", "MeteorDragoon",
        "PhoenixFlare", "SamuraiSteel", "LeonClaw", "DranStrike",
        "BulletGriffon", "BrachioWhip", "BahamutBlitz", "MummyCurse",
        "KnightMail", "WolfHunt", "DranBuster", "GhostCircle",
        "PhoenixRudder", "ClockMirage", "CrimsonGaruda", "UnicornSting",
        "PerseusDark", "CobaltDrake", "SamuraiCalibur", "BlackShell",
        "SolEclipse", "WhaleWave", "SharkEdge", "EmperorMight",
        "WhaleFlame", "PegasusBlast", "WizardRod", "TyrannoBeat",
        "SamuraiSaber", "WizardArrow"
    ]

    all_names = t1_names + t2_names + t3_names + pool_names
    assert len(all_names) == 58

    for idx, name in enumerate(all_names):
        elo = 1200.0 - (idx * 6.0)
        beys.append((name, elo))

    return beys


def simulate_swiss_round(pairings: List[Tuple[str, str]], start_match_id: int, match_type: str, season_id: str = "S4", tier: int = 1, matchday: int = 8) -> Tuple[List[Dict], int]:
    """Simulate a Swiss round given explicit pairings."""
    matches = []
    mid = start_match_id
    for a, b in pairings:
        mid += 1
        # Deterministic scoring: team A wins 4-1
        matches.append({
            "match_id": f"M{mid:04d}",
            "date": "2026-11-01",
            "bey_a": a,
            "bey_b": b,
            "score_a": 4,
            "score_b": 1,
            "match_type": match_type,
            "season_id": season_id,
            "tier": tier,
            "matchday": matchday,
        })
    return matches, mid


class TestSeason4EndToEndSimulation:
    """Comprehensive E2E test verifying all 21 acceptance criteria."""

    def test_full_season_4_lifecycle(self, pool_of_58_beys):
        # -------------------------------------------------------------
        # 1. INITIALIZATION: 24 active in 3 tiers of 8, 34 in pool
        # -------------------------------------------------------------
        season_data = initialize_season("S4", pool_of_58_beys)

        assert len(season_data["tier_assignments"]) == 24
        assert len(season_data["qualification_pool"]) == 34
        assert set(season_data["tiers"].keys()) == {"1", "2", "3"}

        for t in range(1, 4):
            t_beys = [b for b, d in season_data["tier_assignments"].items() if d["tier"] == t]
            assert len(t_beys) == 8, f"Tier {t} must contain exactly 8 Beys (Criterion 1)"
            assert season_data["tiers"][str(t)]["matches_total"] == 40

        # -------------------------------------------------------------
        # 2. CHALLENGE LEAGUE DRAW: 24 distinct from pool, 4 groups of 6
        # -------------------------------------------------------------
        selected_beys = select_challenge_league_beys(
            qualification_pool=season_data["qualification_pool"],
            count=24,
            seed=42,
        )
        assert len(selected_beys) == 24, "Must select exactly 24 Beys (Criterion 14)"
        selected_names = [b["bey"] for b in selected_beys]
        assert len(set(selected_names)) == 24, "Selected Beys must be distinct without replacement"

        groups = assign_challenge_groups(selected_beys, method="snake_elo", seed=42)
        assert len(groups) == 4, "Must have 4 groups (Criterion 15)"
        for g_id in ["A", "B", "C", "D"]:
            assert len(groups[g_id]) == 6, f"Group {g_id} must have 6 Beys"

        # -------------------------------------------------------------
        # 3. REGULAR TIERS SIMULATION: 40 matches/tier (28 RR + 12 Swiss)
        # -------------------------------------------------------------
        all_regular_matches = []
        match_counter = 100

        tier_tables = {}
        for tier in range(1, 4):
            t_beys = [b for b, d in season_data["tier_assignments"].items() if d["tier"] == tier]
            tier_matches = []

            # Phase 1: Round Robin (28 matches, 7 per Bey)
            rr_pairings = schedule_round_robin(t_beys)
            assert len(rr_pairings) == 28, f"Tier {tier} must play 28 RR matches (Criterion 2)"

            for i, (a, b) in enumerate(rr_pairings, 1):
                match_counter += 1
                # Seeded score so standings have clear ordering without ties:
                # Top beys win more points
                score_a = 4 if t_beys.index(a) < t_beys.index(b) else 1
                score_b = 1 if score_a == 4 else 4
                tier_matches.append({
                    "match_id": f"M{match_counter:04d}",
                    "date": "2026-11-01",
                    "bey_a": a,
                    "bey_b": b,
                    "score_a": score_a,
                    "score_b": score_b,
                    "match_type": "season",
                    "season_id": "S4",
                    "tier": tier,
                    "matchday": (i % 7) + 1,
                })

            # Check Phase 1 standings to seed Phase 2 Swiss Round 1
            p1_table = get_league_table(tier_matches, tier=tier, season_id="S4")
            assert len(p1_table) == 8

            # Phase 2 Swiss Round 1: 1v2, 3v4, 5v6, 7v8 (4 matches)
            r1_pairings = [
                (p1_table[0]["bey"], p1_table[1]["bey"]),
                (p1_table[2]["bey"], p1_table[3]["bey"]),
                (p1_table[4]["bey"], p1_table[5]["bey"]),
                (p1_table[6]["bey"], p1_table[7]["bey"]),
            ]
            r1_matches, match_counter = simulate_swiss_round(r1_pairings, match_counter, "season", "S4", tier, matchday=8)
            tier_matches.extend(r1_matches)

            # Phase 2 Swiss Round 2: 4 matches (matchday 9)
            r2_pairings = [
                (p1_table[0]["bey"], p1_table[2]["bey"]),
                (p1_table[1]["bey"], p1_table[3]["bey"]),
                (p1_table[4]["bey"], p1_table[6]["bey"]),
                (p1_table[5]["bey"], p1_table[7]["bey"]),
            ]
            r2_matches, match_counter = simulate_swiss_round(r2_pairings, match_counter, "season", "S4", tier, matchday=9)
            tier_matches.extend(r2_matches)

            # Phase 2 Swiss Round 3: 4 matches (matchday 10)
            r3_pairings = [
                (p1_table[0]["bey"], p1_table[3]["bey"]),
                (p1_table[1]["bey"], p1_table[2]["bey"]),
                (p1_table[4]["bey"], p1_table[7]["bey"]),
                (p1_table[5]["bey"], p1_table[6]["bey"]),
            ]
            r3_matches, match_counter = simulate_swiss_round(r3_pairings, match_counter, "season", "S4", tier, matchday=10)
            tier_matches.extend(r3_matches)

            assert len(tier_matches) == 40, f"Tier {tier} must have exactly 40 matches (Criterion 2)"
            all_regular_matches.extend(tier_matches)

            # Final combined standings across Phase 1 + Phase 2 (Criterion 4)
            final_table = get_league_table(tier_matches, tier=tier, season_id="S4")
            assert len(final_table) == 8
            for entry in final_table:
                assert entry["matches"] == 10, f"{entry['bey']} in Tier {tier} must have played 10 matches (Criterion 3)"
            tier_tables[tier] = final_table

        assert len(all_regular_matches) == 120, "Regular tiers total must be 120 matches (Criterion 20)"

        # -------------------------------------------------------------
        # 4. CHALLENGE LEAGUE SIMULATION: 48 matches (36 group + 12 final)
        # -------------------------------------------------------------
        all_cl_matches = []
        group_qualifiers = []

        for g_id, g_beys in groups.items():
            b_names = [b["bey"] for b in g_beys]
            g_matches = []

            # 3 Swiss rounds per group of 6 = 3 matches/round * 3 = 9 matches
            # Round 1 (1v2, 3v4, 5v6)
            r1_pairings = [(b_names[0], b_names[1]), (b_names[2], b_names[3]), (b_names[4], b_names[5])]
            r1_m, match_counter = simulate_swiss_round(r1_pairings, match_counter, "challenge_group")
            g_matches.extend(r1_m)

            # Round 2
            r2_pairings = [(b_names[0], b_names[2]), (b_names[1], b_names[4]), (b_names[3], b_names[5])]
            r2_m, match_counter = simulate_swiss_round(r2_pairings, match_counter, "challenge_group")
            g_matches.extend(r2_m)

            # Round 3
            r3_pairings = [(b_names[0], b_names[4]), (b_names[1], b_names[3]), (b_names[2], b_names[5])]
            r3_m, match_counter = simulate_swiss_round(r3_pairings, match_counter, "challenge_group")
            g_matches.extend(r3_m)

            assert len(g_matches) == 9, f"Group {g_id} must have 9 matches (Criterion 16)"
            all_cl_matches.extend(g_matches)

            # Group standings
            g_table = calculate_cl_table(g_matches, expected_beys=b_names)
            assert len(g_table) == 6
            for entry in g_table:
                assert entry["matches"] == 3, f"Group participant must play 3 matches"

            # Top 2 advance (Criterion 16)
            group_qualifiers.append(g_table[0]["bey"])
            group_qualifiers.append(g_table[1]["bey"])

        assert len(all_cl_matches) == 36, "CL Phase 1 must have 36 matches total"
        assert len(group_qualifiers) == 8, "Exactly 8 qualifiers must advance to Final Stage (Criterion 16)"

        # Phase 2: Final Swiss Stage (8 Beys, reset to 0 points)
        final_matches = []
        # 3 Swiss rounds of 4 matches each = 12 matches (Criterion 17)
        r1_final_pairings = [
            (group_qualifiers[0], group_qualifiers[1]),
            (group_qualifiers[2], group_qualifiers[3]),
            (group_qualifiers[4], group_qualifiers[5]),
            (group_qualifiers[6], group_qualifiers[7]),
        ]
        r1_fm, match_counter = simulate_swiss_round(r1_final_pairings, match_counter, "challenge_final")
        final_matches.extend(r1_fm)

        r2_final_pairings = [
            (group_qualifiers[0], group_qualifiers[2]),
            (group_qualifiers[1], group_qualifiers[4]),
            (group_qualifiers[3], group_qualifiers[6]),
            (group_qualifiers[5], group_qualifiers[7]),
        ]
        r2_fm, match_counter = simulate_swiss_round(r2_final_pairings, match_counter, "challenge_final")
        final_matches.extend(r2_fm)

        r3_final_pairings = [
            (group_qualifiers[0], group_qualifiers[4]),
            (group_qualifiers[1], group_qualifiers[3]),
            (group_qualifiers[2], group_qualifiers[7]),
            (group_qualifiers[5], group_qualifiers[6]),
        ]
        r3_fm, match_counter = simulate_swiss_round(r3_final_pairings, match_counter, "challenge_final")
        final_matches.extend(r3_fm)

        assert len(final_matches) == 12, "Final Swiss stage must have 12 matches (Criterion 17)"
        all_cl_matches.extend(final_matches)

        assert len(all_cl_matches) == 48, "Challenge League must have 48 matches total (Criterion 20)"
        total_season_matches = len(all_regular_matches) + len(all_cl_matches)
        assert total_season_matches == 168, "Total Season 4 matches must be exactly 168 (Criterion 20)"

        # Final Swiss stage standings
        final_table = calculate_cl_table(final_matches, expected_beys=group_qualifiers)
        assert len(final_table) == 8
        for entry in final_table:
            assert entry["matches"] == 3

        # Process challenge league helper
        cl_processed = process_challenge_league(matches=all_cl_matches, season_id="S4", groups=groups)
        top5_promoted = cl_processed["promoted_to_tier3"]
        ranks6_8_returned = cl_processed["final_eliminated"]
        all_returned_to_pool = cl_processed["returned_to_pool"]

        assert len(top5_promoted) == 5, "Top 5 must promote to Tier III (Criterion 18)"
        assert len(ranks6_8_returned) == 3, "Ranks 6-8 must return to pool (Criterion 19)"
        assert len(all_returned_to_pool) == 19, "All 19 non-qualifying CL Beys return to pool"

        # -------------------------------------------------------------
        # 5. PROMOTION AND RELEGATION RULES VERIFICATION
        # -------------------------------------------------------------
        prom_rel = get_promotion_relegation(
            season_data=season_data,
            league_tables=tier_tables,
            challenge_league_data=cl_processed,
        )

        # Tier I verification (Criteria 5, 6, 7)
        # Tier I rank 8 directly relegated to Tier II
        t1_relegated = [p["bey"] for p in prom_rel["automatic_relegation"] if p["from_tier"] == 1]
        assert t1_relegated == [tier_tables[1][7]["bey"]], "Tier I rank 8 directly relegated (Criterion 5)"

        # Tier II rank 1 directly promoted to Tier I
        t2_promoted_to_t1 = [p["bey"] for p in prom_rel["automatic_promotion"] if p["from_tier"] == 2]
        assert t2_promoted_to_t1 == [tier_tables[2][0]["bey"]], "Tier II rank 1 directly promoted (Criterion 6)"

        # Playoff match: T1 #7 vs T2 #2 (Criterion 7)
        t1_t2_playoff = [m for m in prom_rel["relegation_matches"] if m["higher_tier"] == 1]
        assert len(t1_t2_playoff) == 1
        assert t1_t2_playoff[0]["higher_bey"] == tier_tables[1][6]["bey"]
        assert t1_t2_playoff[0]["lower_bey"] == tier_tables[2][1]["bey"]

        # Tier II verification (Criteria 9, 10, 11)
        # Tier II ranks 7-8 directly relegated to Tier III
        t2_relegated = [p["bey"] for p in prom_rel["automatic_relegation"] if p["from_tier"] == 2]
        assert t2_relegated == [tier_tables[2][7]["bey"], tier_tables[2][6]["bey"]], "Tier II ranks 7-8 relegated (Criterion 9)"

        # Tier III ranks 1-2 directly promoted to Tier II
        t3_promoted = [p["bey"] for p in prom_rel["automatic_promotion"] if p["from_tier"] == 3]
        assert t3_promoted == [tier_tables[3][0]["bey"], tier_tables[3][1]["bey"]], "Tier III ranks 1-2 promoted (Criterion 10)"

        # Playoff match: T2 #6 vs T3 #3 (Criterion 11)
        t2_t3_playoff = [m for m in prom_rel["relegation_matches"] if m["higher_tier"] == 2]
        assert len(t2_t3_playoff) == 1
        assert t2_t3_playoff[0]["higher_bey"] == tier_tables[2][5]["bey"]
        assert t2_t3_playoff[0]["lower_bey"] == tier_tables[3][2]["bey"]

        # Tier III positions 4-8 enter Qualification Pool (Criterion 13)
        t3_to_pool = [q["bey"] for q in prom_rel["qualification_candidates"] if q["tier"] == 3]
        expected_t3_pool = [tier_tables[3][i]["bey"] for i in range(3, 8)]
        assert t3_to_pool == expected_t3_pool, "Tier III ranks 4-8 enter pool (Criterion 13)"

        # Challenge League Top 5 promoted to Tier III
        cl_promoted = [p["bey"] for p in prom_rel["automatic_promotion"] if p["from_tier"] == "CL"]
        assert cl_promoted == top5_promoted, "Challenge League top 5 promoted to Tier III (Criterion 18)"

        # -------------------------------------------------------------
        # 6. ARCHIVE GENERATION
        # -------------------------------------------------------------
        archive = generate_season_archive(
            season_id="S4",
            matches=all_regular_matches + all_cl_matches,
            season_data=season_data,
            league_tables=tier_tables,
            promotion_relegation=prom_rel,
            challenge_league=cl_processed,
        )
        assert archive["challenge_league"] == cl_processed
        assert archive["promotion_relegation"] == prom_rel

        # -------------------------------------------------------------
        # 7. NEXT SEASON TRANSITION (S5): Exactly 8 Beys per tier
        # -------------------------------------------------------------
        elo_lookup = dict(pool_of_58_beys)

        # Resolve relegation playoffs for clean transition:
        # T1 #7 defeats T2 #2 -> T1 #7 stays in T1, T2 #2 stays in T2
        # T2 #6 defeats T3 #3 -> T2 #6 stays in T2, T3 #3 relegated to T3
        # Remove relegation_matches from prom_rel now that they are resolved
        resolved_prom_rel = dict(prom_rel)
        resolved_prom_rel["relegation_matches"] = []

        s5_data, warnings = initialize_season_from_results(
            new_season_id="S5",
            prev_tier_assignments=season_data["tier_assignments"],
            prev_qualification_pool=season_data["qualification_pool"],
            promotion_relegation=resolved_prom_rel,
            elo_lookup=elo_lookup,
        )

        s5_t1 = [b for b, d in s5_data["tier_assignments"].items() if d["tier"] == 1]
        s5_t2 = [b for b, d in s5_data["tier_assignments"].items() if d["tier"] == 2]
        s5_t3 = [b for b, d in s5_data["tier_assignments"].items() if d["tier"] == 3]

        # Enforce exact counts and uniqueness (Criterion 21)
        assert len(s5_t1) == 8, f"S5 Tier 1 must have 8 Beys, got {len(s5_t1)}"
        assert len(s5_t2) == 8, f"S5 Tier 2 must have 8 Beys, got {len(s5_t2)}"
        assert len(s5_t3) == 8, f"S5 Tier 3 must have 8 Beys, got {len(s5_t3)}"

        all_s5_beys = s5_t1 + s5_t2 + s5_t3
        assert len(all_s5_beys) == 24
        assert len(set(all_s5_beys)) == 24, "No duplicate Beys in league (Criterion 21)"

        # Check S5 Tier III composition:
        # - 2 auto-relegated from T2
        # - 1 from playoff (T3 #3 remained in T3)
        # - 5 from Challenge League
        # Total = 8 Beys!
        for b in t2_relegated:
            assert b in s5_t3, f"Auto-relegated {b} must be in Tier III"
        for b in top5_promoted:
            assert b in s5_t3, f"CL-promoted {b} must be in Tier III"

    def test_relegation_playoff_upsets_scenario(self, pool_of_58_beys):
        """
        Verify tier transitions when lower-tier Beys WIN their relegation playoff matches:
        - T2 #2 defeats T1 #7 -> T2 #2 promoted to T1, T1 #7 relegated to T2
        - T3 #3 defeats T2 #6 -> T3 #3 promoted to T2, T2 #6 relegated to T3
        Tier III must still contain exactly 8 Beys (2 auto-relegated + 1 playoff loser from T2 + 5 from Challenge League).
        """
        season_data = initialize_season("S4", pool_of_58_beys)
        elo_lookup = dict(pool_of_58_beys)

        t1_beys = [b for b, d in season_data["tier_assignments"].items() if d["tier"] == 1]
        t2_beys = [b for b, d in season_data["tier_assignments"].items() if d["tier"] == 2]
        t3_beys = [b for b, d in season_data["tier_assignments"].items() if d["tier"] == 3]

        t1_rank7 = t1_beys[6]
        t1_rank8 = t1_beys[7]

        t2_rank1 = t2_beys[0]
        t2_rank2 = t2_beys[1]
        t2_rank6 = t2_beys[5]
        t2_rank7 = t2_beys[6]
        t2_rank8 = t2_beys[7]

        t3_rank1 = t3_beys[0]
        t3_rank2 = t3_beys[1]
        t3_rank3 = t3_beys[2]
        t3_bottom5 = t3_beys[3:]

        cl_promoted = ["CL_1", "CL_2", "CL_3", "CL_4", "CL_5"]

        # Promotion/Relegation structure with playoffs resolved as upsets:
        # T1 #8 -> T2
        # T2 #1 -> T1
        # T2 #2 beats T1 #7 -> T2 #2 to T1, T1 #7 to T2
        # T2 #7-8 -> T3
        # T3 #1-2 -> T2
        # T3 #3 beats T2 #6 -> T3 #3 to T2, T2 #6 to T3
        # T3 #4-8 -> Pool
        # CL top 5 -> T3
        prom_rel = {
            "automatic_promotion": [
                {"bey": t2_rank1, "from_tier": 2, "to_tier": 1},
                {"bey": t2_rank2, "from_tier": 2, "to_tier": 1},  # Playoff winner
                {"bey": t3_rank1, "from_tier": 3, "to_tier": 2},
                {"bey": t3_rank2, "from_tier": 3, "to_tier": 2},
                {"bey": t3_rank3, "from_tier": 3, "to_tier": 2},  # Playoff winner
                {"bey": cl_promoted[0], "from_tier": "CL", "to_tier": 3},
                {"bey": cl_promoted[1], "from_tier": "CL", "to_tier": 3},
                {"bey": cl_promoted[2], "from_tier": "CL", "to_tier": 3},
                {"bey": cl_promoted[3], "from_tier": "CL", "to_tier": 3},
                {"bey": cl_promoted[4], "from_tier": "CL", "to_tier": 3},
            ],
            "automatic_relegation": [
                {"bey": t1_rank8, "from_tier": 1, "to_tier": 2},
                {"bey": t1_rank7, "from_tier": 1, "to_tier": 2},  # Playoff loser
                {"bey": t2_rank7, "from_tier": 2, "to_tier": 3},
                {"bey": t2_rank8, "from_tier": 2, "to_tier": 3},
                {"bey": t2_rank6, "from_tier": 2, "to_tier": 3},  # Playoff loser
            ],
            "relegation_matches": [],
            "qualification_candidates": [
                {"bey": b, "tier": 3, "reason": "tier3_bottom"} for b in t3_bottom5
            ],
        }

        s5_data, warnings = initialize_season_from_results(
            new_season_id="S5",
            prev_tier_assignments=season_data["tier_assignments"],
            prev_qualification_pool=season_data["qualification_pool"],
            promotion_relegation=prom_rel,
            elo_lookup=elo_lookup,
        )

        s5_t1 = [b for b, d in s5_data["tier_assignments"].items() if d["tier"] == 1]
        s5_t2 = [b for b, d in s5_data["tier_assignments"].items() if d["tier"] == 2]
        s5_t3 = [b for b, d in s5_data["tier_assignments"].items() if d["tier"] == 3]

        assert len(s5_t1) == 8, f"S5 Tier 1 must have 8 Beys, got {len(s5_t1)}"
        assert len(s5_t2) == 8, f"S5 Tier 2 must have 8 Beys, got {len(s5_t2)}"
        assert len(s5_t3) == 8, f"S5 Tier 3 must have 8 Beys, got {len(s5_t3)}"

        # Verify specific upset outcomes
        assert t2_rank2 in s5_t1, "T2 #2 must be promoted to Tier 1 after playoff win"
        assert t1_rank7 in s5_t2, "T1 #7 must be relegated to Tier 2 after playoff loss"
        assert t3_rank3 in s5_t2, "T3 #3 must be promoted to Tier 2 after playoff win"
        assert t2_rank6 in s5_t3, "T2 #6 must be relegated to Tier 3 after playoff loss"

        # Tier 3 is composed of: 2 direct T2 relegations + 1 playoff loser (T2 #6) + 5 CL promoted = 8 Beys!
        assert t2_rank7 in s5_t3
        assert t2_rank8 in s5_t3
        for b in cl_promoted:
            assert b in s5_t3
