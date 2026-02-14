"""
Unit tests for tournament_brackets.py module.
Tests the Tournament Bracket Generator for low-data beys.
"""
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tournament_brackets import (
    identify_low_data_beys,
    generate_round_robin_bracket,
    generate_single_elimination_bracket,
    recommend_tournament_type,
    generate_tournament_schedule,
    CONFIG,
)


class TestConfiguration:
    """Tests for configuration constants."""

    def test_config_has_required_keys(self):
        """Config should have all required keys."""
        required = {
            "low_data_threshold_percentile",
            "min_matches_for_tournament",
            "min_participants",
            "round_robin_max_participants",
            "preferred_bracket_sizes",
        }
        assert required == set(CONFIG.keys())

    def test_percentiles_in_valid_range(self):
        """Percentiles should be between 0 and 1."""
        assert 0 < CONFIG["low_data_threshold_percentile"] <= 1

    def test_thresholds_positive(self):
        """Numeric thresholds should be positive."""
        assert CONFIG["min_matches_for_tournament"] >= 0
        assert CONFIG["min_participants"] > 0
        assert CONFIG["round_robin_max_participants"] > 0
        assert len(CONFIG["preferred_bracket_sizes"]) > 0


class TestLowDataIdentification:
    """Tests for low-data Bey identification."""

    def test_identifies_low_data_beys(self):
        """Should identify Beys with fewer matches."""
        beys = {
            "BeyA": {"matches": 3},
            "BeyB": {"matches": 5},
            "BeyC": {"matches": 10},
            "BeyD": {"matches": 15},
            "BeyE": {"matches": 20},
        }
        low_data = identify_low_data_beys(beys)
        # Should identify some of the lower ones
        assert len(low_data) > 0
        assert all(beys[name]["matches"] <= 10 for name in low_data)

    def test_excludes_insufficient_data(self):
        """Should exclude Beys below minimum threshold."""
        beys = {
            "BeyA": {"matches": 1},  # Below minimum
            "BeyB": {"matches": 10},
            "BeyC": {"matches": 15},
        }
        low_data = identify_low_data_beys(beys)
        assert "BeyA" not in low_data

    def test_handles_empty_dataset(self):
        """Should handle empty dataset gracefully."""
        low_data = identify_low_data_beys({})
        assert low_data == []


class TestRoundRobinBracketGeneration:
    """Tests for round-robin bracket generation."""

    def test_generates_bracket_for_even_participants(self):
        """Should generate valid round-robin for even number of participants."""
        participants = ["BeyA", "BeyB", "BeyC", "BeyD"]
        matchups = {}

        bracket = generate_round_robin_bracket(participants, matchups)

        assert bracket["format"] == "round_robin"
        assert len(bracket["participants"]) == 4
        assert bracket["total_rounds"] == 3  # n-1 rounds for n participants
        assert bracket["total_matches"] == 6  # n*(n-1)/2 total matches

    def test_generates_bracket_for_odd_participants(self):
        """Should handle odd number of participants with byes."""
        participants = ["BeyA", "BeyB", "BeyC"]
        matchups = {}

        bracket = generate_round_robin_bracket(participants, matchups)

        assert bracket["format"] == "round_robin"
        assert len(bracket["participants"]) == 3
        assert "BYE" not in bracket["participants"]

    def test_includes_existing_match_counts(self):
        """Should include existing match counts in bracket."""
        participants = ["BeyA", "BeyB"]
        matchups = {("BeyA", "BeyB"): 2}

        bracket = generate_round_robin_bracket(participants, matchups)

        # Check that existing matches are recorded
        match = bracket["rounds"][0]["matches"][0]
        assert match["existing_matches"] == 2

    def test_handles_empty_participants(self):
        """Should handle empty participant list."""
        bracket = generate_round_robin_bracket([], {})
        assert bracket["rounds"] == []

    def test_all_participants_play_each_other(self):
        """Should ensure all participants play each other once."""
        participants = ["BeyA", "BeyB", "BeyC", "BeyD"]
        matchups = {}

        bracket = generate_round_robin_bracket(participants, matchups)

        # Collect all matchups
        all_matchups = set()
        for round_data in bracket["rounds"]:
            for match in round_data["matches"]:
                pair = tuple(sorted([match["bey_a"], match["bey_b"]]))
                all_matchups.add(pair)

        # Should have n*(n-1)/2 unique pairs
        assert len(all_matchups) == 6  # 4*3/2


