"""
Unit tests for challenge_league.py module (Season 4+).
Tests qualification pool selection, weighted random draw, snake group assignment,
group standings, and final Swiss phase qualification.
"""
import pytest

from src.season.challenge_league import (
    calculate_selection_weight,
    get_relevant_participation_counts,
    select_challenge_league_beys,
    assign_challenge_groups,
    calculate_league_table,
    process_challenge_league,
    DEFAULT_CHALLENGE_LEAGUE_SIZE,
    DEFAULT_GROUPS_COUNT,
    DEFAULT_BEYS_PER_GROUP,
    DEFAULT_PROMOTIONS_TO_TIER3,
)


class TestRelevantParticipation:
    """Tests for counting relevant prior participations."""

    def test_counts_only_qualification_and_challenge_matches(self):
        matches = [
            {"bey_a": "BeyA", "bey_b": "BeyB", "match_type": "season"},
            {"bey_a": "BeyA", "bey_b": "BeyC", "match_type": "exhibition"},
            {"bey_a": "BeyA", "bey_b": "BeyD", "match_type": "qualification"},
            {"bey_a": "BeyB", "bey_b": "BeyD", "match_type": "challenge_group"},
            {"bey_a": "BeyB", "bey_b": "BeyE", "match_type": "challenge_final"},
        ]
        counts = get_relevant_participation_counts(matches)
        # BeyA played 1 qualification match
        assert counts.get("BeyA") == 1
        # BeyB played 1 challenge_group + 1 challenge_final = 2
        assert counts.get("BeyB") == 2
        # BeyC played only exhibition -> 0 (not in dict)
        assert counts.get("BeyC", 0) == 0
        # BeyD played 1 qualification + 1 challenge_group = 2
        assert counts.get("BeyD") == 2


class TestSelectionWeights:
    """Tests for selection weight calculations."""

    def test_weight_decreases_with_more_matches(self):
        w0 = calculate_selection_weight("Bey0", relevant_matches=0)
        w5 = calculate_selection_weight("Bey5", relevant_matches=5)
        w10 = calculate_selection_weight("Bey10", relevant_matches=10)

        assert w0 > w5 > w10
        assert w0 == 1.0  # 1 / (1 + 0)
        assert abs(w5 - (1.0 / 6.0)) < 1e-5

    def test_missed_previous_challenge_bonus(self):
        base_w = calculate_selection_weight("BeyA", relevant_matches=2, missed_previous_challenge=False)
        boosted_w = calculate_selection_weight("BeyA", relevant_matches=2, missed_previous_challenge=True)
        assert boosted_w > base_w
        assert abs(boosted_w - base_w * 1.5) < 1e-5

    def test_missed_multiple_seasons_bonus(self):
        w0 = calculate_selection_weight("BeyA", relevant_matches=2, missed_seasons_count=0)
        w2 = calculate_selection_weight("BeyA", relevant_matches=2, missed_seasons_count=2)
        assert w2 > w0


class TestWeightedSelection:
    """Tests for weighted selection without replacement."""

    def test_selects_exact_count(self):
        pool = [{"bey": f"Bey{i}", "elo": 1000 + i * 5} for i in range(34)]
        selected = select_challenge_league_beys(pool, count=24, seed=42)

        assert len(selected) == 24
        # Distinct beys (sampling without replacement)
        selected_names = [s["bey"] for s in selected]
        assert len(set(selected_names)) == 24

    def test_reproducible_with_seed(self):
        pool = [{"bey": f"Bey{i}", "elo": 1000 + i * 5} for i in range(34)]
        draw1 = select_challenge_league_beys(pool, count=24, seed=12345)
        draw2 = select_challenge_league_beys(pool, count=24, seed=12345)
        draw3 = select_challenge_league_beys(pool, count=24, seed=99999)

        assert [d["bey"] for d in draw1] == [d["bey"] for d in draw2]
        assert [d["bey"] for d in draw1] != [d["bey"] for d in draw3]

    def test_higher_weight_selected_more_frequently(self):
        # BeyLow has 0 matches (weight 1.0), BeyHigh has 99 matches (weight ~0.01)
        pool = [{"bey": "BeyLow", "elo": 1000}, {"bey": "BeyHigh", "elo": 1000}]
        p_counts = {"BeyLow": 0, "BeyHigh": 99}

        low_first_count = 0
        trials = 100
        for s in range(trials):
            drawn = select_challenge_league_beys(pool, count=1, seed=s, participation_counts=p_counts)
            if drawn[0]["bey"] == "BeyLow":
                low_first_count += 1

        assert low_first_count > 90

    def test_pool_smaller_than_count_returns_all(self):
        pool = [{"bey": "A", "elo": 1000}, {"bey": "B", "elo": 1020}]
        selected = select_challenge_league_beys(pool, count=24, seed=42)
        assert len(selected) == 2


