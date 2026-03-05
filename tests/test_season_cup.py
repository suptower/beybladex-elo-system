"""
Unit tests for season_cup.py module.
Tests Season Cup qualification, bracket generation, and tournament logic.
"""
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'season'))

from season_cup import (
    get_qualified_beys,
    generate_double_elimination_bracket,
    update_bracket_with_match,
    get_cup_winner,
    export_bracket_for_display
)


class TestQualification:
    """Tests for Season Cup qualification logic."""

    def test_tier_1_qualifies_4(self):
        """Tier I should qualify top 4 beys."""
        league_tables = {
            1: [{"bey": f"T1-{i}", "elo": 1500 - i} for i in range(1, 11)]
        }

        qualified = get_qualified_beys(league_tables)
        tier1_qualified = [q for q in qualified if q["tier"] == 1]

        assert len(tier1_qualified) == 4
        assert tier1_qualified[0]["bey"] == "T1-1"
        assert tier1_qualified[3]["bey"] == "T1-4"

    def test_tier_2_qualifies_2(self):
        """Tier II should qualify top 2 beys."""
        league_tables = {
            2: [{"bey": f"T2-{i}", "elo": 1400 - i} for i in range(1, 9)]
        }

        qualified = get_qualified_beys(league_tables)
        tier2_qualified = [q for q in qualified if q["tier"] == 2]

        assert len(tier2_qualified) == 2
        assert tier2_qualified[0]["bey"] == "T2-1"
        assert tier2_qualified[1]["bey"] == "T2-2"

    def test_tier_3_qualifies_1(self):
        """Tier III should qualify top 1 bey."""
        league_tables = {
            3: [{"bey": f"T3-{i}", "elo": 1300 - i} for i in range(1, 11)]
        }

        qualified = get_qualified_beys(league_tables)
        tier3_qualified = [q for q in qualified if q["tier"] == 3]

        assert len(tier3_qualified) == 1
        assert tier3_qualified[0]["bey"] == "T3-1"

    def test_tier_4_qualifies_1(self):
        """Tier IV should qualify top 1 bey."""
        league_tables = {
            4: [{"bey": f"T4-{i}", "elo": 1200 - i} for i in range(1, 9)]
        }

        qualified = get_qualified_beys(league_tables)
        tier4_qualified = [q for q in qualified if q["tier"] == 4]

        assert len(tier4_qualified) == 1
        assert tier4_qualified[0]["bey"] == "T4-1"

    def test_total_qualified_is_8(self):
        """Total qualified beys should be 8 (4+2+1+1)."""
        league_tables = {
            1: [{"bey": f"T1-{i}", "elo": 1500 - i} for i in range(1, 9)],
            2: [{"bey": f"T2-{i}", "elo": 1400 - i} for i in range(1, 9)],
            3: [{"bey": f"T3-{i}", "elo": 1300 - i} for i in range(1, 9)],
            4: [{"bey": f"T4-{i}", "elo": 1200 - i} for i in range(1, 9)]
        }

        qualified = get_qualified_beys(league_tables)
        assert len(qualified) == 8

    def test_seeding_order(self):
        """Qualified beys should be seeded 1-8 in order."""
        league_tables = {
            1: [{"bey": f"T1-{i}", "elo": 1500 - i} for i in range(1, 9)],
            2: [{"bey": f"T2-{i}", "elo": 1400 - i} for i in range(1, 9)],
            3: [{"bey": f"T3-{i}", "elo": 1300 - i} for i in range(1, 9)],
            4: [{"bey": f"T4-{i}", "elo": 1200 - i} for i in range(1, 9)]
        }

        qualified = get_qualified_beys(league_tables)

        # Check seeding is sequential
        for i, q in enumerate(qualified):
            assert q["seed"] == i + 1

    def test_insufficient_beys_in_tier(self):
        """Should handle tiers with fewer than expected beys."""
        league_tables = {
            1: [{"bey": f"T1-{i}", "elo": 1500} for i in range(1, 3)],  # Only 2 beys
            2: [{"bey": f"T2-{i}", "elo": 1400} for i in range(1, 11)]
        }

        qualified = get_qualified_beys(league_tables)
        tier1_qualified = [q for q in qualified if q["tier"] == 1]

        # Should only qualify 2 from Tier 1 (not 4)
        assert len(tier1_qualified) == 2


