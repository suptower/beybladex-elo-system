"""
Tests for the advanced season statistics module.
"""

import pytest
import tempfile
import csv
import json
import os
from src.season_statistics import (
    BeySeasonStats,
    SeasonStatistics,
    Match,
    Round
)


class TestBeySeasonStats:
    """Test BeySeasonStats class and its computed properties."""
    
    def test_initialization(self):
        """Test that BeySeasonStats initializes correctly."""
        stats = BeySeasonStats("TestBey")
        
        assert stats.bey_name == "TestBey"
        assert stats.matches_played == 0
        assert stats.matches_won == 0
        assert stats.matches_lost == 0
        assert stats.total_points_scored == 0
        assert stats.total_points_conceded == 0
        assert stats.rounds_won == 0
        assert stats.rounds_lost == 0
    
    def test_match_win_rate(self):
        """Test match win rate calculation."""
        stats = BeySeasonStats("TestBey")
        
        # No matches
        assert stats.match_win_rate == 0.0
        
        # With matches
        stats.matches_played = 10
        stats.matches_won = 7
        assert stats.match_win_rate == 70.0
    
    def test_points_differential(self):
        """Test points differential calculation."""
        stats = BeySeasonStats("TestBey")
        stats.total_points_scored = 50
        stats.total_points_conceded = 30
        
        assert stats.points_differential == 20
    
    def test_round_differential(self):
        """Test round differential calculation."""
        stats = BeySeasonStats("TestBey")
        stats.rounds_won = 40
        stats.rounds_lost = 25
        
        assert stats.round_differential == 15
    
    def test_points_per_round(self):
        """Test points per round (PPR) calculation."""
        stats = BeySeasonStats("TestBey")
        
        # No rounds
        assert stats.points_per_round == 0.0
        
        # With rounds
        stats.total_points_scored = 60
        stats.total_rounds_played = 40
        assert stats.points_per_round == 1.5
    
    def test_avg_rounds_per_match(self):
        """Test average rounds per match calculation."""
        stats = BeySeasonStats("TestBey")
        
        # No matches
        assert stats.avg_rounds_per_match == 0.0
        
        # With matches
        stats.total_rounds_played = 35
        stats.matches_played = 10
        assert stats.avg_rounds_per_match == 3.5
    
    def test_avg_points_per_match(self):
        """Test average points per match calculation."""
        stats = BeySeasonStats("TestBey")
        
        # No matches
        assert stats.avg_points_per_match == 0.0
        
        # With matches
        stats.total_points_scored = 45
        stats.matches_played = 15
        assert stats.avg_points_per_match == 3.0
    
    def test_finish_type_stats(self):
        """Test finish type statistics."""
        stats = BeySeasonStats("TestBey")
        
        stats.burst_wins = 10
        stats.pocket_wins = 8
        stats.extreme_wins = 5
        stats.spin_wins = 12
        
        assert stats.total_finishes == 35
    
    def test_burst_win_rate(self):
        """Test burst win rate calculation."""
        stats = BeySeasonStats("TestBey")
        
        # No wins
        assert stats.burst_win_rate == 0.0
        
        # With wins
        stats.rounds_won = 20
        stats.burst_wins = 5
        assert stats.burst_win_rate == 25.0
    
    def test_aggression_ratio(self):
        """Test aggression ratio calculation."""
        stats = BeySeasonStats("TestBey")
        
        # No wins
        assert stats.aggression_ratio == 0.0
        
        # With aggressive wins
        stats.rounds_won = 20
        stats.extreme_wins = 4
        stats.pocket_wins = 6
        stats.burst_wins = 2
        # Total aggressive = 12 / 20 = 60%
        assert stats.aggression_ratio == 60.0
    
    def test_defensive_stability_index(self):
        """Test defensive stability index calculation."""
        stats = BeySeasonStats("TestBey")
        
        # No rounds
        assert stats.defensive_stability_index == 1.0
        
        # With bursts suffered
        stats.total_rounds_played = 50
        stats.burst_losses = 5
        assert stats.defensive_stability_index == 0.9
    
    def test_clutch_win_rate(self):
        """Test clutch win rate calculation."""
        stats = BeySeasonStats("TestBey")
        
        # No matches
        assert stats.clutch_win_rate == 0.0
        
        # With clutch wins
        stats.matches_played = 20
        stats.clutch_matches_won = 5
        assert stats.clutch_win_rate == 25.0
    
    def test_offensive_power_index(self):
        """Test Offensive Power Index (OPI) calculation."""
        stats = BeySeasonStats("TestBey")
        
        # No matches
        assert stats.offensive_power_index == 0.0
        
        # With finishes: Burst=3, Extreme=2.5, Pocket=2, Spin=1
        stats.matches_played = 10
        stats.burst_wins = 5  # 5 * 3 = 15
        stats.extreme_wins = 4  # 4 * 2.5 = 10
        stats.pocket_wins = 3  # 3 * 2 = 6
        stats.spin_wins = 2  # 2 * 1 = 2
        # Total = 33 / 10 = 3.3
        assert stats.offensive_power_index == 3.3
    
    def test_dominance_index(self):
        """Test Dominance Index calculation."""
        stats = BeySeasonStats("TestBey")
        
        # No matches
        assert stats.dominance_index == 0.0
        
        # With data: (Points Diff per Match) + (PPR × 1.5)
        stats.matches_played = 10
        stats.total_points_scored = 50
        stats.total_points_conceded = 30
        stats.total_rounds_played = 40
        
        # Points diff per match = 20 / 10 = 2.0
        # PPR = 50 / 40 = 1.25
        # Dominance = 2.0 + (1.25 * 1.5) = 2.0 + 1.875 = 3.875
        assert abs(stats.dominance_index - 3.875) < 0.01
    
    def test_volatility_index(self):
        """Test Volatility Index calculation."""
        stats = BeySeasonStats("TestBey")
        
        # No data
        assert stats.volatility_index == 0.0
        
        # Single match
        stats.points_per_match = [4]
        assert stats.volatility_index == 0.0
        
        # Multiple matches with variance
        stats.points_per_match = [2, 4, 3, 5, 4]
        # Standard deviation should be > 0
        assert stats.volatility_index > 0
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        stats = BeySeasonStats("TestBey")
        stats.matches_played = 10
        stats.matches_won = 7
        
        result = stats.to_dict()
        
        assert isinstance(result, dict)
        assert result["bey_name"] == "TestBey"
        assert result["matches_played"] == 10
        assert result["matches_won"] == 7
        assert "match_win_rate" in result
        assert "offensive_power_index" in result
        assert "dominance_index" in result


