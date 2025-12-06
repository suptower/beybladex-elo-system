"""
Tests for Custom Tournament Engine

Tests tournament creation, pairing algorithms, match reporting,
standings calculation, and persistence.
"""

import pytest
import json
import tempfile
import os
from src.tournament_engine import (
    Tournament,
    TournamentFormat,
    MatchStatus,
    Participant,
    Match,
    Standing
)


class TestTournamentCreation:
    """Test tournament initialization and setup"""

    def test_create_swiss_tournament(self):
        """Test creating a Swiss format tournament"""
        tournament = Tournament(
            name="Test Swiss",
            format="swiss",
            participants=["P1", "P2", "P3", "P4"]
        )
        assert tournament.name == "Test Swiss"
        assert tournament.format == TournamentFormat.SWISS
        assert len(tournament.participants) == 4

    def test_create_single_elim_tournament(self):
        """Test creating a single elimination tournament"""
        tournament = Tournament(
            name="Test SE",
            format="single_elimination",
            participants=["P1", "P2", "P3", "P4"]
        )
        assert tournament.format == TournamentFormat.SINGLE_ELIMINATION

    def test_auto_calculate_rounds_swiss(self):
        """Test automatic round calculation for Swiss"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            participants=["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]
        )
        # For 8 players, typically 3 rounds (log2(8))
        assert tournament.num_rounds == 3

    def test_auto_calculate_rounds_knockout(self):
        """Test automatic round calculation for knockout"""
        tournament = Tournament(
            name="Test",
            format="single_elimination",
            participants=["P1", "P2", "P3", "P4"]
        )
        # For 4 players, need 2 rounds
        assert tournament.num_rounds == 2

    def test_add_participant(self):
        """Test adding participants"""
        tournament = Tournament(name="Test", format="swiss")
        tournament.add_participant("Player1", seed=1)
        tournament.add_participant("Player2", seed=2)
        
        assert len(tournament.participants) == 2
        assert "Player1" in tournament.participants
        assert tournament.participants["Player1"].seed == 1

    def test_cannot_add_participant_after_start(self):
        """Test that participants cannot be added after tournament starts"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            participants=["P1", "P2"]
        )
        tournament.start()
        
        with pytest.raises(ValueError, match="Cannot add participants"):
            tournament.add_participant("P3")

    def test_tournament_id_generation(self):
        """Test automatic tournament ID generation"""
        tournament = Tournament(name="Test", format="swiss")
        assert tournament.tournament_id.startswith("tournament_")
        assert len(tournament.tournament_id) > len("tournament_")

    def test_custom_tournament_id(self):
        """Test using custom tournament ID"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            tournament_id="custom_id_123"
        )
        assert tournament.tournament_id == "custom_id_123"


class TestTournamentStart:
    """Test tournament start and initial pairing generation"""

    def test_start_tournament(self):
        """Test starting a tournament"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            participants=["P1", "P2", "P3", "P4"]
        )
        assert not tournament.started
        
        tournament.start()
        
        assert tournament.started
        assert tournament.current_round == 1
        assert len(tournament.matches) > 0

    def test_cannot_start_with_insufficient_players(self):
        """Test that tournament requires at least 2 players"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            participants=["P1"]
        )
        
        with pytest.raises(ValueError, match="at least 2"):
            tournament.start()

    def test_cannot_start_twice(self):
        """Test that tournament cannot be started twice"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            participants=["P1", "P2"]
        )
        tournament.start()
        
        with pytest.raises(ValueError, match="already started"):
            tournament.start()

    def test_first_round_pairings_created(self):
        """Test that first round pairings are created on start"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            participants=["P1", "P2", "P3", "P4"]
        )
        tournament.start()
        
        round1_matches = [m for m in tournament.matches if m.round_num == 1]
        assert len(round1_matches) == 2  # 4 players = 2 matches


class TestSwissPairing:
    """Test Swiss system pairing algorithm"""

    def test_first_round_pairing_count(self):
        """Test correct number of pairings in first round"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            participants=["P1", "P2", "P3", "P4", "P5", "P6"]
        )
        tournament.start()
        
        round1_matches = tournament.get_matches(round_num=1)
        assert len(round1_matches) == 3  # 6 players = 3 matches

    def test_bye_handling_odd_players(self):
        """Test bye handling with odd number of players"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            participants=["P1", "P2", "P3"]
        )
        tournament.start()
        
        round1_matches = tournament.get_matches(round_num=1)
        # Should have 2 matches (one regular, one bye)
        assert len(round1_matches) == 2
        
        # One match should be a bye
        bye_matches = [m for m in round1_matches if m["player_b"] is None]
        assert len(bye_matches) == 1

    def test_no_rematches_in_swiss(self):
        """Test that Swiss pairing avoids rematches when possible"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            num_rounds=2,
            participants=["P1", "P2", "P3", "P4"]
        )
        tournament.start()

        # Get the actual matches and report them
        round1_matches = tournament.get_matches(round_num=1)
        tournament.report_match(1, 0, round1_matches[0]["player_a"], 4, 0)
        tournament.report_match(1, 1, round1_matches[1]["player_a"], 4, 0)

        # Round 2 should pair winners together
        round2_matches = tournament.get_matches(round_num=2)
        assert len(round2_matches) == 2

        # Winners should not be paired with same opponent
        for match in round2_matches:
            # Check pairing history
            pair = tuple(sorted([match["player_a"], match["player_b"]]))
            assert tournament.pairings_history.get(pair, 0) <= 1