class TestBracketGeneration:
    """Tests for double-elimination bracket generation."""

    def test_bracket_structure(self):
        """Bracket should have correct structure."""
        qualified = [
            {"bey": f"Bey{i}", "seed": i, "tier": 1, "position": 1, "elo": 1500 - i * 10}
            for i in range(1, 9)
        ]

        bracket = generate_double_elimination_bracket(qualified)

        assert bracket["format"] == "double_elimination"
        assert "winners_bracket" in bracket
        assert "losers_bracket" in bracket
        assert "grand_final" in bracket
        assert bracket["cup_winner"] is None

    def test_winners_bracket_rounds(self):
        """Winners bracket should have correct rounds."""
        qualified = [
            {"bey": f"Bey{i}", "seed": i, "tier": 1, "position": 1, "elo": 1500}
            for i in range(1, 9)
        ]

        bracket = generate_double_elimination_bracket(qualified)
        wb = bracket["winners_bracket"]

        assert "round_1" in wb
        assert "round_2" in wb
        assert "finals" in wb
        assert len(wb["round_1"]) == 4  # 4 matches in first round
        assert len(wb["round_2"]) == 2  # 2 matches in second round

    def test_losers_bracket_rounds(self):
        """Losers bracket should have correct rounds."""
        qualified = [
            {"bey": f"Bey{i}", "seed": i, "tier": 1, "position": 1, "elo": 1500}
            for i in range(1, 9)
        ]

        bracket = generate_double_elimination_bracket(qualified)
        lb = bracket["losers_bracket"]

        assert "round_1" in lb
        assert "round_2" in lb
        assert "round_3" in lb
        assert "finals" in lb
        assert len(lb["round_1"]) == 2
        assert len(lb["round_2"]) == 2

    def test_seeding_matchups(self):
        """First round should match seeds correctly (1v8, 4v5, 2v7, 3v6)."""
        qualified = [
            {"bey": f"Bey{i}", "seed": i, "tier": 1, "position": 1, "elo": 1500}
            for i in range(1, 9)
        ]

        bracket = generate_double_elimination_bracket(qualified)
        r1_matches = bracket["winners_bracket"]["round_1"]

        # Match 1: 1 vs 8
        assert r1_matches[0]["seed_a"] == 1
        assert r1_matches[0]["seed_b"] == 8

        # Match 2: 4 vs 5
        assert r1_matches[1]["seed_a"] == 4
        assert r1_matches[1]["seed_b"] == 5

        # Match 3: 2 vs 7
        assert r1_matches[2]["seed_a"] == 2
        assert r1_matches[2]["seed_b"] == 7

        # Match 4: 3 vs 6
        assert r1_matches[3]["seed_a"] == 3
        assert r1_matches[3]["seed_b"] == 6

    def test_invalid_participant_count(self):
        """Should raise error if not exactly 8 participants."""
        qualified = [
            {"bey": f"Bey{i}", "seed": i, "tier": 1, "position": 1, "elo": 1500}
            for i in range(1, 7)  # Only 6
        ]

        try:
            generate_double_elimination_bracket(qualified)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Expected 8" in str(e)


class TestBracketUpdate:
    """Tests for bracket update with match results."""

    def test_update_match(self):
        """Should update match with result."""
        qualified = [
            {"bey": f"Bey{i}", "seed": i, "tier": 1, "position": 1, "elo": 1500}
            for i in range(1, 9)
        ]

        bracket = generate_double_elimination_bracket(qualified)

        # Update first match
        updated = update_bracket_with_match(
            bracket, "WB-R1-M1", "Bey1", 4, 2, "Bey1", "Bey8"
        )

        # Find the updated match
        match = updated["winners_bracket"]["round_1"][0]
        assert match["winner"] == "Bey1"
        assert match["score_a"] == 4
        assert match["score_b"] == 2


class TestCupWinner:
    """Tests for determining cup winner."""

    def test_no_winner_incomplete_bracket(self):
        """Should return None if grand final not complete."""
        qualified = [
            {"bey": f"Bey{i}", "seed": i, "tier": 1, "position": 1, "elo": 1500}
            for i in range(1, 9)
        ]

        bracket = generate_double_elimination_bracket(qualified)
        winner = get_cup_winner(bracket)
        assert winner is None

    def test_winner_from_grand_final(self):
        """Should return winner from completed grand final."""
        qualified = [
            {"bey": f"Bey{i}", "seed": i, "tier": 1, "position": 1, "elo": 1500}
            for i in range(1, 9)
        ]

        bracket = generate_double_elimination_bracket(qualified)
        bracket["grand_final"]["winner"] = "Champion"

        winner = get_cup_winner(bracket)
        assert winner == "Champion"
        assert bracket["cup_winner"] == "Champion"


class TestBracketExport:
    """Tests for bracket export for display."""

    def test_export_simplifies_structure(self):
        """Export should create simplified structure."""
        qualified = [
            {"bey": f"Bey{i}", "seed": i, "tier": 1, "position": 1, "elo": 1500}
            for i in range(1, 9)
        ]

        bracket = generate_double_elimination_bracket(qualified)
        display = export_bracket_for_display(bracket)

        assert "format" in display
        assert "winners_bracket" in display
        assert "losers_bracket" in display
        assert "grand_final" in display

    def test_export_match_format(self):
        """Exported matches should have simplified format."""
        qualified = [
            {"bey": f"Bey{i}", "seed": i, "tier": 1, "position": 1, "elo": 1500}
            for i in range(1, 9)
        ]

        bracket = generate_double_elimination_bracket(qualified)
        display = export_bracket_for_display(bracket)

        # Check a round 1 match
        if display["winners_bracket"]["round_1"]:
            match = display["winners_bracket"]["round_1"][0]
            assert "id" in match
            assert "participants" in match
            assert len(match["participants"]) == 2