class TestSeasonStatistics:
    """Test SeasonStatistics class functionality."""
    
    @pytest.fixture
    def temp_data_files(self):
        """Create temporary CSV files for testing."""
        temp_dir = tempfile.mkdtemp()
        
        # Create matches.csv
        matches_file = os.path.join(temp_dir, "matches.csv")
        with open(matches_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["MatchID", "Date", "BeyA", "BeyB", "ScoreA", "ScoreB",
                           "MatchType", "SeasonID", "Tier", "Matchday", "arena"])
            writer.writerow(["M001", "2025-01-01", "BeyA", "BeyB", "4", "2",
                           "season", "S1", "1", "1", "Xtreme"])
            writer.writerow(["M002", "2025-01-02", "BeyA", "BeyC", "3", "4",
                           "season", "S1", "1", "1", "Xtreme"])
            writer.writerow(["M003", "2025-01-03", "BeyB", "BeyC", "4", "1",
                           "season_cup", "S1", "", "", "Xtreme"])
        
        # Create rounds.csv
        rounds_file = os.path.join(temp_dir, "rounds.csv")
        with open(rounds_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["match_id", "round_number", "winner", "finish_type", "points_awarded", "notes"])
            # Match M001: BeyA wins 4-2
            writer.writerow(["M001", "1", "BeyA", "burst", "2", ""])
            writer.writerow(["M001", "2", "BeyA", "pocket", "2", ""])
            writer.writerow(["M001", "3", "BeyB", "spin", "1", ""])
            writer.writerow(["M001", "4", "BeyB", "spin", "1", ""])
            # Match M002: BeyC wins 4-3
            writer.writerow(["M002", "1", "BeyA", "extreme", "3", ""])
            writer.writerow(["M002", "2", "BeyC", "burst", "2", ""])
            writer.writerow(["M002", "3", "BeyC", "pocket", "2", ""])
            # Match M003: BeyB wins 4-1
            writer.writerow(["M003", "1", "BeyB", "burst", "2", ""])
            writer.writerow(["M003", "2", "BeyB", "pocket", "2", ""])
            writer.writerow(["M003", "3", "BeyC", "spin", "1", ""])
        
        yield matches_file, rounds_file, temp_dir
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
    
    def test_load_data(self, temp_data_files):
        """Test loading data from CSV files."""
        matches_file, rounds_file, _ = temp_data_files
        
        stats = SeasonStatistics(matches_file, rounds_file)
        stats.load_data()
        
        assert len(stats.matches) == 3
        assert len(stats.rounds) >= 7  # At least 7 rounds (some matches may have extra rounds)
    
    def test_load_data_with_season_filter(self, temp_data_files):
        """Test loading data with season filter."""
        matches_file, rounds_file, _ = temp_data_files
        
        stats = SeasonStatistics(matches_file, rounds_file)
        stats.load_data(season_id="S1")
        
        assert len(stats.matches) == 3  # All matches are S1
    
    def test_load_data_with_tier_filter(self, temp_data_files):
        """Test loading data with tier filter."""
        matches_file, rounds_file, _ = temp_data_files
        
        stats = SeasonStatistics(matches_file, rounds_file)
        stats.load_data(tier=1)
        
        # Tier filter only filters matches with explicit tier (season_cup has no tier)
        assert len(stats.matches) >= 2  # At least tier 1 matches
    
    def test_compute_statistics(self, temp_data_files):
        """Test computing statistics."""
        matches_file, rounds_file, _ = temp_data_files
        
        stats = SeasonStatistics(matches_file, rounds_file)
        stats.load_data()
        stats.compute_statistics()
        
        # Check that stats were computed
        assert "all" in stats.stats
        assert "swiss" in stats.stats
        assert "playoffs" in stats.stats
        
        # Check specific bey stats
        all_stats = stats.stats["all"]
        assert "BeyA" in all_stats
        assert "BeyB" in all_stats
        assert "BeyC" in all_stats
        
        # BeyA played 2 matches, won 1
        bey_a_stats = all_stats["BeyA"]
        assert bey_a_stats.matches_played == 2
        assert bey_a_stats.matches_won == 1
        assert bey_a_stats.matches_lost == 1
    
    def test_phase_separation(self, temp_data_files):
        """Test Swiss vs Playoffs phase separation."""
        matches_file, rounds_file, _ = temp_data_files
        
        stats = SeasonStatistics(matches_file, rounds_file)
        stats.load_data()
        stats.compute_statistics()
        
        # Swiss phase should have 2 matches
        swiss_stats = stats.stats["swiss"]
        assert len(swiss_stats) == 3  # BeyA, BeyB, BeyC
        
        # Playoffs phase should have 1 match
        playoff_stats = stats.stats["playoffs"]
        assert len(playoff_stats) == 2  # BeyB, BeyC
    
    def test_finish_type_tracking(self, temp_data_files):
        """Test that finish types are tracked correctly."""
        matches_file, rounds_file, _ = temp_data_files
        
        stats = SeasonStatistics(matches_file, rounds_file)
        stats.load_data()
        stats.compute_statistics()
        
        all_stats = stats.stats["all"]
        bey_a_stats = all_stats["BeyA"]
        
        # BeyA should have burst and pocket wins
        assert bey_a_stats.burst_wins > 0
        assert bey_a_stats.pocket_wins > 0
    
    def test_generate_leaderboards(self, temp_data_files):
        """Test leaderboard generation."""
        matches_file, rounds_file, _ = temp_data_files
        
        stats = SeasonStatistics(matches_file, rounds_file)
        stats.load_data()
        stats.compute_statistics()
        
        leaderboards = stats.generate_leaderboards("all")
        
        assert "match_win_rate" in leaderboards
        assert "points_differential" in leaderboards
        assert "offensive_power_index" in leaderboards
        assert "dominance_index" in leaderboards
        
        # Check that leaderboards are sorted
        match_win_leaders = leaderboards["match_win_rate"]
        assert len(match_win_leaders) > 0
        assert isinstance(match_win_leaders[0], BeySeasonStats)
    
    def test_generate_awards(self, temp_data_files):
        """Test award generation."""
        matches_file, rounds_file, _ = temp_data_files
        
        stats = SeasonStatistics(matches_file, rounds_file)
        stats.load_data()
        stats.compute_statistics()
        
        awards = stats.generate_awards("all", min_matches=1)
        
        # Should have various awards
        assert len(awards) > 0
        assert "most_dominant" in awards
        
        # Each award should have required fields
        for award_key, award in awards.items():
            assert "title" in award
            assert "icon" in award
            assert "winner" in award
            assert "value" in award
            assert "metric" in award
    
    def test_export_to_json(self, temp_data_files):
        """Test JSON export functionality."""
        matches_file, rounds_file, temp_dir = temp_data_files
        
        stats = SeasonStatistics(matches_file, rounds_file)
        stats.load_data()
        stats.compute_statistics()
        
        output_file = os.path.join(temp_dir, "test_output.json")
        stats.export_to_json(output_file, phase="all", include_awards=True)
        
        # Check file was created
        assert os.path.exists(output_file)
        
        # Check JSON structure
        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        assert "phase" in data
        assert "statistics" in data
        assert "leaderboards" in data
        assert "awards" in data
        
        # Check statistics structure
        assert len(data["statistics"]) > 0
        for bey, bey_stats in data["statistics"].items():
            assert "bey_name" in bey_stats
            assert "matches_played" in bey_stats
            assert "offensive_power_index" in bey_stats
    
    def test_export_to_csv(self, temp_data_files):
        """Test CSV export functionality."""
        matches_file, rounds_file, temp_dir = temp_data_files
        
        stats = SeasonStatistics(matches_file, rounds_file)
        stats.load_data()
        stats.compute_statistics()
        
        output_file = os.path.join(temp_dir, "test_output.csv")
        stats.export_to_csv(output_file, phase="all")
        
        # Check file was created
        assert os.path.exists(output_file)
        
        # Check CSV structure
        with open(output_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) > 0
        # Check headers
        assert "bey_name" in rows[0]
        assert "matches_played" in rows[0]
        assert "offensive_power_index" in rows[0]
        assert "dominance_index" in rows[0]