class TestSingleEliminationBracketGeneration:
    """Tests for single elimination bracket generation."""

    def test_generates_bracket_for_power_of_two(self):
        """Should generate valid bracket for power of 2 participants."""
        participants = ["BeyA", "BeyB", "BeyC", "BeyD"]
        matchups = {}

        bracket = generate_single_elimination_bracket(participants, matchups)

        assert bracket["format"] == "single_elimination"
        assert len(bracket["participants"]) == 4
        # 4 participants = 2 rounds (semis + finals)
        assert bracket["total_rounds"] == 2
        assert bracket["total_matches"] == 3  # 2 semis + 1 final

    def test_handles_non_power_of_two(self):
        """Should pad to next power of 2 with byes."""
        participants = ["BeyA", "BeyB", "BeyC"]
        matchups = {}

        bracket = generate_single_elimination_bracket(participants, matchups)

        assert bracket["format"] == "single_elimination"
        assert len(bracket["participants"]) == 3
        # Should work with 4-participant bracket (1 bye)

    def test_round_names_are_correct(self):
        """Should have correct round names."""
        participants = ["BeyA", "BeyB", "BeyC", "BeyD"]
        matchups = {}

        bracket = generate_single_elimination_bracket(participants, matchups)

        round_names = [r["name"] for r in bracket["rounds"]]
        assert "Semi-Finals" in round_names
        assert "Finals" in round_names

    def test_includes_existing_match_counts(self):
        """Should include existing match counts in bracket."""
        participants = ["BeyA", "BeyB", "BeyC", "BeyD"]
        matchups = {("BeyA", "BeyB"): 1}

        bracket = generate_single_elimination_bracket(participants, matchups)

        # Find the match between BeyA and BeyB
        for round_data in bracket["rounds"]:
            for match in round_data["matches"]:
                if set([match["bey_a"], match["bey_b"]]) == set(["BeyA", "BeyB"]):
                    assert match["existing_matches"] == 1

    def test_handles_empty_participants(self):
        """Should handle empty participant list."""
        bracket = generate_single_elimination_bracket([], {})
        assert bracket["rounds"] == []

    def test_match_ids_are_unique(self):
        """Should generate unique match IDs."""
        participants = ["BeyA", "BeyB", "BeyC", "BeyD", "BeyE", "BeyF", "BeyG", "BeyH"]
        matchups = {}

        bracket = generate_single_elimination_bracket(participants, matchups)

        match_ids = []
        for round_data in bracket["rounds"]:
            for match in round_data["matches"]:
                match_ids.append(match["match_id"])

        assert len(match_ids) == len(set(match_ids))  # All unique


class TestTournamentRecommendation:
    """Tests for tournament type recommendation."""

    def test_recommends_nothing_for_few_participants(self):
        """Should not recommend tournament if too few participants."""
        low_data_beys = ["BeyA", "BeyB"]
        beys = {
            "BeyA": {"matches": 3},
            "BeyB": {"matches": 4},
        }

        rec = recommend_tournament_type(low_data_beys, beys)

        assert rec["recommended"] is None
        assert "Not enough" in rec["reason"]

    def test_recommends_round_robin_for_small_group(self):
        """Should recommend round-robin for small groups."""
        low_data_beys = ["BeyA", "BeyB", "BeyC", "BeyD", "BeyE"]
        beys = {name: {"matches": 3} for name in low_data_beys}

        rec = recommend_tournament_type(low_data_beys, beys)

        assert rec["recommended"] == "round_robin"
        assert "benefits" in rec

    def test_recommends_single_elim_for_large_group(self):
        """Should recommend single elimination for large groups."""
        low_data_beys = [f"Bey{i}" for i in range(15)]
        beys = {name: {"matches": 3} for name in low_data_beys}

        rec = recommend_tournament_type(low_data_beys, beys)

        assert rec["recommended"] == "single_elimination"
        assert "benefits" in rec

    def test_recommendation_includes_reason(self):
        """Should include explanatory reason."""
        low_data_beys = ["BeyA", "BeyB", "BeyC", "BeyD"]
        beys = {name: {"matches": 3} for name in low_data_beys}

        rec = recommend_tournament_type(low_data_beys, beys)

        assert "reason" in rec
        assert len(rec["reason"]) > 0