class TestMatchReporting:
    """Test match result reporting"""

    def test_report_match_result(self):
        """Test basic match result reporting"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            participants=["P1", "P2"]
        )
        tournament.start()
        
        tournament.report_match(1, 0, "P1", 4, 2)
        
        matches = tournament.get_matches(round_num=1)
        match = matches[0]
        assert match["winner"] == "P1"
        assert match["score_a"] == 4
        assert match["score_b"] == 2
        assert match["status"] == "completed"

    def test_cannot_report_nonexistent_match(self):
        """Test that reporting nonexistent match raises error"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            participants=["P1", "P2"]
        )
        tournament.start()
        
        with pytest.raises(ValueError, match="Match not found"):
            tournament.report_match(99, 99, "P1", 4, 0)

    def test_cannot_report_completed_match(self):
        """Test that completed match cannot be reported again"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            participants=["P1", "P2"]
        )
        tournament.start()
        tournament.report_match(1, 0, "P1", 4, 0)
        
        with pytest.raises(ValueError, match="already completed"):
            tournament.report_match(1, 0, "P2", 4, 0)

    def test_standings_updated_after_match(self):
        """Test that standings are updated after match"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            participants=["P1", "P2"]
        )
        tournament.start()
        
        tournament.report_match(1, 0, "P1", 4, 2)
        
        standings = tournament.get_standings()
        p1_standing = next(s for s in standings if s["player"] == "P1")
        p2_standing = next(s for s in standings if s["player"] == "P2")
        
        assert p1_standing["wins"] == 1
        assert p1_standing["points"] == 1.0
        assert p2_standing["losses"] == 1
        assert p2_standing["points"] == 0.0


class TestStandings:
    """Test standings calculation and tie-breakers"""

    def test_initial_standings(self):
        """Test initial standings before any matches"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            participants=["P1", "P2", "P3"]
        )
        
        standings = tournament.get_standings()
        assert len(standings) == 3
        
        for standing in standings:
            assert standing["wins"] == 0
            assert standing["losses"] == 0
            assert standing["points"] == 0.0

    def test_standings_sorting(self):
        """Test that standings are sorted correctly"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            participants=["P1", "P2", "P3", "P4"]
        )
        tournament.start()
        
        # Get the actual matches and report winners
        round1_matches = tournament.get_matches(round_num=1)
        
        # Report first match
        match0 = round1_matches[0]
        tournament.report_match(1, 0, match0["player_a"], 4, 0)
        
        # Report second match
        match1 = round1_matches[1]
        tournament.report_match(1, 1, match1["player_a"], 4, 0)
        
        standings = tournament.get_standings()
        
        # Winners should be ranked higher
        assert standings[0]["wins"] == 1
        assert standings[1]["wins"] == 1
        assert standings[2]["wins"] == 0

    def test_buchholz_calculation(self):
        """Test Buchholz tie-breaker calculation"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            num_rounds=2,
            participants=["P1", "P2", "P3", "P4"]
        )
        tournament.start()

        # Get the actual matches and report them
        round1_matches = tournament.get_matches(round_num=1)
        tournament.report_match(1, 0, round1_matches[0]["player_a"], 4, 0)
        tournament.report_match(1, 1, round1_matches[1]["player_a"], 4, 0)

        standings = tournament.get_standings()

        # Check that Buchholz is calculated
        for standing in standings:
            assert "buchholz" in standing
            assert isinstance(standing["buchholz"], (int, float))

    def test_game_wins_tracking(self):
        """Test that game wins/losses are tracked"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            participants=["P1", "P2"]
        )
        tournament.start()

        # Get the actual match and report it
        round1_matches = tournament.get_matches(round_num=1)
        match = round1_matches[0]
        winner = match["player_a"]
        loser = match["player_b"]
        tournament.report_match(1, 0, winner, 4, 2)

        standings = tournament.get_standings()
        winner_standing = next(s for s in standings if s["player"] == winner)
        loser_standing = next(s for s in standings if s["player"] == loser)

        assert winner_standing["game_wins"] == 4
        assert winner_standing["game_losses"] == 2
        assert loser_standing["game_wins"] == 2
        assert loser_standing["game_losses"] == 4