class TestClutchAndComebackDetection:
    """Test clutch and comeback detection logic."""
    
    def test_clutch_match_detection(self):
        """Test detection of clutch matches (close scores)."""
        stats_a = BeySeasonStats("BeyA")
        stats_b = BeySeasonStats("BeyB")
        
        # Create a close match: BeyA wins 3-2
        match = Match(
            match_id="M001",
            tier=1,
            phase="Swiss",
            bey_a="BeyA",
            bey_b="BeyB",
            final_score_a=3,
            final_score_b=2,
            winner="BeyA",
            total_rounds=5,
            timestamp="2025-01-01"
        )
        
        rounds = [
            Round("R1", "M001", 1, "BeyA", "BeyB", "BeyA", "BeyB", "BURST", 2),
            Round("R2", "M001", 2, "BeyA", "BeyB", "BeyB", "BeyA", "SPIN", 1),
            Round("R3", "M001", 3, "BeyA", "BeyB", "BeyB", "BeyA", "SPIN", 1),
            Round("R4", "M001", 4, "BeyA", "BeyB", "BeyA", "BeyB", "SPIN", 1),
        ]
        
        stat_sys = SeasonStatistics()
        stat_sys._detect_clutch_and_comebacks(match, rounds, stats_a, stats_b)
        
        # Close match, so clutch should be detected
        assert stats_a.clutch_matches_won > 0 or stats_b.clutch_matches_won > 0


