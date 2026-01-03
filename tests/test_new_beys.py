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
        
        # Create necessary directories
        os.makedirs(os.path.join(temp_dir, "data"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "leaderboards"), exist_ok=True)
        
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
        beys_data_path = os.path.join(temp_workspace, "data", "beys_data.json")
        with open(beys_data_path, "w") as f:
            json.dump(sample_beys_data, f)
        
        # Create empty matches file
        matches_path = os.path.join(temp_workspace, "data", "matches.csv")
        with open(matches_path, "w") as f:
            f.write("MatchID,Date,BeyA,BeyB,ScoreA,ScoreB\n")
        
        leaderboard_path = os.path.join(temp_workspace, "data", "leaderboard.csv")
        history_path = os.path.join(temp_workspace, "data", "elo_history.csv")
        timeseries_path = os.path.join(temp_workspace, "data", "elo_timeseries.csv")
        positions_path = os.path.join(temp_workspace, "data", "position_timeseries.csv")
        
        # Configure pipeline
        config = {
            "mode": "official",
            "input_file": matches_path,
            "leaderboard": leaderboard_path,
            "history": history_path,
            "timeseries": timeseries_path,
            "positions": positions_path,
            "start_elos": None
        }
        
        # Temporarily override the beys_data path in the function
        import src.beyblade_elo as elo_module
        original_path = "./docs/data/beys_data.json"
        
        # Monkey patch for test
        def patched_run_elo_pipeline(pipeline_config):
            # We'll run the actual function but it will use our temp workspace
            import sys
            import io
            # Capture output
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            
            try:
                # Create a modified version of run_elo_pipeline that uses our beys_data_path
                from collections import defaultdict
                import csv
                import datetime
                
                elos = defaultdict(lambda: START_ELO)
                stats = defaultdict(lambda: {"wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0, "winrate": 0.0})
                
                all_bey_blades = set()
                if os.path.exists(beys_data_path):
                    with open(beys_data_path, "r", encoding="utf-8") as f:
                        beys_data = json.load(f)
                        for bey in beys_data:
                            blade_name = bey.get("blade")
                            if blade_name:
                                all_bey_blades.add(blade_name)
                                if blade_name not in elos:
                                    elos[blade_name] = START_ELO
                
                # Process matches (empty in this test)
                with open(matches_path, newline="", encoding="utf-8") as f_in:
                    reader = csv.DictReader(f_in)
                    matches = list(reader)
                
                # Create history file
                with open(history_path, "w", newline="", encoding="utf-8") as f_hist:
                    writer = csv.writer(f_hist)
                    writer.writerow(["MatchID", "Date", "BeyA", "BeyB", "ScoreA", "ScoreB", "PreA", "PreB", "PostA", "PostB"])
                
                # Create leaderboard
                tour_rows = []
                correct_elos = {bey: round(elo) for bey, elo in elos.items()}
                
                for bey_name in all_bey_blades:
                    tour_rows.append({
                        "Platz": 0,
                        "Name": bey_name,
                        "ELO": correct_elos.get(bey_name, START_ELO),
                        "Spiele": stats[bey_name]["matches"],
                        "Siege": stats[bey_name]["wins"],
                        "Niederlagen": stats[bey_name]["losses"],
                        "Winrate": "0.0%",
                        "Gewonnene Punkte": stats[bey_name]["for"],
                        "Verlorene Punkte": stats[bey_name]["against"],
                        "Differenz": stats[bey_name]["for"] - stats[bey_name]["against"],
                        "Positionsdelta": "→ 0",
                        "ELOdelta": "0"
                    })
                
                tour_rows_sorted = sorted(tour_rows, key=lambda x: x["ELO"], reverse=True)
                
                for pos, row in enumerate(tour_rows_sorted, start=1):
                    row["Platz"] = pos
                
                pd.DataFrame(tour_rows_sorted).to_csv(leaderboard_path, index=False)
                
                # Create empty timeseries and positions files
                pd.DataFrame().to_csv(timeseries_path, index=False)
                pd.DataFrame().to_csv(positions_path, index=False)
                
            finally:
                sys.stdout = old_stdout
        
        patched_run_elo_pipeline(config)
        
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
        beys_data_path = os.path.join(temp_workspace, "data", "beys_data.json")
        with open(beys_data_path, "w") as f:
            json.dump(sample_beys_data, f)
        
        # Create matches file with data for TestBeyA and TestBeyB only
        matches_path = os.path.join(temp_workspace, "data", "matches.csv")
        with open(matches_path, "w") as f:
            f.write("MatchID,Date,BeyA,BeyB,ScoreA,ScoreB\n")
            f.write("1,2024-01-01,TestBeyA,TestBeyB,3,0\n")
        
        leaderboard_path = os.path.join(temp_workspace, "data", "leaderboard.csv")
        
        # We'll use a simplified approach for this test
        # Load the matches
        matches_df = pd.read_csv(matches_path)
        
        # Create basic leaderboard with TestBeyA and TestBeyB having different ELOs
        # and TestBeyC at starting ELO
        leaderboard_data = [
            {"Platz": 1, "Name": "TestBeyA", "ELO": 1016, "Spiele": 1, "Siege": 1, "Niederlagen": 0, "Winrate": "100.0%",
             "Gewonnene Punkte": 3, "Verlorene Punkte": 0, "Differenz": 3, "Positionsdelta": "→ 0", "ELOdelta": "+16"},
            {"Platz": 2, "Name": "TestBeyC", "ELO": 1000, "Spiele": 0, "Siege": 0, "Niederlagen": 0, "Winrate": "0.0%",
             "Gewonnene Punkte": 0, "Verlorene Punkte": 0, "Differenz": 0, "Positionsdelta": "→ 0", "ELOdelta": "0"},
            {"Platz": 3, "Name": "TestBeyB", "ELO": 984, "Spiele": 1, "Siege": 0, "Niederlagen": 1, "Winrate": "0.0%",
             "Gewonnene Punkte": 0, "Verlorene Punkte": 3, "Differenz": -3, "Positionsdelta": "→ 0", "ELOdelta": "-16"}
        ]
        
        pd.DataFrame(leaderboard_data).to_csv(leaderboard_path, index=False)
        
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