class TestRoundProgression:
    """Test multi-round tournament progression"""

    def test_round_completion_triggers_next_round(self):
        """Test that completing round generates next round pairings"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            num_rounds=2,
            participants=["P1", "P2", "P3", "P4"]
        )
        tournament.start()
        
        # Complete all round 1 matches using actual participants
        round1_matches = tournament.get_matches(round_num=1)
        tournament.report_match(1, 0, round1_matches[0]["player_a"], 4, 0)
        tournament.report_match(1, 1, round1_matches[1]["player_a"], 4, 0)
        
        # Round 2 should be automatically generated
        round2_matches = tournament.get_matches(round_num=2)
        assert len(round2_matches) > 0
        assert tournament.current_round == 2

    def test_tournament_completes_after_final_round(self):
        """Test that tournament is marked complete after final round"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            num_rounds=1,
            participants=["P1", "P2"]
        )
        tournament.start()
        
        assert not tournament.completed
        
        tournament.report_match(1, 0, "P1", 4, 0)
        
        assert tournament.completed


class TestKnockoutTournaments:
    """Test single and double elimination tournaments"""

    def test_single_elimination_bracket(self):
        """Test single elimination bracket generation"""
        tournament = Tournament(
            name="Test SE",
            format="single_elimination",
            participants=["P1", "P2", "P3", "P4"]
        )
        tournament.start()
        
        # Round 1 should have 2 matches (4 players)
        round1_matches = tournament.get_matches(round_num=1)
        assert len(round1_matches) == 2

    def test_single_elimination_advancement(self):
        """Test that winners advance in single elimination"""
        tournament = Tournament(
            name="Test SE",
            format="single_elimination",
            participants=["P1", "P2", "P3", "P4"]
        )
        tournament.start()
        
        # Complete round 1
        tournament.report_match(1, 0, "P1", 4, 0)
        tournament.report_match(1, 1, "P3", 4, 0)
        
        # Round 2 (finals) should pair the winners
        round2_matches = tournament.get_matches(round_num=2)
        assert len(round2_matches) == 1
        
        # Check that winners advanced
        match = round2_matches[0]
        assert set([match["player_a"], match["player_b"]]) == {"P1", "P3"}