class TestMatchEntity:
    """Test Match entity."""
    
    def test_match_creation(self):
        """Test Match dataclass creation."""
        match = Match(
            match_id="M001",
            tier=1,
            phase="Swiss",
            bey_a="BeyA",
            bey_b="BeyB",
            final_score_a=4,
            final_score_b=2,
            winner="BeyA",
            total_rounds=6,
            timestamp="2025-01-01"
        )
        
        assert match.match_id == "M001"
        assert match.tier == 1
        assert match.phase == "Swiss"
        assert match.winner == "BeyA"
        assert match.total_rounds == 6


class TestRoundEntity:
    """Test Round entity."""
    
    def test_round_creation(self):
        """Test Round dataclass creation."""
        round_obj = Round(
            round_id="R001",
            match_id="M001",
            round_number=1,
            bey_a="BeyA",
            bey_b="BeyB",
            winner="BeyA",
            loser="BeyB",
            finish_type="BURST",
            points_awarded=2
        )
        
        assert round_obj.round_id == "R001"
        assert round_obj.match_id == "M001"
        assert round_obj.winner == "BeyA"
        assert round_obj.finish_type == "BURST"
        assert round_obj.points_awarded == 2


class TestMinimumMatchesFilter:
    """Test minimum matches filter for awards."""
    
    def test_awards_respect_min_matches(self):
        """Test that awards filter by minimum matches."""
        # Create mock stats
        stats_dict = {
            "BeyA": BeySeasonStats("BeyA"),
            "BeyB": BeySeasonStats("BeyB"),
            "BeyC": BeySeasonStats("BeyC"),
        }
        
        # BeyA has enough matches and good stats
        stats_dict["BeyA"].matches_played = 10
        stats_dict["BeyA"].total_points_scored = 50
        stats_dict["BeyA"].total_points_conceded = 20
        stats_dict["BeyA"].total_rounds_played = 35
        
        # BeyB has enough matches but lower stats
        stats_dict["BeyB"].matches_played = 8
        stats_dict["BeyB"].total_points_scored = 30
        stats_dict["BeyB"].total_points_conceded = 25
        stats_dict["BeyB"].total_rounds_played = 28
        
        # BeyC doesn't have enough matches but has best stats
        stats_dict["BeyC"].matches_played = 3
        stats_dict["BeyC"].total_points_scored = 20
        stats_dict["BeyC"].total_points_conceded = 5
        stats_dict["BeyC"].total_rounds_played = 12
        
        stat_sys = SeasonStatistics()
        stat_sys.stats["all"] = stats_dict
        
        awards = stat_sys.generate_awards("all", min_matches=5)
        
        # Most dominant should be BeyA, not BeyC (due to min matches)
        if "most_dominant" in awards:
            assert awards["most_dominant"]["winner"] == "BeyA"