class TestGroupAssignment:
    """Tests for Challenge League group assignment."""

    def test_snake_elo_distribution(self):
        beys = [{"bey": f"Bey{i:02d}", "elo": 1200 - i * 10} for i in range(24)]
        groups = assign_challenge_groups(beys, method="snake_elo")

        assert len(groups) == DEFAULT_GROUPS_COUNT
        assert all(len(g) == DEFAULT_BEYS_PER_GROUP for g in groups.values())

        # Round 1: A gets 0, B gets 1, C gets 2, D gets 3
        assert groups["A"][0]["bey"] == "Bey00"
        assert groups["B"][0]["bey"] == "Bey01"
        assert groups["C"][0]["bey"] == "Bey02"
        assert groups["D"][0]["bey"] == "Bey03"

        # Round 2 (snake): D gets 4, C gets 5, B gets 6, A gets 7
        assert groups["D"][1]["bey"] == "Bey04"
        assert groups["C"][1]["bey"] == "Bey05"
        assert groups["B"][1]["bey"] == "Bey06"
        assert groups["A"][1]["bey"] == "Bey07"

    def test_random_distribution(self):
        beys = [f"Bey{i}" for i in range(24)]
        groups = assign_challenge_groups(beys, method="random", seed=42)

        assert len(groups) == 4
        assert all(len(g) == 6 for g in groups.values())
        all_assigned = [b["bey"] for g in groups.values() for b in g]
        assert len(set(all_assigned)) == 24


class TestChallengeLeagueStandings:
    """Tests for group standings and final Swiss stage standings."""

    def test_group_stage_dominant_win_points(self):
        matches = [
            {"bey_a": "A", "bey_b": "B", "score_a": 4, "score_b": 0, "elo_a": 1000, "elo_b": 1000},
            {"bey_a": "C", "bey_b": "D", "score_a": 4, "score_b": 2, "elo_a": 1000, "elo_b": 1000},
        ]
        table = calculate_league_table(matches, expected_beys=["A", "B", "C", "D"])
        lookup = {row["bey"]: row for row in table}

        assert lookup["A"]["season_points"] == 4  # Dominant win (4-0)
        assert lookup["C"]["season_points"] == 3  # Normal win (4-2)
        assert lookup["B"]["season_points"] == 0
        assert lookup["D"]["season_points"] == 0

    def test_final_swiss_points_reset_to_zero(self):
        # Group stage matches where Bey1 had 9 points
        group_matches = [
            {"bey_a": "Q1", "bey_b": "X1", "score_a": 4, "score_b": 0, "match_type": "challenge_group", "season_id": "S4", "tier": "A"},
            {"bey_a": "Q1", "bey_b": "X2", "score_a": 4, "score_b": 0, "match_type": "challenge_group", "season_id": "S4", "tier": "A"},
        ]
        # Final Swiss matches where Q1 lost
        final_matches = [
            {"bey_a": "Q1", "bey_b": "Q2", "score_a": 1, "score_b": 4, "match_type": "challenge_final", "season_id": "S4"},
        ]
        all_matches = group_matches + final_matches
        groups = {"A": [{"bey": "Q1", "elo": 1000}, {"bey": "X1", "elo": 950}, {"bey": "X2", "elo": 900}]}

        res = process_challenge_league(all_matches, "S4", groups=groups)
        final_table = res["final_swiss"]
        q1_final = next(r for r in final_table if r["bey"] == "Q1")
        # Final Swiss points should strictly be 0 from the loss, NOT 8 from group wins!
        assert q1_final["season_points"] == 0


class TestEndToEndChallengeLeague:
    """Tests end-to-end processing of Challenge League."""

    def test_top5_promoted_and_remainder_returned(self):
        # 8 qualifiers in final swiss
        qualifiers = [f"Qual{i}" for i in range(1, 9)]
        final_matches = []
        # Qual1 beats Qual2, Qual3 beats Qual4, Qual5 beats Qual6, Qual7 beats Qual8
        final_matches.append({"bey_a": "Qual1", "bey_b": "Qual2", "score_a": 4, "score_b": 0, "match_type": "challenge_final", "season_id": "S4"})
        final_matches.append({"bey_a": "Qual3", "bey_b": "Qual4", "score_a": 4, "score_b": 1, "match_type": "challenge_final", "season_id": "S4"})
        final_matches.append({"bey_a": "Qual5", "bey_b": "Qual6", "score_a": 4, "score_b": 2, "match_type": "challenge_final", "season_id": "S4"})
        final_matches.append({"bey_a": "Qual7", "bey_b": "Qual8", "score_a": 4, "score_b": 3, "match_type": "challenge_final", "season_id": "S4"})
        # Round 2: Qual1 beats Qual3, Qual5 beats Qual7
        final_matches.append({"bey_a": "Qual1", "bey_b": "Qual3", "score_a": 4, "score_b": 0, "match_type": "challenge_final", "season_id": "S4"})
        final_matches.append({"bey_a": "Qual5", "bey_b": "Qual7", "score_a": 4, "score_b": 1, "match_type": "challenge_final", "season_id": "S4"})

        groups = {
            "A": [{"bey": "Qual1", "elo": 1000}, {"bey": "Qual2", "elo": 1000}],
            "B": [{"bey": "Qual3", "elo": 1000}, {"bey": "Qual4", "elo": 1000}],
            "C": [{"bey": "Qual5", "elo": 1000}, {"bey": "Qual6", "elo": 1000}],
            "D": [{"bey": "Qual7", "elo": 1000}, {"bey": "Qual8", "elo": 1000}],
        }

        res = process_challenge_league(final_matches, "S4", groups=groups)
        assert len(res["promoted_to_tier3"]) == DEFAULT_PROMOTIONS_TO_TIER3
        assert "Qual1" in res["promoted_to_tier3"]
        assert len(res["final_swiss"]) == 8