class TestScheduleGeneration:
    """Tests for tournament schedule generation."""

    def test_generates_schedule_with_dates(self):
        """Should generate schedule with dates."""
        bracket = {
            "rounds": [
                {
                    "round": 1,
                    "matches": [
                        {"bey_a": "BeyA", "bey_b": "BeyB", "existing_matches": 0}
                    ]
                }
            ]
        }

        schedule = generate_tournament_schedule(bracket)

        assert len(schedule) > 0
        assert "date" in schedule[0]
        assert "bey_a" in schedule[0]
        assert "bey_b" in schedule[0]

    def test_different_rounds_on_different_days(self):
        """Should schedule different rounds on different days."""
        bracket = {
            "rounds": [
                {
                    "round": 1,
                    "matches": [{"bey_a": "BeyA", "bey_b": "BeyB"}]
                },
                {
                    "round": 2,
                    "matches": [{"bey_a": "BeyC", "bey_b": "BeyD"}]
                }
            ]
        }

        schedule = generate_tournament_schedule(bracket)

        assert len(schedule) == 2
        assert schedule[0]["date"] != schedule[1]["date"]

    def test_accepts_custom_start_date(self):
        """Should accept custom start date."""
        bracket = {
            "rounds": [
                {
                    "round": 1,
                    "matches": [{"bey_a": "BeyA", "bey_b": "BeyB"}]
                }
            ]
        }

        schedule = generate_tournament_schedule(bracket, "2025-06-01")

        assert schedule[0]["date"] == "2025-06-01"

    def test_handles_empty_bracket(self):
        """Should handle empty bracket."""
        bracket = {"rounds": []}
        schedule = generate_tournament_schedule(bracket)
        assert schedule == []


class TestBracketDataStructure:
    """Tests for bracket data structure."""

    def test_round_robin_has_required_fields(self):
        """Round-robin bracket should have required fields."""
        participants = ["BeyA", "BeyB", "BeyC", "BeyD"]
        bracket = generate_round_robin_bracket(participants, {})

        required = {"format", "participants", "total_rounds", "total_matches", "rounds"}
        assert required == set(bracket.keys())

    def test_single_elim_has_required_fields(self):
        """Single elimination bracket should have required fields."""
        participants = ["BeyA", "BeyB", "BeyC", "BeyD"]
        bracket = generate_single_elimination_bracket(participants, {})

        required = {"format", "participants", "total_rounds", "total_matches", "rounds"}
        assert required == set(bracket.keys())

    def test_matches_have_participant_info(self):
        """Matches should have participant information."""
        participants = ["BeyA", "BeyB"]
        bracket = generate_round_robin_bracket(participants, {})

        match = bracket["rounds"][0]["matches"][0]
        assert "bey_a" in match
        assert "bey_b" in match
        assert "existing_matches" in match

    def test_round_robin_match_count_is_correct(self):
        """Total matches should equal n*(n-1)/2."""
        for n in [4, 5, 6, 7, 8]:
            participants = [f"Bey{i}" for i in range(n)]
            bracket = generate_round_robin_bracket(participants, {})

            expected_matches = n * (n - 1) // 2
            assert bracket["total_matches"] == expected_matches

    def test_single_elim_match_count_is_correct(self):
        """Total matches should equal participants - 1."""
        for n in [4, 8, 16]:
            participants = [f"Bey{i}" for i in range(n)]
            bracket = generate_single_elimination_bracket(participants, {})

            expected_matches = n - 1
            assert bracket["total_matches"] == expected_matches
