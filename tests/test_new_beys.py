"""
Tests for new bey addition functionality without match data
"""
import pytest
import json
import os
import tempfile
import shutil
import pandas as pd
from src.beyblade_elo import run_elo_pipeline, START_ELO


class TestNewBeyAddition:
    """Test suite for adding new beys without match data"""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing"""
        temp_dir = tempfile.mkdtemp()

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def sample_beys_data(self):
        """Sample beys_data.json with test beys"""
        return [
            {
                "code": "BX-01",
                "name": "TestBeyA 1-60R",
                "blade": "TestBeyA",
                "ratchet": "1-60",
                "bit": "Rush",
                "type": "Attack",
                "image": "./data/beys/TestBeyA.png",
                "description": "Test beyblade A"
            },
            {
                "code": "BX-02",
                "name": "TestBeyB 2-70B",
                "blade": "TestBeyB",
                "ratchet": "2-70",
                "bit": "Ball",
                "type": "Defense",
                "image": "./data/beys/TestBeyB.png",
                "description": "Test beyblade B"
            },
            {
                "code": "BX-03",
                "name": "TestBeyC 3-80S",
                "blade": "TestBeyC",
                "ratchet": "3-80",
                "bit": "Spike",
                "type": "Stamina",
                "image": "./data/beys/TestBeyC.png",
                "description": "Test beyblade C"
            }
        ]

    def test_new_beys_appear_in_leaderboard(self, temp_workspace, sample_beys_data):
        """Test that new beys without matches appear in leaderboard with starting ELO"""
        # Setup files
        beys_data_path = os.path.join(temp_workspace, "beys_data.json")
        with open(beys_data_path, "w") as f:
            json.dump(sample_beys_data, f)

        # Create empty matches file
        matches_path = os.path.join(temp_workspace, "matches.csv")
        with open(matches_path, "w") as f:
            f.write("MatchID,Date,BeyA,BeyB,ScoreA,ScoreB\n")

        leaderboard_path = os.path.join(temp_workspace, "leaderboard.csv")
        history_path = os.path.join(temp_workspace, "elo_history.csv")
        timeseries_path = os.path.join(temp_workspace, "elo_timeseries.csv")
        positions_path = os.path.join(temp_workspace, "position_timeseries.csv")

        # Configure pipeline with custom beys_data_path
        config = {
            "mode": "official",
            "input_file": matches_path,
            "leaderboard": leaderboard_path,
            "history": history_path,
            "timeseries": timeseries_path,
            "positions": positions_path,
            "start_elos": None,
            "beys_data_file": beys_data_path
        }

        # Run the actual pipeline
        run_elo_pipeline(config)

        # Verify leaderboard exists and contains all beys
        assert os.path.exists(leaderboard_path), "Leaderboard file should exist"

        leaderboard = pd.read_csv(leaderboard_path)
        assert len(leaderboard) == 3, "Leaderboard should contain all 3 test beys"

        # Check that all beys have starting ELO
        for _, row in leaderboard.iterrows():
            assert row["ELO"] == START_ELO, f"{row['Name']} should have starting ELO of {START_ELO}"
            assert row["Spiele"] == 0, f"{row['Name']} should have 0 matches"
            assert row["Siege"] == 0, f"{row['Name']} should have 0 wins"
            assert row["Niederlagen"] == 0, f"{row['Name']} should have 0 losses"
            assert row["Winrate"] == "0.0%", f"{row['Name']} should have 0% winrate"

    def test_new_beys_with_existing_matches(self, temp_workspace, sample_beys_data):
        """Test that new beys work alongside beys with match data"""
        # Setup files
        beys_data_path = os.path.join(temp_workspace, "beys_data.json")
        with open(beys_data_path, "w") as f:
            json.dump(sample_beys_data, f)

        # Create matches file with data for TestBeyA and TestBeyB only
        matches_path = os.path.join(temp_workspace, "matches.csv")
        with open(matches_path, "w") as f:
            f.write("MatchID,Date,BeyA,BeyB,ScoreA,ScoreB\n")
            f.write("1,2024-01-01,TestBeyA,TestBeyB,3,0\n")

        leaderboard_path = os.path.join(temp_workspace, "leaderboard.csv")
        history_path = os.path.join(temp_workspace, "elo_history.csv")
        timeseries_path = os.path.join(temp_workspace, "elo_timeseries.csv")
        positions_path = os.path.join(temp_workspace, "position_timeseries.csv")

        # Configure pipeline with custom beys_data_path
        config = {
            "mode": "official",
            "input_file": matches_path,
            "leaderboard": leaderboard_path,
            "history": history_path,
            "timeseries": timeseries_path,
            "positions": positions_path,
            "start_elos": None,
            "beys_data_file": beys_data_path
        }

        # Run the actual pipeline
        run_elo_pipeline(config)

        # Verify leaderboard
        leaderboard = pd.read_csv(leaderboard_path)
        assert len(leaderboard) == 3, "Leaderboard should contain all 3 beys"

        # Check TestBeyC has starting ELO and no matches
        testbey_c = leaderboard[leaderboard["Name"] == "TestBeyC"].iloc[0]
        assert testbey_c["ELO"] == START_ELO, "TestBeyC should have starting ELO"
        assert testbey_c["Spiele"] == 0, "TestBeyC should have 0 matches"

        # Check TestBeyA has increased ELO
        testbey_a = leaderboard[leaderboard["Name"] == "TestBeyA"].iloc[0]
        assert testbey_a["ELO"] > START_ELO, "TestBeyA should have ELO above starting"
        assert testbey_a["Spiele"] == 1, "TestBeyA should have 1 match"

        # Check TestBeyB has decreased ELO
        testbey_b = leaderboard[leaderboard["Name"] == "TestBeyB"].iloc[0]
        assert testbey_b["ELO"] < START_ELO, "TestBeyB should have ELO below starting"
        assert testbey_b["Spiele"] == 1, "TestBeyB should have 1 match"