class TestPersistence:
    """Test tournament save and load functionality"""

    def test_save_tournament(self):
        """Test saving tournament to JSON"""
        tournament = Tournament(
            name="Test Tournament",
            format="swiss",
            participants=["P1", "P2", "P3", "P4"]
        )
        tournament.start()
        
        # Get the actual match and report it
        round1_matches = tournament.get_matches(round_num=1)
        tournament.report_match(1, 0, round1_matches[0]["player_a"], 4, 2)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        
        try:
            tournament.save(filepath)
            
            # Check file exists and is valid JSON
            assert os.path.exists(filepath)
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            assert data["name"] == "Test Tournament"
            assert data["format"] == "swiss"
            assert len(data["participants"]) == 4
        finally:
            os.unlink(filepath)

    def test_load_tournament(self):
        """Test loading tournament from JSON"""
        tournament = Tournament(
            name="Test Tournament",
            format="swiss",
            participants=["P1", "P2", "P3", "P4"]
        )
        tournament.start()
        
        # Get the actual match and report it
        round1_matches = tournament.get_matches(round_num=1)
        tournament.report_match(1, 0, round1_matches[0]["player_a"], 4, 2)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        
        try:
            tournament.save(filepath)
            loaded = Tournament.load(filepath)
            
            assert loaded.name == tournament.name
            assert loaded.format == tournament.format
            assert len(loaded.participants) == len(tournament.participants)
            assert loaded.started == tournament.started
            assert len(loaded.matches) == len(tournament.matches)
        finally:
            os.unlink(filepath)

    def test_save_and_load_preserves_state(self):
        """Test that save/load preserves tournament state"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            num_rounds=2,
            participants=["P1", "P2", "P3", "P4"]
        )
        tournament.start()
        
        # Get the actual matches and report them
        round1_matches = tournament.get_matches(round_num=1)
        tournament.report_match(1, 0, round1_matches[0]["player_a"], 4, 2)
        tournament.report_match(1, 1, round1_matches[1]["player_a"], 4, 1)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        
        try:
            tournament.save(filepath)
            loaded = Tournament.load(filepath)
            
            # Check standings are preserved
            original_standings = tournament.get_standings()
            loaded_standings = loaded.get_standings()
            
            assert len(original_standings) == len(loaded_standings)
            
            for orig, load in zip(original_standings, loaded_standings):
                assert orig["player"] == load["player"]
                assert orig["wins"] == load["wins"]
                assert orig["points"] == load["points"]
        finally:
            os.unlink(filepath)

    def test_to_dict(self):
        """Test tournament export to dictionary"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            participants=["P1", "P2"]
        )
        tournament.start()
        
        data = tournament.to_dict()
        
        assert isinstance(data, dict)
        assert "tournament_id" in data
        assert "name" in data
        assert "format" in data
        assert "participants" in data
        assert "matches" in data
        assert "standings" in data
        assert data["name"] == "Test"


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_tournament(self):
        """Test tournament with no participants"""
        tournament = Tournament(name="Test", format="swiss")
        assert len(tournament.participants) == 0

    def test_single_participant(self):
        """Test tournament with single participant"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            participants=["P1"]
        )
        
        with pytest.raises(ValueError):
            tournament.start()

    def test_remove_participant(self):
        """Test removing a participant"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            participants=["P1", "P2", "P3"]
        )
        tournament.remove_participant("P2")
        
        assert tournament.participants["P2"].active is False

    def test_bye_match_counts_as_win(self):
        """Test that bye matches count as wins"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            participants=["P1", "P2", "P3"]
        )
        tournament.start()
        
        # One player should have a bye
        bye_match = next(m for m in tournament.matches if m.is_bye())
        
        # Report other match
        non_bye_matches = [m for m in tournament.matches if not m.is_bye()]
        if non_bye_matches:
            match = non_bye_matches[0]
            tournament.report_match(
                match.round_num,
                match.match_num,
                match.player_a,
                4, 0
            )
        
        standings = tournament.get_standings()
        
        # Player with bye should have 1 win
        bye_player = bye_match.player_a
        bye_standing = next(s for s in standings if s["player"] == bye_player)
        assert bye_standing["wins"] == 1


class TestGetMethods:
    """Test data retrieval methods"""

    def test_get_standings_returns_list(self):
        """Test get_standings returns list of dicts"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            participants=["P1", "P2"]
        )
        
        standings = tournament.get_standings()
        assert isinstance(standings, list)
        assert all(isinstance(s, dict) for s in standings)

    def test_get_matches_all(self):
        """Test get_matches returns all matches"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            num_rounds=2,
            participants=["P1", "P2", "P3", "P4"]
        )
        tournament.start()
        
        # Get the actual matches and report them
        round1_matches = tournament.get_matches(round_num=1)
        tournament.report_match(1, 0, round1_matches[0]["player_a"], 4, 0)
        tournament.report_match(1, 1, round1_matches[1]["player_a"], 4, 0)
        
        all_matches = tournament.get_matches()
        assert len(all_matches) > 2  # Round 1 + Round 2

    def test_get_matches_by_round(self):
        """Test get_matches filtered by round"""
        tournament = Tournament(
            name="Test",
            format="swiss",
            num_rounds=2,
            participants=["P1", "P2", "P3", "P4"]
        )
        tournament.start()

        # Get the actual matches and report them
        round1_matches = tournament.get_matches(round_num=1)
        tournament.report_match(1, 0, round1_matches[0]["player_a"], 4, 0)
        tournament.report_match(1, 1, round1_matches[1]["player_a"], 4, 0)

        round1_matches = tournament.get_matches(round_num=1)
        assert all(m["round"] == 1 for m in round1_matches)
